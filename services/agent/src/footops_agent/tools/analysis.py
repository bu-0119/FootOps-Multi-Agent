"""AgentScope tools exposing deterministic FootOps application services."""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from agentscope.tool import FunctionTool

from footops_agent.artifacts import (
    AgentToolTrace,
    AnalysisWorkspace,
    CompetitionSeason,
    PlayerCatalogEntry,
)
from footops_agent.providers import DataProviderError
from footops_agent.services import (
    AnalysisWorkspaceService,
    DataCatalogService,
    InsufficientDataError,
    PlayerNotFoundError,
    UnsupportedAnalysisQuestionError,
)

_COMPETITION_ALIASES = {
    "西甲": "la liga",
    "英超": "premier league",
    "德甲": "1. bundesliga",
    "意甲": "serie a",
    "法甲": "ligue 1",
    "欧冠": "champions league",
    "欧联": "uefa europa league",
    "欧洲杯": "uefa euro",
    "世界杯": "fifa world cup",
    "美洲杯": "copa america",
    "国王杯": "copa del rey",
}


def _normalize(value: str) -> str:
    value = value.casefold().strip()
    for alias, canonical in _COMPETITION_ALIASES.items():
        value = value.replace(alias, canonical)
    value = re.sub(r"(\d{4})[./-](\d{2})(?!\d)", r"\1/20\2", value)
    value = value.replace("赛季", "").replace("season", "")
    return re.sub(r"[^\w]+", "", value)


def _competition_matches(query: str, item: CompetitionSeason) -> bool:
    """Match compact names embedded in a longer natural-language query."""
    normalized_query = _normalize(query)
    if not normalized_query:
        return True
    competition_name = _normalize(item.competition_name)
    season_name = _normalize(item.season_name)
    label = _normalize(
        " ".join(
            [
                item.country_name,
                item.competition_name,
                item.season_name,
            ]
        )
    )
    if normalized_query in label or label in normalized_query:
        return True
    if competition_name not in normalized_query:
        return False
    mentions_year = bool(re.search(r"\d{4}", normalized_query))
    return not mentions_year or season_name in normalized_query


@dataclass
class AgentToolContext:
    """Per-run artifact storage kept outside model-controlled output."""

    traces: list[AgentToolTrace] = field(default_factory=list)
    workspace: AnalysisWorkspace | None = None
    resolved_competition: CompetitionSeason | None = None
    resolved_player: PlayerCatalogEntry | None = None
    on_trace: Callable[[AgentToolTrace], None] | None = None

    def record(self, tool_name: str, status: str, summary: str) -> None:
        trace = AgentToolTrace(
            sequence=len(self.traces) + 1,
            tool_name=tool_name,
            status=status,  # type: ignore[arg-type]
            summary=summary,
        )
        self.traces.append(trace)
        if self.on_trace is not None:
            self.on_trace(trace)


def build_scope_tools(
    catalog: DataCatalogService,
    context: AgentToolContext,
) -> list[FunctionTool]:
    """Build read-only catalog tools for the dedicated ScopeAgent."""

    async def search_competitions(query: str = "", limit: int = 12) -> dict:
        """Search public competition-season coverage by name, alias or season."""
        competitions = await asyncio.to_thread(catalog.list_competitions)
        candidates = []
        for item in competitions:
            if not _competition_matches(query, item):
                continue
            candidates.append(item.model_dump(mode="json"))
        if _normalize(query):
            candidates = candidates[: max(1, min(limit, 20))]
        context.resolved_competition = (
            CompetitionSeason.model_validate(candidates[0])
            if len(candidates) == 1
            else None
        )
        status = "completed" if candidates else "not_found"
        context.record(
            "search_competitions",
            status,
            f"赛事检索返回 {len(candidates)} 个候选。",
        )
        return {
            "status": status,
            "query": query,
            "candidates": candidates,
            "instruction": (
                "候选不唯一时必须向用户澄清，不能自行选择。"
                if len(candidates) != 1
                else "使用候选的 competition_id 和 season_id 继续检索球员。"
            ),
        }

    async def search_players(
        competition_id: int,
        season_id: int,
        player_query: str,
        limit: int = 8,
    ) -> dict:
        """Find player candidates inside one verified competition season."""
        try:
            competition, players = await asyncio.to_thread(
                catalog.list_players,
                competition_id,
                season_id,
            )
        except DataProviderError as exc:
            context.record("search_players", "not_found", "赛事赛季不在公开目录中。")
            return {"status": "not_found", "message": str(exc), "candidates": []}

        query = _normalize(player_query)
        candidates = []
        for entry in players:
            names = [entry.player.player_name, entry.player.player_nickname or ""]
            if query and not any(
                query in _normalize(name) or _normalize(name) in query
                for name in names
                if name
            ):
                continue
            candidates.append(entry.model_dump(mode="json"))
        candidates = candidates[: max(1, min(limit, 20))]
        context.resolved_player = (
            PlayerCatalogEntry.model_validate(candidates[0])
            if len(candidates) == 1
            else None
        )
        status = "completed" if candidates else "not_found"
        context.record(
            "search_players",
            status,
            f"{competition.competition_name} {competition.season_name} 返回 "
            f"{len(candidates)} 个球员候选。",
        )
        return {
            "status": status,
            "competition": competition.model_dump(mode="json"),
            "query": player_query,
            "candidates": candidates,
            "instruction": (
                "使用候选的规范球员名和 player_id 执行分析。"
                if len(candidates) == 1
                else (
                    "未命中且输入是中文译名时，可转换为常见拉丁字母简称后重试一次；"
                    "只能使用重试工具返回的 ID。"
                    if not candidates
                    else "候选不唯一时必须向用户澄清。"
                )
            ),
        }

    return [
        FunctionTool(search_competitions, is_read_only=True),
        FunctionTool(search_players, is_read_only=True),
    ]


def build_analysis_tools(
    catalog: DataCatalogService,
    workspace_service: AnalysisWorkspaceService,
    context: AgentToolContext,
) -> list[FunctionTool]:
    """Build catalog and deterministic analysis tools for one Agent run."""

    scope_tools = build_scope_tools(catalog, context)

    async def run_player_role_analysis(
        question: str,
        competition_id: int,
        season_id: int,
        player: str,
        player_id: int,
        requested_window: int = 5,
    ) -> dict:
        """Run deterministic player-role metrics, evidence gate and workspace build."""
        try:
            workspace = await asyncio.to_thread(
                workspace_service.create,
                question,
                competition_id,
                season_id,
                player,
                requested_window,
                player_id,
            )
        except PlayerNotFoundError:
            context.record(
                "run_player_role_analysis",
                "not_found",
                "所选范围没有该球员的公开出场数据。",
            )
            return {
                "status": "not_found",
                "message": "所选赛事赛季中没有找到该球员，请核对范围。",
            }
        except InsufficientDataError:
            context.record(
                "run_player_role_analysis",
                "insufficient",
                "公开出场不足两场，未生成分析。",
            )
            return {
                "status": "insufficient",
                "message": "公开数据不足两场，请更换赛事赛季或球员。",
            }
        except UnsupportedAnalysisQuestionError as exc:
            context.record(
                "run_player_role_analysis",
                "unsupported",
                "问题超出当前球员角色指标能力。",
            )
            return {"status": "unsupported", "message": exc.public_message}
        except DataProviderError:
            context.record(
                "run_player_role_analysis",
                "error",
                "公开数据源读取失败。",
            )
            return {
                "status": "error",
                "message": "公开数据源暂时不可用，请稍后重试。",
            }

        context.workspace = workspace
        context.record(
            "run_player_role_analysis",
            "completed",
            f"工作区 {workspace.workspace_id} 已通过证据门禁，"
            f"包含 {len(workspace.findings)} 条观察。",
        )
        appearances = {
            item.match.match_id: item
            for item in (workspace.coverage.appearances if workspace.coverage else [])
        }
        reviewed_findings = {
            item.finding_id: item
            for item in (
                workspace.evidence_review.reviews if workspace.evidence_review else []
            )
        }
        match_facts = []
        if workspace.metrics is not None:
            for row in workspace.metrics.matches:
                appearance = appearances.get(row.match_id)
                match = appearance.match if appearance else None
                team_id = appearance.team.team_id if appearance else None
                opponent = None
                score = None
                if match and team_id == match.home_team.team_id:
                    opponent = match.away_team.team_name
                    if match.home_score is not None and match.away_score is not None:
                        score = f"{match.home_score}-{match.away_score}"
                elif match:
                    opponent = match.home_team.team_name
                    if match.home_score is not None and match.away_score is not None:
                        score = f"{match.away_score}-{match.home_score}"
                match_facts.append(
                    {
                        "match_id": row.match_id,
                        "date": row.match_date.isoformat(),
                        "opponent": opponent,
                        "score_from_player_team_perspective": score,
                        "metrics": {
                            "shots": row.shot_count,
                            "xg": row.expected_goals,
                            "shot_involvements": row.shot_involvement_count,
                            "key_passes": row.key_pass_count,
                            "forward_passes": row.forward_pass_count,
                            "progressive_carries": row.progressive_carry_count,
                            "average_touch_x": row.average_touch_x,
                        },
                        "source_ref": f"source:{row.match_id}",
                        "metric_refs": {
                            "shots": f"metric:shot_count:{row.match_id}",
                            "xg": f"metric:expected_goals:{row.match_id}",
                            "shot_involvements": (
                                f"metric:shot_involvement_count:{row.match_id}"
                            ),
                        },
                    }
                )
        findings_for_model = [
            {
                "finding_id": finding.finding_id,
                "statement": finding.statement,
                "claim_type": finding.claim_type,
                "review_status": reviewed_findings.get(finding.finding_id).status
                if finding.finding_id in reviewed_findings
                else "unreviewed",
                "limitations": finding.limitations,
            }
            for finding in workspace.findings
        ]
        return {
            "status": "completed",
            "workspace_id": workspace.workspace_id,
            "finding_count": len(workspace.findings),
            "evidence_status": (
                workspace.evidence_review.overall_status
                if workspace.evidence_review
                else "missing"
            ),
            "player": workspace.metrics.player.model_dump(mode="json")
            if workspace.metrics
            else None,
            "competition": workspace.coverage.competition.model_dump(mode="json")
            if workspace.coverage
            else None,
            "match_facts": match_facts,
            "reviewed_findings": findings_for_model,
            "limitations": workspace.metrics.limitations if workspace.metrics else [],
            "instruction": (
                "match_facts 是逐场事实依据；用户问哪场最高时，只指出胜出场次、"
                "该指标值和来源，不要逐场抄写所有数据（界面会展示完整数据表）。"
                "射门次数、xG、射门参与是不同指标，不能互相替代。用户问‘整体发挥最好’"
                "但未给标准时，不得私自合成总分；分别概括可用维度或询问评判口径。"
                "只可称‘样本内上升/下降’，不可在没有统计检验时写‘统计显著’。"
                "只根据 review_status=‘supported’ 的 Finding 下结论。"
                "结束工具调用并返回 completed。"
            ),
        }

    return [
        *scope_tools,
        FunctionTool(run_player_role_analysis, is_read_only=True),
    ]

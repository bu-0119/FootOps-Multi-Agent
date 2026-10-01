"""AgentScope runtime for natural-language FootOps analysis requests."""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentscope.agent import Agent, ContextConfig, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.model import DeepSeekChatModel
from agentscope.state import AgentState
from agentscope.tool import Toolkit

from footops_agent.artifacts import (
    AgentAnalysisInput,
    AgentDecision,
    AgentModelUsage,
    AgentToolTrace,
    AnalysisWorkspace,
    ResolvedAgentScope,
)
from footops_agent.config import Settings
from footops_agent.prompts import (
    ANALYSIS_AGENT_SYSTEM_PROMPT,
    ANALYSIS_CONTEXT_COMPRESSION_PROMPT,
)
from footops_agent.services import AnalysisWorkspaceService, DataCatalogService
from footops_agent.tools import AgentToolContext, build_analysis_tools

from .usage import collect_agent_model_usage

PLAYER_ROLE_SKILL_DIR = (
    Path(__file__).resolve().parents[1] / "skills" / "player_role_analysis"
)


def _decision_from_workspace(workspace: AnalysisWorkspace) -> AgentDecision:
    """Build a trusted completion when only model formatting was exhausted."""
    scope = workspace.request.scope
    coverage = workspace.coverage
    competition = coverage.competition if coverage is not None else None
    return AgentDecision(
        action="completed",
        message="已完成数据检索、确定性指标计算和证据审核。",
        resolved_scope=ResolvedAgentScope(
            competition_id=scope.competition_id,
            season_id=scope.season_id,
            competition_name=(
                competition.competition_name if competition is not None else None
            ),
            season_name=competition.season_name if competition is not None else None,
            player=scope.player,
            player_id=scope.player_id,
            requested_window=(
                coverage.requested_window if coverage is not None else None
            ),
        ),
        limitations=[
            "最终状态由已保存的 Workspace 构造；模型结构化输出预算已耗尽。",
        ],
    )


def _safe_clarification(
    decision: AgentDecision,
    trace: list[AgentToolTrace],
) -> AgentDecision:
    """Replace model-authored scope examples with tool-grounded wording."""
    scope = decision.resolved_scope
    if scope.competition_id is None or scope.season_id is None:
        message = "请补充要分析的赛事和赛季；我只会使用公开目录中核验到的范围。"
    elif scope.player_id is None:
        label = " ".join(
            item
            for item in [scope.competition_name, scope.season_name]
            if item
        )
        player_not_found = any(
            item.tool_name == "search_players" and item.status == "not_found"
            for item in trace
        )
        if player_not_found:
            message = (
                f"已确认 {label or '赛事赛季'}，但没有唯一匹配到该球员。"
                "请补充常用英文名或完整姓名。"
            )
        else:
            message = f"已确认 {label or '赛事赛季'}，请补充要分析的球员。"
    else:
        message = "还缺少一个可核验的分析条件，请补充赛事、赛季或球员范围。"
    return decision.model_copy(update={"message": message})


@dataclass(frozen=True)
class AgentRuntimeResult:
    """Trusted result returned to the Harness after one bounded run."""

    decision: AgentDecision
    workspace: AnalysisWorkspace | None
    trace: list[AgentToolTrace]
    usage: AgentModelUsage | None = None


class AnalysisAgentRuntime(Protocol):
    mode: str
    provider: str
    model_name: str
    model_called: bool

    async def run(self, request: AgentAnalysisInput) -> AgentRuntimeResult:
        """Execute one natural-language orchestration run."""


class MockAnalysisAgentRuntime:
    """Deterministic runtime used by tests and credential-free development."""

    mode = "mock"
    provider = "none"
    model_name = "mock"
    model_called = False

    def __init__(
        self,
        catalog: DataCatalogService,
        workspace_service: AnalysisWorkspaceService,
        trace_callback: Callable[[AgentToolTrace], None] | None = None,
    ) -> None:
        self.catalog = catalog
        self.workspace_service = workspace_service
        self.trace_callback = trace_callback

    async def run(self, request: AgentAnalysisInput) -> AgentRuntimeResult:
        hint = request.scope_hint
        if hint.competition_id is None or hint.season_id is None:
            return self._clarify("请补充要分析的赛事和赛季。", hint)
        if not hint.player:
            return self._clarify("请告诉我要分析哪名球员。", hint)

        player_id = hint.player_id
        canonical_name = hint.player
        if player_id is None:
            _, players = await asyncio.to_thread(
                self.catalog.list_players,
                hint.competition_id,
                hint.season_id,
            )
            query = hint.player.casefold().strip()
            matches = [
                entry
                for entry in players
                if query
                in {
                    entry.player.player_name.casefold(),
                    (entry.player.player_nickname or "").casefold(),
                }
            ]
            if len(matches) != 1:
                return self._clarify("没有唯一匹配到球员，请补充完整姓名。", hint)
            player_id = matches[0].player.player_id
            canonical_name = (
                matches[0].player.player_nickname or matches[0].player.player_name
            )

        workspace = await asyncio.to_thread(
            self.workspace_service.create,
            request.question,
            hint.competition_id,
            hint.season_id,
            canonical_name,
            hint.requested_window or 5,
            player_id,
        )
        decision = AgentDecision(
            action="completed",
            message="mock Agent 已使用明确范围执行确定性分析。",
            resolved_scope=ResolvedAgentScope(
                competition_id=hint.competition_id,
                season_id=hint.season_id,
                player=canonical_name,
                player_id=player_id,
                requested_window=hint.requested_window or 5,
            ),
            limitations=["mock 模式不会从自然语言推断缺失实体。"],
        )
        return AgentRuntimeResult(decision, workspace, [])

    @staticmethod
    def _clarify(message: str, hint: object) -> AgentRuntimeResult:
        scope = hint if hasattr(hint, "model_dump") else None
        values = scope.model_dump() if scope is not None else {}
        decision = AgentDecision(
            action="clarification_required",
            message=message,
            resolved_scope=ResolvedAgentScope(**values),
            limitations=["mock 模式不会调用 LLM 解析缺失范围。"],
        )
        return AgentRuntimeResult(decision, None, [])


class DeepSeekAnalysisAgentRuntime:
    """Request-scoped AgentScope ReAct runtime backed by DeepSeek."""

    mode = "deepseek"
    provider = "deepseek"
    model_called = True

    def __init__(
        self,
        settings: Settings,
        catalog: DataCatalogService,
        workspace_service: AnalysisWorkspaceService,
        trace_callback: Callable[[AgentToolTrace], None] | None = None,
    ) -> None:
        if settings.deepseek_api_key is None:
            raise ValueError("DeepSeek API key is required")
        self.settings = settings
        self.catalog = catalog
        self.workspace_service = workspace_service
        self.trace_callback = trace_callback
        self.model_name = settings.deepseek_model

    def _build_model(self) -> DeepSeekChatModel:
        credential = DeepSeekCredential(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
        )
        return DeepSeekChatModel(
            credential=credential,
            model=self.settings.deepseek_model,
            parameters=DeepSeekChatModel.Parameters(
                max_tokens=2200,
                temperature=0.1,
            ),
            stream=False,
            max_retries=1,
            client_kwargs={
                "timeout": self.settings.footops_request_timeout_seconds,
            },
        )

    def _build_agent(self, context: AgentToolContext) -> Agent:
        """Assemble one isolated AgentScope session with bounded context."""
        toolkit = Toolkit(
            tools=build_analysis_tools(
                self.catalog,
                self.workspace_service,
                context,
            ),
            skills_or_loaders=[str(PLAYER_ROLE_SKILL_DIR)],
        )
        return Agent(
            name="FootOpsAnalysisAgent",
            system_prompt=ANALYSIS_AGENT_SYSTEM_PROMPT,
            model=self._build_model(),
            toolkit=toolkit,
            state=AgentState(
                middle_context={"footops_capability": "player_role_analysis"}
            ),
            context_config=ContextConfig(
                trigger_ratio=self.settings.footops_context_trigger_ratio,
                reserve_ratio=self.settings.footops_context_reserve_ratio,
                compression_prompt=ANALYSIS_CONTEXT_COMPRESSION_PROMPT,
                tool_result_limit=self.settings.footops_tool_result_limit,
            ),
            react_config=ReActConfig(
                max_iters=self.settings.footops_agent_max_iters,
                structured_output_grace_iters=2,
            ),
        )
    async def run(self, request: AgentAnalysisInput) -> AgentRuntimeResult:
        context = AgentToolContext(on_trace=self.trace_callback)
        agent = self._build_agent(context)
        content = {
            "question": request.question,
            "conversation_history": [
                turn.model_dump() for turn in request.history
            ],
            "scope_hint": request.scope_hint.model_dump(exclude_none=True),
            "instruction": (
                "先读取 footops-player-role-analysis Skill，再按 Skill 使用工具。"
            ),
        }
        response = await agent.reply(
            UserMsg(
                name="user",
                content=json.dumps(content, ensure_ascii=False),
            ),
            structured_schema=AgentDecision,
        )
        usage = collect_agent_model_usage(agent, self.settings)
        if response.structured_output is None:
            if context.workspace is None:
                trace = ", ".join(
                    f"{item.tool_name}:{item.status}" for item in context.traces
                )
                raise RuntimeError(
                    "Agent returned no structured decision; "
                    f"tool trace: {trace or 'empty'}"
                )
            decision = _decision_from_workspace(context.workspace)
        else:
            decision = AgentDecision.model_validate(response.structured_output)

        if decision.action == "clarification_required":
            decision = _safe_clarification(decision, context.traces)

        if context.workspace is not None and decision.action != "completed":
            decision = decision.model_copy(
                update={
                    "action": "completed",
                    "message": "已完成数据检索、确定性指标计算和证据审核。",
                }
            )
        if context.workspace is None and decision.action == "completed":
            raise RuntimeError("Agent reported completion without a workspace")
        return AgentRuntimeResult(
            decision,
            context.workspace,
            context.traces,
            usage,
        )

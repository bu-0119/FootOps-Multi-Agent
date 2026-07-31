"""Coverage auditing for public football datasets."""

from footops_agent.artifacts import CompetitionSeason, CoverageAuditArtifact
from footops_agent.providers import DataProviderError, FootballDataProvider


class InsufficientDataError(RuntimeError):
    """The selected public dataset cannot satisfy the golden-task window."""


class DataCatalogService:
    """Inspect coverage without invoking an LLM or producing a conclusion."""

    def __init__(self, provider: FootballDataProvider):
        self.provider = provider

    def audit_player(
        self,
        competition_id: int,
        season_id: int,
        player_query: str,
        requested_window: int = 5,
    ) -> CoverageAuditArtifact:
        competition = self._resolve_competition(competition_id, season_id)
        matches = self.provider.list_matches(competition_id, season_id)
        appearances = self.provider.find_player_appearances(matches, player_query)
        selected = appearances[-requested_window:]
        warnings = []
        if len(appearances) < 3:
            warnings.append(
                "公开数据中不足 3 场有出场位置记录的比赛，不能执行黄金任务。"
            )
        elif len(appearances) < requested_window:
            warnings.append(
                f"请求 {requested_window} 场，但公开数据只覆盖 {len(appearances)} 场；"
                "建议缩小窗口。"
            )
        return CoverageAuditArtifact(
            source=self.provider.source_reference("competitions.json"),
            query=player_query.strip(),
            competition=competition,
            matches_scanned=len(matches),
            appearances=appearances,
            requested_window=requested_window,
            suggested_match_ids=[item.match.match_id for item in selected],
            meets_minimum=len(appearances) >= 3,
            warnings=warnings,
        )

    def _resolve_competition(
        self,
        competition_id: int,
        season_id: int,
    ) -> CompetitionSeason:
        for competition in self.provider.list_competitions():
            if (
                competition.competition_id == competition_id
                and competition.season_id == season_id
            ):
                return competition
        raise DataProviderError(
            "competition and season are not available in the public dataset"
        )

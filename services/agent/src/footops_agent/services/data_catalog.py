"""Coverage auditing for public football datasets."""

from footops_agent.artifacts import (
    CompetitionSeason,
    CoverageAuditArtifact,
    PlayerCatalogEntry,
)
from footops_agent.providers import DataProviderError, FootballDataProvider


class InsufficientDataError(RuntimeError):
    """The selected public dataset cannot satisfy the golden-task window."""


class PlayerNotFoundError(RuntimeError):
    """The selected dataset does not contain the requested player."""


class DataCatalogService:
    """Inspect coverage without invoking an LLM or producing a conclusion."""

    def __init__(self, provider: FootballDataProvider):
        self.provider = provider
        self._player_catalog_cache: dict[
            tuple[int, int],
            tuple[CompetitionSeason, list[PlayerCatalogEntry]],
        ] = {}

    def list_competitions(self) -> list[CompetitionSeason]:
        return self.provider.list_competitions()

    def list_players(
        self,
        competition_id: int,
        season_id: int,
    ) -> tuple[CompetitionSeason, list[PlayerCatalogEntry]]:
        cache_key = (competition_id, season_id)
        cached = self._player_catalog_cache.get(cache_key)
        if cached is not None:
            competition, players = cached
            return competition, list(players)
        competition = self._resolve_competition(competition_id, season_id)
        matches = self.provider.list_matches(competition_id, season_id)
        players = self.provider.list_players(matches)
        self._player_catalog_cache[cache_key] = (competition, players)
        return competition, list(players)

    def audit_player(
        self,
        competition_id: int,
        season_id: int,
        player_query: str,
        requested_window: int = 5,
        player_id: int | None = None,
    ) -> CoverageAuditArtifact:
        competition = self._resolve_competition(competition_id, season_id)
        matches = self.provider.list_matches(competition_id, season_id)
        appearances = self.provider.find_player_appearances(
            matches,
            player_query,
            player_id,
        )
        if not appearances:
            raise PlayerNotFoundError(player_query)
        selected = appearances[-requested_window:]
        warnings = []
        if len(appearances) < 2:
            warnings.append(
                "公开数据中不足 2 场有出场位置记录的比赛，不能执行对比分析。"
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
            meets_minimum=len(appearances) >= 2,
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

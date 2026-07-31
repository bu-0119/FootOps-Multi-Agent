"""Provider interfaces consumed by deterministic FootOps services."""

from typing import Protocol

from footops_agent.artifacts import (
    CompetitionSeason,
    MatchDataSnapshot,
    MatchRef,
    PlayerMatchCoverage,
    SourceReference,
)


class DataProviderError(RuntimeError):
    """Base failure raised by a football-data provider."""


class ResourceNotFoundError(DataProviderError):
    """A provider resource does not exist in the public dataset."""


class FootballDataProvider(Protocol):
    """Read-only provider contract for the Phase 2A data slice."""

    name: str

    def list_competitions(self) -> list[CompetitionSeason]: ...

    def list_matches(self, competition_id: int, season_id: int) -> list[MatchRef]: ...

    def find_player_appearances(
        self,
        matches: list[MatchRef],
        player_query: str,
    ) -> list[PlayerMatchCoverage]: ...

    def load_player_snapshot(
        self,
        coverage: PlayerMatchCoverage,
    ) -> MatchDataSnapshot: ...

    def source_reference(self, relative_path: str) -> SourceReference: ...

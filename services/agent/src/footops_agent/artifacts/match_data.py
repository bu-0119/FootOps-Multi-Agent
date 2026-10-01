"""Contracts for football-data coverage and normalized match snapshots."""

from datetime import date
from typing import Literal

from pydantic import Field

from .base import SourceReference, StrictModel


class CompetitionSeason(StrictModel):
    competition_id: int
    season_id: int
    country_name: str
    competition_name: str
    season_name: str


class TeamRef(StrictModel):
    team_id: int
    team_name: str


class PlayerRef(StrictModel):
    player_id: int
    player_name: str
    player_nickname: str | None = None


class PositionInterval(StrictModel):
    position_id: int
    position_name: str
    from_time: str | None = None
    to_time: str | None = None
    from_period: int | None = None
    to_period: int | None = None


class MatchRef(StrictModel):
    match_id: int
    match_date: date
    competition: CompetitionSeason
    home_team: TeamRef
    away_team: TeamRef
    home_score: int | None = None
    away_score: int | None = None


class PlayerMatchCoverage(StrictModel):
    match: MatchRef
    player: PlayerRef
    team: TeamRef
    positions: list[PositionInterval] = Field(default_factory=list)
    lineups_url: str
    events_url: str


class PlayerCatalogEntry(StrictModel):
    """One resolvable player and their coverage in a competition season."""

    player: PlayerRef
    teams: list[TeamRef] = Field(default_factory=list)
    appearance_count: int = Field(ge=1)
    first_match_date: date
    last_match_date: date


class CoverageAuditArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    source: SourceReference
    query: str
    competition: CompetitionSeason
    matches_scanned: int
    appearances: list[PlayerMatchCoverage] = Field(default_factory=list)
    requested_window: int = Field(ge=2, le=10)
    suggested_match_ids: list[int] = Field(default_factory=list, max_length=10)
    meets_minimum: bool
    warnings: list[str] = Field(default_factory=list)


class PitchLocation(StrictModel):
    """StatsBomb's normalized 120 by 80 event coordinate."""

    x: float = Field(ge=0, le=120)
    y: float = Field(ge=0, le=80)


class PlayerEvent(StrictModel):
    event_id: str
    event_index: int
    match_id: int
    period: int
    minute: int
    second: int
    event_type: str
    event_type_id: int
    play_pattern: str | None = None
    location: PitchLocation | None = None
    end_location: PitchLocation | None = None
    outcome: str | None = None
    pass_assisted_shot_id: str | None = None
    pass_shot_assist: bool = False
    pass_goal_assist: bool = False


class MatchDataSnapshot(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    source: SourceReference
    match: MatchRef
    player: PlayerRef
    team: TeamRef
    positions: list[PositionInterval] = Field(default_factory=list)
    events: list[PlayerEvent] = Field(default_factory=list)

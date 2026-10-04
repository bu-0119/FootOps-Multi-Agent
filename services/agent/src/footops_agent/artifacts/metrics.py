"""Deterministic metric artifacts for the player-role golden task."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from .base import SourceReference, StrictModel, utc_now
from .match_data import PlayerRef


class MatchRoleMetrics(StrictModel):
    match_id: int
    match_date: date
    event_count: int = Field(ge=0)
    touch_event_count: int = Field(ge=0)
    average_touch_x: float | None = Field(default=None, ge=0, le=120)
    average_touch_y: float | None = Field(default=None, ge=0, le=80)
    attacking_third_touch_count: int = Field(ge=0)
    attacking_third_touch_ratio: float | None = Field(default=None, ge=0, le=1)
    penalty_area_touch_count: int = Field(ge=0)
    penalty_area_touch_ratio: float | None = Field(default=None, ge=0, le=1)
    receipt_count: int = Field(ge=0)
    average_receipt_x: float | None = Field(default=None, ge=0, le=120)
    forward_pass_count: int = Field(ge=0)
    completed_forward_pass_count: int = Field(ge=0)
    progressive_carry_count: int = Field(ge=0)
    key_pass_count: int = Field(ge=0)
    shot_count: int = Field(ge=0)
    expected_goals: float | None = Field(default=None, ge=0)
    shot_involvement_count: int = Field(ge=0)


class PlayerRoleMetricArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    metric_definition_version: Literal["footops-player-role-v1"] = (
        "footops-player-role-v1"
    )
    generated_at: datetime = Field(default_factory=utc_now)
    player: PlayerRef
    sources: list[SourceReference] = Field(min_length=1)
    matches: list[MatchRoleMetrics] = Field(min_length=1, max_length=10)
    limitations: list[str] = Field(default_factory=list)

"""Deterministic, evidence-linked tactics board contracts."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel, utc_now


class BoardPoint(StrictModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class TacticsPlayerMarker(StrictModel):
    marker_id: str
    label: str = Field(min_length=1)
    display_label: str = Field(min_length=1, max_length=3)
    position: BoardPoint
    role: Literal["focus", "teammate", "opponent"] = "focus"
    finding_refs: list[str] = Field(min_length=1)


class TacticsZone(StrictModel):
    zone_id: str
    label: str = Field(min_length=1)
    kind: Literal["touch_area", "attacking_third"]
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    width: float = Field(gt=0, le=100)
    height: float = Field(gt=0, le=100)
    finding_refs: list[str] = Field(min_length=1)


class TacticsArrow(StrictModel):
    arrow_id: str
    label: str = Field(min_length=1)
    kind: Literal["movement", "passing"]
    start: BoardPoint
    end: BoardPoint
    finding_refs: list[str] = Field(min_length=1)


class TacticsAnnotation(StrictModel):
    annotation_id: str
    text: str = Field(min_length=1)
    finding_refs: list[str] = Field(min_length=1)


class TacticsBoardArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    generator: Literal["footops-deterministic-tactics-v1"] = (
        "footops-deterministic-tactics-v1"
    )
    title: str = Field(min_length=1)
    pitch_orientation: Literal["vertical_attacking_up"] = "vertical_attacking_up"
    formation: Literal["unassigned", "4-3-3", "4-2-3-1", "3-4-3"] = (
        "unassigned"
    )
    players: list[TacticsPlayerMarker] = Field(default_factory=list)
    zones: list[TacticsZone] = Field(default_factory=list)
    arrows: list[TacticsArrow] = Field(default_factory=list)
    passing_lanes: list[TacticsArrow] = Field(default_factory=list)
    annotations: list[TacticsAnnotation] = Field(default_factory=list)
    finding_refs: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_element_finding_refs(self) -> "TacticsBoardArtifact":
        allowed = set(self.finding_refs)
        elements = [
            *self.players,
            *self.zones,
            *self.arrows,
            *self.passing_lanes,
            *self.annotations,
        ]
        if any(not set(element.finding_refs).issubset(allowed) for element in elements):
            raise ValueError("board elements may only reference reviewed findings")
        return self

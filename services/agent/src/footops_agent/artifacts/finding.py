"""Auditable findings derived from deterministic metric artifacts."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from .base import StrictModel, utc_now


class FindingTimeRange(StrictModel):
    start_date: date
    end_date: date
    match_ids: list[int] = Field(min_length=3, max_length=10)


class FindingArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    finding_id: str
    statement: str = Field(min_length=1)
    claim_type: Literal["descriptive", "inference"]
    metric_refs: list[str] = Field(min_length=1)
    source_refs: list[str] = Field(min_length=1)
    time_range: FindingTimeRange
    direction: Literal["increase", "decrease", "stable"]
    confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class FindingSetArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    generator: Literal["footops-deterministic-finding-v1"] = (
        "footops-deterministic-finding-v1"
    )
    findings: list[FindingArtifact] = Field(min_length=1)

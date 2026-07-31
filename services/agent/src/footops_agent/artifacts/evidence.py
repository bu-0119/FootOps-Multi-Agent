"""Evidence references and deterministic review results."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel, utc_now


class EvidenceReference(StrictModel):
    evidence_id: str
    kind: Literal["source", "metric"]
    source_url: str | None = None
    match_id: int | None = None
    metric_name: str | None = None
    metric_value: float | int | None = None
    detail: str

    @model_validator(mode="after")
    def validate_reference_shape(self) -> "EvidenceReference":
        if self.kind == "source" and not self.source_url:
            raise ValueError("source evidence requires source_url")
        if self.kind == "metric" and (
            self.match_id is None
            or self.metric_name is None
            or self.metric_value is None
        ):
            raise ValueError(
                "metric evidence requires match_id, metric_name, and metric_value"
            )
        return self


class EvidenceSetArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    references: list[EvidenceReference] = Field(min_length=1)


class FindingEvidenceReview(StrictModel):
    finding_id: str
    status: Literal["supported", "needs_more_evidence", "rejected"]
    accepted_metric_refs: list[str] = Field(default_factory=list)
    accepted_source_refs: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class EvidenceReviewArtifact(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    reviewed_at: datetime = Field(default_factory=utc_now)
    gate_version: Literal["footops-evidence-gate-v1"] = (
        "footops-evidence-gate-v1"
    )
    overall_status: Literal["passed", "partial", "rejected"]
    support_rate: float = Field(ge=0, le=1)
    reviews: list[FindingEvidenceReview] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)

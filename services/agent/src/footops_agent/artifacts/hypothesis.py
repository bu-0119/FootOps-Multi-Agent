"""Grounded tactical hypotheses combining match findings and knowledge evidence."""

from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel


class TacticalHypothesisArtifact(StrictModel):
    """A bounded inference that must cite both match and knowledge evidence."""

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["grounded", "insufficient"]
    hypothesis: str = Field(min_length=1, max_length=2000)
    fact_refs: list[str] = Field(default_factory=list, max_length=12)
    metric_refs: list[str] = Field(default_factory=list, max_length=12)
    knowledge_refs: list[str] = Field(default_factory=list, max_length=12)
    limitations: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_grounding(self) -> "TacticalHypothesisArtifact":
        if self.status == "grounded" and (
            not self.metric_refs or not self.knowledge_refs
        ):
            raise ValueError(
                "grounded tactical hypothesis requires metric and knowledge references"
            )
        if self.status == "insufficient" and (
            self.metric_refs or self.knowledge_refs
        ):
            raise ValueError("insufficient hypothesis cannot expose partial citations")
        return self

"""Composable entry-routing plan before tools or agents are selected."""

from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel


class ExecutionPlanArtifact(StrictModel):
    """Declare independent data, knowledge, and orchestration requirements."""

    schema_version: Literal["1.0"] = "1.0"
    intent: Literal[
        "chat",
        "rule_qa",
        "tactical_knowledge",
        "metric_knowledge",
        "data_analysis",
        "hybrid_tactical_analysis",
    ]
    need_match_data: bool = False
    need_rule_rag: bool = False
    need_tactical_rag: bool = False
    need_metric_rag: bool = False
    need_multi_agent: bool = False
    scope_required: bool = False
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_requirements(self) -> "ExecutionPlanArtifact":
        if self.intent == "chat" and any(
            (
                self.need_match_data,
                self.need_rule_rag,
                self.need_tactical_rag,
                self.need_metric_rag,
                self.need_multi_agent,
                self.scope_required,
            )
        ):
            raise ValueError("chat plan cannot request tools or analysis scope")
        if self.scope_required and not self.need_match_data:
            raise ValueError("analysis scope is only required for match data")
        if self.intent == "rule_qa" and not self.need_rule_rag:
            raise ValueError("rule_qa requires rule knowledge retrieval")
        if self.intent == "tactical_knowledge" and not self.need_tactical_rag:
            raise ValueError("tactical knowledge intent requires tactical retrieval")
        if self.intent == "metric_knowledge" and not self.need_metric_rag:
            raise ValueError("metric knowledge intent requires metric retrieval")
        if self.intent == "data_analysis" and not self.need_match_data:
            raise ValueError("data analysis requires match data")
        if self.intent == "hybrid_tactical_analysis" and not (
            self.need_match_data
            and (self.need_rule_rag or self.need_tactical_rag or self.need_metric_rag)
        ):
            raise ValueError("hybrid analysis requires data and knowledge retrieval")
        return self

"""Versioned contracts for repeatable Agent comparison runs."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from footops_agent.artifacts import AgentModelUsage, AgentScopeHint, StrictModel
from footops_agent.artifacts.base import utc_now

type EvaluationMode = Literal[
    "deterministic",
    "direct_llm",
    "single_agent",
    "multi_agent",
]
type EvaluationStatus = Literal[
    "chat",
    "completed",
    "clarification_required",
    "unsupported",
    "error",
]


class GoldenTaskExpectation(StrictModel):
    """Desired user-visible behavior and Agent-specific tool requirements."""

    status: Literal["chat", "completed", "clarification_required", "unsupported"]
    require_workspace: bool
    required_agent_tools: list[str] = Field(default_factory=list)


class GoldenTask(StrictModel):
    task_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    scope_hint: AgentScopeHint = Field(default_factory=AgentScopeHint)
    expectation: GoldenTaskExpectation
    tags: list[str] = Field(default_factory=list)


class GoldenTaskSuite(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    suite_id: str = Field(min_length=1)
    description: str
    tasks: list[GoldenTask] = Field(min_length=1)


class EvaluationObservation(StrictModel):
    mode: EvaluationMode
    status: EvaluationStatus
    message: str
    duration_ms: float = Field(ge=0)
    model_called: bool
    model_name: str
    tool_sequence: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    finding_count: int = Field(default=0, ge=0)
    claim_support_rate: float | None = Field(default=None, ge=0, le=1)
    usage: AgentModelUsage | None = None
    stopping_reason: str
    error_type: str | None = None


class EvaluationAssertions(StrictModel):
    status_match: bool
    workspace_match: bool
    tool_sequence_match: bool | None = None
    supported_claims: bool | None = None
    no_unsupported_completion: bool


class EvaluationCaseResult(StrictModel):
    task_id: str
    mode: EvaluationMode
    passed: bool
    observation: EvaluationObservation
    assertions: EvaluationAssertions


class EvaluationSummary(StrictModel):
    mode: EvaluationMode
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    average_latency_ms: float = Field(ge=0)
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    tool_sequence_accuracy: float | None = Field(default=None, ge=0, le=1)
    average_claim_support_rate: float | None = Field(default=None, ge=0, le=1)
    unsupported_completion_count: int = Field(ge=0)
    error_count: int = Field(ge=0)


class EvaluationReport(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    report_id: str
    suite_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    results: list[EvaluationCaseResult]
    summaries: list[EvaluationSummary]
    notes: list[str] = Field(default_factory=list)

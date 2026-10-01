"""Contracts shared by the natural-language Agent runtime and harness."""

from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel


class AgentScopeHint(StrictModel):
    """Optional user-supplied constraints; every field may be inferred."""

    competition_id: int | None = Field(default=None, gt=0)
    season_id: int | None = Field(default=None, gt=0)
    player: str | None = None
    player_id: int | None = Field(default=None, gt=0)
    requested_window: int | None = Field(default=None, ge=2, le=10)

    @model_validator(mode="after")
    def validate_competition_pair(self) -> "AgentScopeHint":
        if (self.competition_id is None) != (self.season_id is None):
            raise ValueError("competition_id and season_id must be provided together")
        return self


class AgentConversationTurn(StrictModel):
    """One compact prior turn supplied to the stateless HTTP runtime."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AgentAnalysisInput(StrictModel):
    """One natural-language request entering the Agent harness."""

    question: str = Field(min_length=1)
    scope_hint: AgentScopeHint = Field(default_factory=AgentScopeHint)
    history: list[AgentConversationTurn] = Field(default_factory=list, max_length=12)


class ResolvedAgentScope(StrictModel):
    """The scope understood or resolved by the orchestration Agent."""

    competition_id: int | None = Field(default=None, gt=0)
    season_id: int | None = Field(default=None, gt=0)
    competition_name: str | None = None
    season_name: str | None = None
    player: str | None = None
    player_id: int | None = Field(default=None, gt=0)
    requested_window: int | None = Field(default=None, ge=2, le=10)


class AgentDecision(StrictModel):
    """Schema-validated final decision produced by the AgentScope loop."""

    action: Literal["chat", "completed", "clarification_required", "unsupported"]
    message: str = Field(min_length=1)
    resolved_scope: ResolvedAgentScope = Field(default_factory=ResolvedAgentScope)
    limitations: list[str] = Field(default_factory=list, max_length=8)


class AgentToolTrace(StrictModel):
    """Auditable business-level trace without exposing model reasoning."""

    sequence: int = Field(ge=1)
    tool_name: str
    status: Literal["completed", "not_found", "insufficient", "unsupported", "error"]
    summary: str


class AgentModelUsage(StrictModel):
    """Provider-reported token usage and optional configured cost estimate."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    pricing_basis: str | None = None

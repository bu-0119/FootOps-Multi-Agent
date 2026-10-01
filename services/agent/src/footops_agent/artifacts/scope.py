"""Strongly typed output from the dedicated analysis ScopeAgent."""

from typing import Literal

from pydantic import Field, model_validator

from .agent_run import ResolvedAgentScope
from .base import StrictModel


class ScopeResolutionArtifact(StrictModel):
    """A catalog-grounded scope or one bounded clarification request."""

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["resolved", "clarification_required"]
    message: str = Field(min_length=1)
    scope: ResolvedAgentScope = Field(default_factory=ResolvedAgentScope)

    @model_validator(mode="after")
    def validate_resolved_scope(self) -> "ScopeResolutionArtifact":
        if self.status != "resolved":
            return self
        values = (
            self.scope.competition_id,
            self.scope.season_id,
            self.scope.player,
            self.scope.player_id,
            self.scope.requested_window,
        )
        if any(value is None for value in values):
            raise ValueError("resolved scope requires competition, player, and window")
        return self

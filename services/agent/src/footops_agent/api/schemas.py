"""HTTP request and response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from footops_agent.artifacts import (
    AgentConversationTurn,
    AgentDecision,
    AgentModelUsage,
    AgentScopeHint,
    AgentToolTrace,
    AnalysisPlan,
    AnalysisWorkspace,
    CompetitionSeason,
    CoverageAuditArtifact,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    ExecutionPlanArtifact,
    FindingSetArtifact,
    KnowledgeAnswerArtifact,
    KnowledgeEvidenceArtifact,
    PlayerCatalogEntry,
    PlayerRoleMetricArtifact,
    ScopeResolutionArtifact,
)


class ApiModel(BaseModel):
    """Base API model with a stable JSON naming policy."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: Literal["footops-agent"] = "footops-agent"


class LlmStatusResponse(ApiModel):
    status: Literal["ready", "unavailable"]
    mode: Literal["mock", "deepseek"]
    provider: Literal["none", "deepseek"]
    model: str
    key_configured: bool
    agentscope_version: str
    message: str


class AnalysisPlanRequest(ApiModel):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        """Reject inputs containing only whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class AgentAnalysisRequest(AnalysisPlanRequest):
    """Natural-language-first request with optional scope constraints."""

    competition_id: int | None = Field(default=None, gt=0)
    season_id: int | None = Field(default=None, gt=0)
    player: str | None = None
    player_id: int | None = Field(default=None, gt=0)
    requested_window: int | None = Field(default=None, ge=2, le=10)
    history: list[AgentConversationTurn] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_scope_hint(self) -> "AgentAnalysisRequest":
        if (self.competition_id is None) != (self.season_id is None):
            raise ValueError("competition_id and season_id must be provided together")
        return self

    def to_scope_hint(self) -> AgentScopeHint:
        return AgentScopeHint(
            competition_id=self.competition_id,
            season_id=self.season_id,
            player=self.player.strip() if self.player else None,
            player_id=self.player_id,
            requested_window=self.requested_window,
        )


class AnalysisPlanResponse(ApiModel):
    run_id: str
    status: Literal["planned"] = "planned"
    mode: Literal["mock", "deepseek"]
    provider: Literal["none", "deepseek"]
    model: str
    model_called: bool
    data_retrieved: bool = False
    real_conclusions_generated: bool = False
    message: str
    plan: AnalysisPlan


class PlayerDataRequest(ApiModel):
    competition_id: int = Field(gt=0)
    season_id: int = Field(gt=0)
    player: str = Field(min_length=1)
    player_id: int | None = Field(default=None, gt=0)
    requested_window: int = Field(default=5, ge=2, le=10)

    @field_validator("player")
    @classmethod
    def strip_player(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("player must not be blank")
        return value


class AnalysisWorkspaceCreateRequest(PlayerDataRequest):
    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def strip_workspace_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class CompetitionCatalogResponse(ApiModel):
    status: Literal["ready"] = "ready"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    competitions: list[CompetitionSeason]


class PlayerCatalogResponse(ApiModel):
    status: Literal["ready"] = "ready"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    competition: CompetitionSeason
    players: list[PlayerCatalogEntry]


class DataCoverageAuditResponse(ApiModel):
    status: Literal["audited"] = "audited"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: Literal[False] = False
    data_retrieved: Literal[True] = True
    real_conclusions_generated: Literal[False] = False
    audit: CoverageAuditArtifact


class PlayerRoleMetricsResponse(ApiModel):
    status: Literal["calculated"] = "calculated"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: Literal[False] = False
    data_retrieved: Literal[True] = True
    real_conclusions_generated: Literal[False] = False
    audit: CoverageAuditArtifact
    metrics: PlayerRoleMetricArtifact


class PlayerRoleFindingReviewResponse(ApiModel):
    status: Literal["reviewed"] = "reviewed"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: Literal[False] = False
    data_retrieved: Literal[True] = True
    findings_generated: Literal[True] = True
    evidence_reviewed: Literal[True] = True
    real_conclusions_generated: Literal[False] = False
    audit: CoverageAuditArtifact
    metrics: PlayerRoleMetricArtifact
    findings: FindingSetArtifact
    evidence: EvidenceSetArtifact
    evidence_review: EvidenceReviewArtifact


class AnalysisWorkspaceResponse(ApiModel):
    status: Literal["ready"] = "ready"
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: Literal[False] = False
    data_retrieved: Literal[True] = True
    findings_generated: Literal[True] = True
    evidence_reviewed: Literal[True] = True
    tactics_board_generated: bool
    real_conclusions_generated: Literal[False] = False
    workspace: AnalysisWorkspace


class MultiAgentTraceEvent(ApiModel):
    """Public collaboration trace without model reasoning or raw payloads."""

    sequence: int = Field(ge=1)
    event_type: str
    actor: str
    task_id: str = ""
    artifact_id: str = ""
    message: str = ""


class MultiAgentAnalysisResponse(ApiModel):
    """Outcome of one scoped event-driven multi-agent run."""

    run_id: str
    status: Literal["ready"] = "ready"
    runtime: Literal["footops_event_driven_multi_agent_v1"] = (
        "footops_event_driven_multi_agent_v1"
    )
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: Literal[False] = False
    agents: list[str]
    rounds: int = Field(ge=1)
    trace: list[MultiAgentTraceEvent]
    workspace: AnalysisWorkspace


class MultiAgentRunResponse(ApiModel):
    """Natural-language ScopeAgent result and optional multi-agent workspace."""

    run_id: str
    status: Literal["completed", "clarification_required", "unsupported"]
    runtime: Literal["footops_event_driven_multi_agent_v1"] = (
        "footops_event_driven_multi_agent_v1"
    )
    provider: Literal["statsbomb-open-data"] = "statsbomb-open-data"
    model_called: bool
    model: str
    message: str
    duration_ms: float = Field(ge=0)
    execution_plan: ExecutionPlanArtifact
    scope: ScopeResolutionArtifact | None = None
    scope_trace: list[AgentToolTrace] = Field(default_factory=list)
    usage: AgentModelUsage | None = None
    agents: list[str] = Field(default_factory=list)
    rounds: int = Field(default=0, ge=0)
    trace: list[MultiAgentTraceEvent] = Field(default_factory=list)
    workspace: AnalysisWorkspace | None = None


class ErrorBody(ApiModel):
    code: str
    message: str


class MultiAgentStreamEvent(ApiModel):
    """Versioned user-facing events for a natural-language multi-agent run."""

    schema_version: Literal["1.0"] = "1.0"
    event: Literal[
        "multi_agent.started",
        "multi_agent.collaboration",
        "multi_agent.completed",
        "multi_agent.clarification_required",
        "multi_agent.unsupported",
        "multi_agent.error",
    ]
    request_id: str
    sequence: int = Field(ge=1)
    message: str
    trace: MultiAgentTraceEvent | None = None
    response: MultiAgentRunResponse | None = None
    error: ErrorBody | None = None


class AgentAnalysisResponse(ApiModel):
    """Outcome of one bounded AgentScope orchestration run."""

    run_id: str
    status: Literal["chat", "completed", "clarification_required", "unsupported"]
    mode: Literal["mock", "deepseek"]
    provider: Literal["none", "deepseek"]
    model: str
    model_called: bool
    data_retrieved: bool
    message: str
    decision: AgentDecision
    trace: list[AgentToolTrace] = Field(default_factory=list)
    duration_ms: float = Field(ge=0)
    execution_plan: ExecutionPlanArtifact
    usage: AgentModelUsage | None = None
    knowledge_evidence: KnowledgeEvidenceArtifact | None = None
    knowledge_answer: KnowledgeAnswerArtifact | None = None
    workspace: AnalysisWorkspace | None = None


class AnalysisStreamEvent(ApiModel):
    """Versioned business event emitted while creating a workspace."""

    schema_version: Literal["1.0"] = "1.0"
    event: Literal["analysis.status", "analysis.completed", "analysis.error"]
    request_id: str
    sequence: int = Field(ge=1)
    message: str
    response: AnalysisWorkspaceResponse | None = None
    error: ErrorBody | None = None


class ErrorResponse(ApiModel):
    run_id: str | None = None
    status: Literal["error"] = "error"
    error: ErrorBody


class AgentRunStreamEvent(ApiModel):
    """Versioned business event emitted by the Agent analysis harness."""

    schema_version: Literal["1.0"] = "1.0"
    event: Literal[
        "agent.started",
        "agent.tool.completed",
        "agent.chat_completed",
        "agent.completed",
        "agent.clarification_required",
        "agent.unsupported",
        "agent.error",
    ]
    request_id: str
    sequence: int = Field(ge=1)
    message: str
    trace: AgentToolTrace | None = None
    response: AgentAnalysisResponse | None = None
    error: ErrorBody | None = None

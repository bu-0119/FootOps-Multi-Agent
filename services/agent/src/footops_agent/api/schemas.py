"""HTTP request and response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from footops_agent.artifacts import (
    AnalysisPlan,
    AnalysisWorkspace,
    CoverageAuditArtifact,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingSetArtifact,
    PlayerRoleMetricArtifact,
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
    requested_window: int = Field(default=5, ge=3, le=10)

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
    tactics_board_generated: Literal[True] = True
    real_conclusions_generated: Literal[False] = False
    workspace: AnalysisWorkspace


class ErrorBody(ApiModel):
    code: str
    message: str


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

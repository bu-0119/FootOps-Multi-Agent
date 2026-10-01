"""Persistent workspace contract for the FootOps golden task."""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import Field

from .base import StrictModel, utc_now
from .evidence import EvidenceReviewArtifact, EvidenceSetArtifact
from .finding import FindingArtifact
from .match_data import CoverageAuditArtifact
from .metrics import PlayerRoleMetricArtifact
from .tactics import TacticsBoardArtifact


class AnalysisScope(StrictModel):
    competition_id: int = Field(gt=0)
    season_id: int = Field(gt=0)
    player: str = Field(min_length=1)
    player_id: int = Field(gt=0)
    team: str | None = None
    match_ids: list[int] = Field(min_length=2, max_length=10)


class AnalysisRequestArtifact(StrictModel):
    question: str = Field(min_length=1)
    scope: AnalysisScope


type WorkspaceStatus = Literal[
    "created",
    "data_ready",
    "metrics_ready",
    "findings_ready",
    "evidence_reviewed",
    "tactics_ready",
    "completed",
    "insufficient_data",
    "failed",
]


class AnalysisWorkspace(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    workspace_id: str = Field(default_factory=lambda: uuid4().hex)
    status: WorkspaceStatus = "created"
    request: AnalysisRequestArtifact
    coverage: CoverageAuditArtifact | None = None
    metrics: PlayerRoleMetricArtifact | None = None
    findings: list[FindingArtifact] = Field(default_factory=list)
    evidence: EvidenceSetArtifact | None = None
    evidence_review: EvidenceReviewArtifact | None = None
    tactics_board: TacticsBoardArtifact | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

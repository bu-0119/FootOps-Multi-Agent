"""Versioned Pydantic artifact schemas."""

from .base import SourceReference, StrictModel
from .evidence import (
    EvidenceReference,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingEvidenceReview,
)
from .finding import FindingArtifact, FindingSetArtifact, FindingTimeRange
from .match_data import (
    CompetitionSeason,
    CoverageAuditArtifact,
    MatchDataSnapshot,
    MatchRef,
    PitchLocation,
    PlayerEvent,
    PlayerMatchCoverage,
    PlayerRef,
    PositionInterval,
    TeamRef,
)
from .metrics import MatchRoleMetrics, PlayerRoleMetricArtifact
from .planning import AnalysisPlan, AnalysisPlanStep, QuestionUnderstanding
from .tactics import (
    BoardPoint,
    TacticsAnnotation,
    TacticsArrow,
    TacticsBoardArtifact,
    TacticsPlayerMarker,
    TacticsZone,
)
from .workspace import (
    AnalysisRequestArtifact,
    AnalysisScope,
    AnalysisWorkspace,
    WorkspaceStatus,
)

__all__ = [
    "AnalysisPlan",
    "AnalysisPlanStep",
    "AnalysisRequestArtifact",
    "AnalysisScope",
    "AnalysisWorkspace",
    "BoardPoint",
    "CompetitionSeason",
    "CoverageAuditArtifact",
    "EvidenceReference",
    "EvidenceReviewArtifact",
    "EvidenceSetArtifact",
    "FindingArtifact",
    "FindingEvidenceReview",
    "FindingSetArtifact",
    "FindingTimeRange",
    "MatchDataSnapshot",
    "MatchRef",
    "MatchRoleMetrics",
    "PitchLocation",
    "PlayerEvent",
    "PlayerMatchCoverage",
    "PlayerRef",
    "PlayerRoleMetricArtifact",
    "PositionInterval",
    "QuestionUnderstanding",
    "SourceReference",
    "StrictModel",
    "TeamRef",
    "TacticsAnnotation",
    "TacticsArrow",
    "TacticsBoardArtifact",
    "TacticsPlayerMarker",
    "TacticsZone",
    "WorkspaceStatus",
]

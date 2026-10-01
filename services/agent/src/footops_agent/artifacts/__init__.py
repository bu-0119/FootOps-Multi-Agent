"""Versioned Pydantic artifact schemas."""

from .agent_run import (
    AgentAnalysisInput,
    AgentConversationTurn,
    AgentDecision,
    AgentModelUsage,
    AgentScopeHint,
    AgentToolTrace,
    ResolvedAgentScope,
)
from .base import SourceReference, StrictModel
from .evidence import (
    EvidenceReference,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingEvidenceReview,
)
from .execution_plan import ExecutionPlanArtifact
from .finding import FindingArtifact, FindingSetArtifact, FindingTimeRange
from .hypothesis import TacticalHypothesisArtifact
from .knowledge import (
    KnowledgeAnswerArtifact,
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceReference,
)
from .match_data import (
    CompetitionSeason,
    CoverageAuditArtifact,
    MatchDataSnapshot,
    MatchRef,
    PitchLocation,
    PlayerCatalogEntry,
    PlayerEvent,
    PlayerMatchCoverage,
    PlayerRef,
    PositionInterval,
    TeamRef,
)
from .metrics import MatchRoleMetrics, PlayerRoleMetricArtifact
from .planning import AnalysisPlan, AnalysisPlanStep, QuestionUnderstanding
from .scope import ScopeResolutionArtifact
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
    "AgentAnalysisInput",
    "AgentConversationTurn",
    "AgentDecision",
    "AgentModelUsage",
    "AgentScopeHint",
    "AgentToolTrace",
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
    "ExecutionPlanArtifact",
    "FindingArtifact",
    "FindingEvidenceReview",
    "FindingSetArtifact",
    "FindingTimeRange",
    "KnowledgeAnswerArtifact",
    "KnowledgeEvidenceArtifact",
    "KnowledgeEvidenceReference",
    "MatchDataSnapshot",
    "MatchRef",
    "MatchRoleMetrics",
    "PitchLocation",
    "PlayerEvent",
    "PlayerCatalogEntry",
    "PlayerMatchCoverage",
    "PlayerRef",
    "PlayerRoleMetricArtifact",
    "PositionInterval",
    "QuestionUnderstanding",
    "ResolvedAgentScope",
    "ScopeResolutionArtifact",
    "SourceReference",
    "StrictModel",
    "TeamRef",
    "TacticalHypothesisArtifact",
    "TacticsAnnotation",
    "TacticsArrow",
    "TacticsBoardArtifact",
    "TacticsPlayerMarker",
    "TacticsZone",
    "WorkspaceStatus",
]

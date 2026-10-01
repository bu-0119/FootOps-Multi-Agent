"""Domain payloads exchanged through the collaboration board."""

from dataclasses import dataclass

from footops_agent.artifacts import (
    CoverageAuditArtifact,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingSetArtifact,
    KnowledgeEvidenceArtifact,
    PlayerRoleMetricArtifact,
    TacticalHypothesisArtifact,
    TacticsBoardArtifact,
)


@dataclass(frozen=True)
class MultiAgentAnalysisRequest:
    question: str
    competition_id: int
    season_id: int
    player_query: str
    requested_window: int = 5
    player_id: int | None = None
    requires_knowledge: bool = False
    revision_budget: int = 1


@dataclass(frozen=True)
class DataBundle:
    audit: CoverageAuditArtifact
    metrics: PlayerRoleMetricArtifact


@dataclass(frozen=True)
class FindingBundle:
    findings: FindingSetArtifact
    evidence: EvidenceSetArtifact


@dataclass(frozen=True)
class ReviewBundle:
    review: EvidenceReviewArtifact


@dataclass(frozen=True)
class TacticsBundle:
    tactics_board: TacticsBoardArtifact


@dataclass(frozen=True)
class KnowledgeBundle:
    evidence: KnowledgeEvidenceArtifact
    hypothesis: TacticalHypothesisArtifact

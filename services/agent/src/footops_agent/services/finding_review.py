"""Vertical data-to-finding-to-evidence-review use case."""

from footops_agent.artifacts import (
    CoverageAuditArtifact,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingSetArtifact,
    PlayerRoleMetricArtifact,
)
from footops_agent.providers import FootballDataProvider

from .evidence_gate import EvidenceGate
from .finding_builder import DeterministicFindingBuilder
from .player_role import PlayerRoleAnalysisService


class PlayerRoleFindingReviewService:
    def __init__(
        self,
        provider: FootballDataProvider,
        finding_builder: DeterministicFindingBuilder | None = None,
        evidence_gate: EvidenceGate | None = None,
    ) -> None:
        self.analysis = PlayerRoleAnalysisService(provider)
        self.finding_builder = finding_builder or DeterministicFindingBuilder()
        self.evidence_gate = evidence_gate or EvidenceGate()

    def review(
        self,
        competition_id: int,
        season_id: int,
        player_query: str,
        requested_window: int = 5,
        player_id: int | None = None,
    ) -> tuple[
        CoverageAuditArtifact,
        PlayerRoleMetricArtifact,
        FindingSetArtifact,
        EvidenceSetArtifact,
        EvidenceReviewArtifact,
    ]:
        audit, metrics = self.analysis.calculate(
            competition_id,
            season_id,
            player_query,
            requested_window,
            player_id,
        )
        findings, evidence = self.finding_builder.build(metrics)
        review = self.evidence_gate.review(findings, evidence, metrics)
        return audit, metrics, findings, evidence, review

"""Analysis workspace lifecycle for the player-role golden task."""

from collections.abc import Mapping

from footops_agent.artifacts import (
    AnalysisRequestArtifact,
    AnalysisScope,
    AnalysisWorkspace,
    CoverageAuditArtifact,
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingArtifact,
    PlayerRoleMetricArtifact,
    TacticsBoardArtifact,
    WorkspaceStatus,
)
from footops_agent.artifacts.base import utc_now
from footops_agent.providers import FootballDataProvider
from footops_agent.repositories import (
    AnalysisWorkspaceRepository,
    WorkspaceNotFoundError,
)

from .finding_review import PlayerRoleFindingReviewService
from .tactics_board import DeterministicTacticsBoardBuilder


class InvalidWorkspaceTransitionError(ValueError):
    """Raised when workspace lifecycle rules are violated."""


class WorkspaceStateMachine:
    """Validate state transitions and the artifacts required by each state."""

    _allowed: Mapping[WorkspaceStatus, frozenset[WorkspaceStatus]] = {
        "created": frozenset({"data_ready", "insufficient_data", "failed"}),
        "data_ready": frozenset({"metrics_ready", "failed"}),
        "metrics_ready": frozenset({"findings_ready", "failed"}),
        "findings_ready": frozenset({"evidence_reviewed", "failed"}),
        "evidence_reviewed": frozenset({"tactics_ready", "failed"}),
        "tactics_ready": frozenset({"completed", "failed"}),
        "completed": frozenset(),
        "insufficient_data": frozenset(),
        "failed": frozenset(),
    }

    def transition(
        self,
        workspace: AnalysisWorkspace,
        target: WorkspaceStatus,
        *,
        coverage: CoverageAuditArtifact | None = None,
        metrics: PlayerRoleMetricArtifact | None = None,
        findings: list[FindingArtifact] | None = None,
        evidence: EvidenceSetArtifact | None = None,
        evidence_review: EvidenceReviewArtifact | None = None,
        tactics_board: TacticsBoardArtifact | None = None,
    ) -> AnalysisWorkspace:
        if target not in self._allowed[workspace.status]:
            raise InvalidWorkspaceTransitionError(
                f"cannot transition workspace from {workspace.status} to {target}"
            )

        values = workspace.model_dump(mode="python")
        updates = {
            "coverage": coverage,
            "metrics": metrics,
            "findings": findings,
            "evidence": evidence,
            "evidence_review": evidence_review,
            "tactics_board": tactics_board,
        }
        values.update(
            {key: value for key, value in updates.items() if value is not None}
        )
        values.update(status=target, updated_at=utc_now())
        candidate = AnalysisWorkspace.model_validate(values)
        self._validate_required_artifacts(candidate)
        return candidate

    @staticmethod
    def _validate_required_artifacts(workspace: AnalysisWorkspace) -> None:
        state_order = {
            "created": 0,
            "data_ready": 1,
            "metrics_ready": 2,
            "findings_ready": 3,
            "evidence_reviewed": 4,
            "tactics_ready": 5,
            "completed": 6,
        }
        position = state_order.get(workspace.status)
        if position is None:
            return
        if position >= 1 and workspace.coverage is None:
            raise InvalidWorkspaceTransitionError("data_ready requires coverage")
        if position >= 2 and workspace.metrics is None:
            raise InvalidWorkspaceTransitionError("metrics_ready requires metrics")
        if position >= 3 and not workspace.findings:
            raise InvalidWorkspaceTransitionError("findings_ready requires findings")
        if position >= 4 and (
            workspace.evidence is None or workspace.evidence_review is None
        ):
            raise InvalidWorkspaceTransitionError(
                "evidence_reviewed requires evidence and review"
            )
        if position >= 5 and workspace.tactics_board is None:
            raise InvalidWorkspaceTransitionError(
                "tactics_ready requires a tactics board"
            )


class AnalysisWorkspaceService:
    """Create and retrieve one auditable player-role analysis workspace."""

    def __init__(
        self,
        provider: FootballDataProvider,
        repository: AnalysisWorkspaceRepository,
        state_machine: WorkspaceStateMachine | None = None,
        tactics_builder: DeterministicTacticsBoardBuilder | None = None,
    ) -> None:
        self.review_service = PlayerRoleFindingReviewService(provider)
        self.repository = repository
        self.state_machine = state_machine or WorkspaceStateMachine()
        self.tactics_builder = tactics_builder or DeterministicTacticsBoardBuilder()

    def create(
        self,
        question: str,
        competition_id: int,
        season_id: int,
        player_query: str,
        requested_window: int = 5,
    ) -> AnalysisWorkspace:
        audit, metrics, finding_set, evidence, review = self.review_service.review(
            competition_id,
            season_id,
            player_query,
            requested_window,
        )
        selected_ids = set(audit.suggested_match_ids)
        selected_appearance = next(
            item
            for item in audit.appearances
            if item.match.match_id in selected_ids
        )
        request = AnalysisRequestArtifact(
            question=question,
            scope=AnalysisScope(
                competition_id=competition_id,
                season_id=season_id,
                player=metrics.player.player_nickname or metrics.player.player_name,
                team=selected_appearance.team.team_name,
                match_ids=audit.suggested_match_ids,
            ),
        )
        workspace = self.repository.save(AnalysisWorkspace(request=request))
        workspace = self._save_transition(workspace, "data_ready", coverage=audit)
        workspace = self._save_transition(workspace, "metrics_ready", metrics=metrics)
        workspace = self._save_transition(
            workspace,
            "findings_ready",
            findings=finding_set.findings,
        )
        workspace = self._save_transition(
            workspace,
            "evidence_reviewed",
            evidence=evidence,
            evidence_review=review,
        )
        tactics_board = self.tactics_builder.build(
            metrics,
            finding_set.findings,
            review,
        )
        return self._save_transition(
            workspace,
            "tactics_ready",
            tactics_board=tactics_board,
        )

    def get(self, workspace_id: str) -> AnalysisWorkspace:
        workspace = self.repository.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    def _save_transition(
        self,
        workspace: AnalysisWorkspace,
        target: WorkspaceStatus,
        **artifacts: object,
    ) -> AnalysisWorkspace:
        transitioned = self.state_machine.transition(
            workspace,
            target,
            **artifacts,  # type: ignore[arg-type]
        )
        return self.repository.save(transitioned)

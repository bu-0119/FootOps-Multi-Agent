"""Claim-based coordinator adapted from the MindBridge learning project."""

from collections.abc import Callable
from typing import Protocol

from .events import (
    CollaborationArtifact,
    CollaborationBoard,
    CollaborationEvent,
    CollaborationEventType,
    CollaborationTask,
    CollaborationTaskPriority,
)
from .registry import AgentCapability, AgentRegistry


class CoordinatorRole(Protocol):
    name: str


class EventDrivenCoordinator:
    """Derive work from missing artifacts and accept only reviewed output."""

    def __init__(
        self,
        registry: AgentRegistry,
        coordinator_agent: CoordinatorRole,
        finalizer: Callable[[CollaborationBoard], object],
        max_rounds: int = 6,
    ) -> None:
        self.registry = registry
        self.coordinator_agent = coordinator_agent
        self.finalizer = finalizer
        self.max_rounds = max_rounds

    def run(self, board: CollaborationBoard) -> CollaborationBoard:
        board = board.append_event(
            CollaborationEvent(
                event_type=CollaborationEventType.RUN_STARTED,
                actor=self.coordinator_agent.name,
                message="analysis request published to collaboration board",
            )
        )
        for round_number in range(1, self.max_rounds + 1):
            board = board.append_event(
                CollaborationEvent(
                    event_type=CollaborationEventType.ROUND_STARTED,
                    actor=self.coordinator_agent.name,
                    message=f"round={round_number}",
                    metadata={"round": round_number},
                )
            )
            board = self._derive_missing_work(board)
            board = self._try_accept_final(board)
            if board.final_artifact_id:
                return board

            candidates = self._claim_candidates(board)
            if not candidates:
                break
            for task, candidate in candidates:
                claimed = task.claim(candidate.agent.profile.name)
                board = board.add_task(claimed).append_event(
                    CollaborationEvent(
                        event_type=CollaborationEventType.TASK_CLAIMED,
                        actor=candidate.agent.profile.name,
                        task_id=task.task_id,
                        message=candidate.decision.reason,
                        metadata={"confidence": candidate.decision.confidence},
                    )
                )
                result = candidate.agent.act(claimed, board)
                board = board.apply_turn_result(
                    claimed,
                    candidate.agent.profile.name,
                    result,
                )

            board = self._derive_missing_work(board)
            board = self._try_accept_final(board)
            if board.final_artifact_id:
                return board

        return board.append_event(
            CollaborationEvent(
                event_type=CollaborationEventType.BUDGET_EXHAUSTED,
                actor=self.coordinator_agent.name,
                message="multi-agent round budget exhausted before final acceptance",
            )
        )

    def _derive_missing_work(
        self,
        board: CollaborationBoard,
    ) -> CollaborationBoard:
        if board.latest_artifact("data_bundle") is None:
            return self._ensure_task(
                board,
                "task:data",
                "Load player events and calculate metrics",
                AgentCapability.DATA,
                CollaborationTaskPriority.HIGH,
                "data",
            )
        if board.latest_artifact("finding_bundle") is None:
            return self._ensure_task(
                board,
                "task:findings",
                "Generate candidate tactical findings",
                AgentCapability.TACTICAL,
                CollaborationTaskPriority.HIGH,
                "findings",
            )
        findings = board.latest_artifact("finding_bundle")
        review = board.latest_artifact("review_bundle")
        if review is None or (
            findings is not None
            and review.revision_round < findings.revision_round
        ):
            revision_round = findings.revision_round if findings is not None else 0
            return self._ensure_task(
                board,
                f"task:evidence-review:{revision_round}",
                "Review finding evidence independently",
                AgentCapability.EVIDENCE,
                CollaborationTaskPriority.CRITICAL,
                "evidence_review",
                revision_round=revision_round,
            )
        if review.payload.review.overall_status != "passed":
            revision_round = review.revision_round + 1
            if revision_round <= board.request.revision_budget:
                return self._ensure_task(
                    board,
                    f"task:revision:{revision_round}",
                    "Revise findings using evidence critique",
                    AgentCapability.TACTICAL,
                    CollaborationTaskPriority.HIGH,
                    "revision",
                    revision_round=revision_round,
                )
            return board
        if board.request.requires_knowledge and board.latest_artifact(
            "knowledge_bundle"
        ) is None:
            return self._ensure_task(
                board,
                "task:knowledge",
                "Ground findings in versioned tactical knowledge",
                AgentCapability.KNOWLEDGE,
                CollaborationTaskPriority.HIGH,
                "knowledge",
            )
        if self._requires_tactics(board) and board.latest_artifact(
            "tactics_bundle"
        ) is None:
            return self._ensure_task(
                board,
                "task:tactics",
                "Project approved findings onto the tactics board",
                AgentCapability.TACTICAL,
                CollaborationTaskPriority.NORMAL,
                "tactics",
            )
        return board

    def _ensure_task(
        self,
        board: CollaborationBoard,
        task_id: str,
        title: str,
        capability: AgentCapability,
        priority: CollaborationTaskPriority,
        kind: str,
        revision_round: int = 0,
    ) -> CollaborationBoard:
        if task_id in board.tasks:
            return board
        task = CollaborationTask(
            task_id=task_id,
            title=title,
            capability=capability.value,
            priority=priority,
            metadata={"kind": kind, "revision_round": revision_round},
        )
        return board.add_task(task).append_event(
            CollaborationEvent(
                event_type=CollaborationEventType.TASK_CREATED,
                actor=self.coordinator_agent.name,
                task_id=task.task_id,
                message=task.title,
            )
        )

    def _claim_candidates(self, board: CollaborationBoard):
        selected = []
        for task in sorted(
            board.open_tasks(),
            key=lambda item: item.priority.value,
            reverse=True,
        ):
            candidates = self.registry.candidates_for(task, board)
            if candidates:
                selected.append((task, candidates[0]))
        return selected

    def _try_accept_final(
        self,
        board: CollaborationBoard,
    ) -> CollaborationBoard:
        if board.final_artifact_id:
            return board
        required = ["data_bundle", "finding_bundle", "review_bundle"]
        if any(board.latest_artifact(kind) is None for kind in required):
            return board
        review = board.latest_artifact("review_bundle")
        if review is None or review.payload.review.overall_status != "passed":
            return board
        if self._requires_tactics(board) and board.latest_artifact(
            "tactics_bundle"
        ) is None:
            return board
        if board.request.requires_knowledge:
            knowledge = board.latest_artifact("knowledge_bundle")
            if knowledge is None or knowledge.payload.hypothesis.status != "grounded":
                return board

        workspace = self.finalizer(board)
        artifact = CollaborationArtifact(
            artifact_id=f"{self.coordinator_agent.name}:workspace:{board.run_id}",
            owner=self.coordinator_agent.name,
            kind="workspace",
            payload=workspace,
            confidence=1.0,
        )
        board = board.add_artifact(artifact)
        return board.accept_final(
            artifact.artifact_id,
            self.coordinator_agent.name,
            "accepted after EvidenceAgent approval and required tactics projection",
        )

    @staticmethod
    def _requires_tactics(board: CollaborationBoard) -> bool:
        findings = board.latest_artifact("finding_bundle")
        if findings is None:
            return False
        return any(
            item.finding_id == "finding:average_touch_x"
            for item in findings.payload.findings.findings
        )

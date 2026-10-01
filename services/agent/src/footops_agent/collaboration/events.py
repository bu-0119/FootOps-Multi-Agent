"""Immutable collaboration protocol for the FootOps multi-agent runtime."""

from dataclasses import dataclass, field, replace
from enum import Enum, StrEnum
from typing import Any


class CollaborationEventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    ROUND_STARTED = "ROUND_STARTED"
    TASK_CREATED = "TASK_CREATED"
    TASK_CLAIMED = "TASK_CLAIMED"
    TASK_CLOSED = "TASK_CLOSED"
    ARTIFACT_PUBLISHED = "ARTIFACT_PUBLISHED"
    CRITIQUE_CREATED = "CRITIQUE_CREATED"
    REVISION_PUBLISHED = "REVISION_PUBLISHED"
    FINAL_ACCEPTED = "FINAL_ACCEPTED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class CollaborationTaskStatus(StrEnum):
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    CLOSED = "CLOSED"


class CollaborationTaskPriority(int, Enum):
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class CollaborationTask:
    task_id: str
    title: str
    capability: str
    priority: CollaborationTaskPriority = CollaborationTaskPriority.NORMAL
    status: CollaborationTaskStatus = CollaborationTaskStatus.OPEN
    claimed_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def claim(self, agent_name: str) -> "CollaborationTask":
        return replace(
            self,
            status=CollaborationTaskStatus.CLAIMED,
            claimed_by=agent_name,
        )

    def close(self) -> "CollaborationTask":
        return replace(self, status=CollaborationTaskStatus.CLOSED)


@dataclass(frozen=True)
class CollaborationArtifact:
    artifact_id: str
    owner: str
    kind: str
    payload: Any
    task_id: str = ""
    confidence: float = 1.0
    revision_round: int = 0


@dataclass(frozen=True)
class CollaborationEvent:
    event_type: CollaborationEventType
    actor: str
    task_id: str = ""
    artifact_id: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CollaborationTurnResult:
    artifacts: tuple[CollaborationArtifact, ...] = field(default_factory=tuple)
    close_task: bool = True


@dataclass(frozen=True)
class CollaborationBoard:
    run_id: str
    request: Any
    tasks: dict[str, CollaborationTask] = field(default_factory=dict)
    artifacts: tuple[CollaborationArtifact, ...] = field(default_factory=tuple)
    events: tuple[CollaborationEvent, ...] = field(default_factory=tuple)
    final_artifact_id: str = ""

    def add_task(self, task: CollaborationTask) -> "CollaborationBoard":
        tasks = dict(self.tasks)
        tasks[task.task_id] = task
        return replace(self, tasks=tasks)

    def append_event(self, event: CollaborationEvent) -> "CollaborationBoard":
        return replace(self, events=(*self.events, event))

    def add_artifact(
        self,
        artifact: CollaborationArtifact,
    ) -> "CollaborationBoard":
        board = replace(self, artifacts=(*self.artifacts, artifact)).append_event(
            CollaborationEvent(
                event_type=CollaborationEventType.ARTIFACT_PUBLISHED,
                actor=artifact.owner,
                task_id=artifact.task_id,
                artifact_id=artifact.artifact_id,
                message=artifact.kind,
                metadata={"confidence": artifact.confidence},
            )
        )
        if artifact.kind == "review_bundle":
            review = getattr(artifact.payload, "review", None)
            if review is not None and review.overall_status != "passed":
                board = board.append_event(
                    CollaborationEvent(
                        event_type=CollaborationEventType.CRITIQUE_CREATED,
                        actor=artifact.owner,
                        task_id=artifact.task_id,
                        artifact_id=artifact.artifact_id,
                        message="evidence review requires tactical revision",
                        metadata={
                            "revision_round": artifact.revision_round,
                            "review_status": review.overall_status,
                        },
                    )
                )
        if artifact.revision_round > 0:
            board = board.append_event(
                CollaborationEvent(
                    event_type=CollaborationEventType.REVISION_PUBLISHED,
                    actor=artifact.owner,
                    task_id=artifact.task_id,
                    artifact_id=artifact.artifact_id,
                    message=f"revision_round={artifact.revision_round}",
                    metadata={"revision_round": artifact.revision_round},
                )
            )
        return board

    def apply_turn_result(
        self,
        task: CollaborationTask,
        agent_name: str,
        result: CollaborationTurnResult,
    ) -> "CollaborationBoard":
        board = self
        for artifact in result.artifacts:
            board = board.add_artifact(artifact)
        if result.close_task:
            closed = task.close()
            board = board.add_task(closed).append_event(
                CollaborationEvent(
                    event_type=CollaborationEventType.TASK_CLOSED,
                    actor=agent_name,
                    task_id=task.task_id,
                    message=task.title,
                )
            )
        return board

    def open_tasks(self) -> list[CollaborationTask]:
        return [
            task
            for task in self.tasks.values()
            if task.status == CollaborationTaskStatus.OPEN
        ]

    def latest_artifact(self, kind: str) -> CollaborationArtifact | None:
        return next(
            (
                artifact
                for artifact in reversed(self.artifacts)
                if artifact.kind == kind
            ),
            None,
        )

    def accept_final(
        self,
        artifact_id: str,
        actor: str,
        reason: str,
    ) -> "CollaborationBoard":
        return replace(self, final_artifact_id=artifact_id).append_event(
            CollaborationEvent(
                event_type=CollaborationEventType.FINAL_ACCEPTED,
                actor=actor,
                artifact_id=artifact_id,
                message=reason,
            )
        )

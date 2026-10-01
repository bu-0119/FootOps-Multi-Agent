"""Executable event-driven multi-agent runtime for a scoped analysis."""

from dataclasses import dataclass
from uuid import uuid4

from footops_agent.agents import (
    CoordinatorAgent,
    DataAgent,
    EvidenceAgent,
    KnowledgeAgent,
    TacticalAgent,
)
from footops_agent.artifacts import (
    AnalysisRequestArtifact,
    AnalysisScope,
    AnalysisWorkspace,
    TacticalHypothesisArtifact,
)
from footops_agent.collaboration import (
    AgentRegistry,
    CollaborationBoard,
    CollaborationEvent,
    CollaborationTask,
    EventDrivenCoordinator,
    MultiAgentAnalysisRequest,
)
from footops_agent.providers import FootballDataProvider
from footops_agent.rag import HybridKnowledgeRetriever
from footops_agent.repositories import AnalysisWorkspaceRepository
from footops_agent.services import WorkspaceStateMachine


@dataclass(frozen=True)
class MultiAgentRunResult:
    run_id: str
    agent_names: tuple[str, ...]
    workspace: AnalysisWorkspace
    events: tuple[CollaborationEvent, ...]
    tasks: tuple[CollaborationTask, ...]
    hypothesis: TacticalHypothesisArtifact | None = None


class FootOpsMultiAgentRuntime:
    """Compose FootOps domain agents through a MindBridge-style task board."""

    framework_name = "footops_event_driven_multi_agent_v1"

    def __init__(
        self,
        provider: FootballDataProvider,
        repository: AnalysisWorkspaceRepository,
        max_rounds: int = 6,
        knowledge_retriever: HybridKnowledgeRetriever | None = None,
    ) -> None:
        self.repository = repository
        self.state_machine = WorkspaceStateMachine()
        self.registry = AgentRegistry(
            [
                DataAgent(provider),
                TacticalAgent(),
                EvidenceAgent(),
                KnowledgeAgent(knowledge_retriever),
            ]
        )
        self.coordinator_agent = CoordinatorAgent()
        self.coordinator = EventDrivenCoordinator(
            self.registry,
            self.coordinator_agent,
            self._finalize_workspace,
            max_rounds=max_rounds,
        )

    def run(self, request: MultiAgentAnalysisRequest) -> MultiAgentRunResult:
        board = self.coordinator.run(
            CollaborationBoard(run_id=uuid4().hex, request=request)
        )
        final = board.latest_artifact("workspace")
        if final is None or not board.final_artifact_id:
            raise RuntimeError("multi-agent run ended without an accepted workspace")
        active_agents = [self.coordinator_agent.name]
        for event in board.events:
            if (
                event.event_type.value == "TASK_CLAIMED"
                and event.actor not in active_agents
            ):
                active_agents.append(event.actor)
        knowledge = board.latest_artifact("knowledge_bundle")
        return MultiAgentRunResult(
            run_id=board.run_id,
            agent_names=tuple(active_agents),
            workspace=final.payload,
            events=board.events,
            tasks=tuple(board.tasks.values()),
            hypothesis=knowledge.payload.hypothesis if knowledge else None,
        )

    def _finalize_workspace(self, board: CollaborationBoard) -> AnalysisWorkspace:
        data = board.latest_artifact("data_bundle")
        findings = board.latest_artifact("finding_bundle")
        review = board.latest_artifact("review_bundle")
        tactics = board.latest_artifact("tactics_bundle")
        if data is None or findings is None or review is None:
            raise RuntimeError("accepted workspace requires data, findings, and review")

        request = board.request
        selected_ids = set(data.payload.audit.suggested_match_ids)
        appearance = next(
            item
            for item in data.payload.audit.appearances
            if item.match.match_id in selected_ids
        )
        request_artifact = AnalysisRequestArtifact(
            question=request.question,
            scope=AnalysisScope(
                competition_id=request.competition_id,
                season_id=request.season_id,
                player=(
                    data.payload.metrics.player.player_nickname
                    or data.payload.metrics.player.player_name
                ),
                player_id=data.payload.metrics.player.player_id,
                team=appearance.team.team_name,
                match_ids=data.payload.audit.suggested_match_ids,
            ),
        )
        workspace = self.repository.save(AnalysisWorkspace(request=request_artifact))
        workspace = self._transition(
            workspace,
            "data_ready",
            coverage=data.payload.audit,
        )
        workspace = self._transition(
            workspace,
            "metrics_ready",
            metrics=data.payload.metrics,
        )
        workspace = self._transition(
            workspace,
            "findings_ready",
            findings=findings.payload.findings.findings,
        )
        workspace = self._transition(
            workspace,
            "evidence_reviewed",
            evidence=findings.payload.evidence,
            evidence_review=review.payload.review,
        )
        if tactics is None:
            return self._transition(workspace, "completed")
        return self._transition(
            workspace,
            "tactics_ready",
            tactics_board=tactics.payload.tactics_board,
        )

    def _transition(
        self,
        workspace: AnalysisWorkspace,
        target: str,
        **artifacts: object,
    ) -> AnalysisWorkspace:
        transitioned = self.state_machine.transition(
            workspace,
            target,  # type: ignore[arg-type]
            **artifacts,  # type: ignore[arg-type]
        )
        return self.repository.save(transitioned)

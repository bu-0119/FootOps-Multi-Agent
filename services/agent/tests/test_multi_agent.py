"""Event-driven multi-agent collaboration and API tests."""

import pytest
from fastapi.testclient import TestClient
from test_data_pipeline import provider

from footops_agent.api.main import create_app
from footops_agent.artifacts import EvidenceReviewArtifact, FindingEvidenceReview
from footops_agent.collaboration import (
    CollaborationArtifact,
    CollaborationBoard,
    CollaborationEventType,
    CollaborationTask,
    CollaborationTaskStatus,
    MultiAgentAnalysisRequest,
    ReviewBundle,
)
from footops_agent.config import Settings
from footops_agent.rag import HybridKnowledgeRetriever, RedisVectorKnowledgeIndex
from footops_agent.repositories import InMemoryAnalysisWorkspaceRepository
from footops_agent.runtime import FootOpsMultiAgentRuntime


def analysis_request(
    question: str | None = None,
    requires_knowledge: bool = False,
) -> MultiAgentAnalysisRequest:
    return MultiAgentAnalysisRequest(
        question=question or "分析佩德里最近三场的角色变化",
        competition_id=11,
        season_id=90,
        player_query="Pedri",
        requested_window=3,
        player_id=30486,
        requires_knowledge=requires_knowledge,
    )


def test_collaboration_board_updates_are_immutable() -> None:
    board = CollaborationBoard(run_id="run-1", request=analysis_request())
    task = CollaborationTask(
        task_id="task:data",
        title="Load data",
        capability="DATA",
    )

    updated = board.add_task(task)

    assert board.tasks == {}
    assert updated.tasks[task.task_id].status == CollaborationTaskStatus.OPEN


def test_collaboration_board_publishes_critique_for_failed_review() -> None:
    review = EvidenceReviewArtifact(
        overall_status="partial",
        support_rate=0.5,
        reviews=[
            FindingEvidenceReview(
                finding_id="finding:invalid",
                status="rejected",
                reasons=["指标引用数值不一致"],
            )
        ],
    )
    board = CollaborationBoard(run_id="run-critique", request=analysis_request())

    updated = board.add_artifact(
        CollaborationArtifact(
            artifact_id="EvidenceAgent:review:1",
            owner="EvidenceAgent",
            kind="review_bundle",
            payload=ReviewBundle(review=review),
        )
    )

    assert updated.events[-1].event_type == CollaborationEventType.CRITIQUE_CREATED
    assert updated.events[-1].metadata["review_status"] == "partial"


def test_multi_agent_runtime_claims_tasks_and_accepts_reviewed_workspace() -> None:
    runtime = FootOpsMultiAgentRuntime(
        provider(),
        InMemoryAnalysisWorkspaceRepository(),
        knowledge_retriever=HybridKnowledgeRetriever(
            vector_index=RedisVectorKnowledgeIndex(Settings(_env_file=None)),
        ),
    )

    result = runtime.run(analysis_request())

    claimed = [
        event.actor
        for event in result.events
        if event.event_type == CollaborationEventType.TASK_CLAIMED
    ]
    assert result.agent_names == (
        "CoordinatorAgent",
        "DataAgent",
        "TacticalAgent",
        "EvidenceAgent",
    )
    assert claimed == [
        "DataAgent",
        "TacticalAgent",
        "EvidenceAgent",
        "TacticalAgent",
    ]
    assert result.events[-1].event_type == CollaborationEventType.FINAL_ACCEPTED
    assert result.events[-1].actor == "CoordinatorAgent"
    assert result.workspace.status == "tactics_ready"
    assert len(result.workspace.findings) == 6
    assert result.workspace.evidence_review is not None
    assert result.workspace.evidence_review.overall_status == "passed"


def test_multi_agent_runtime_skips_tactics_for_passing_only_question() -> None:
    runtime = FootOpsMultiAgentRuntime(
        provider(),
        InMemoryAnalysisWorkspaceRepository(),
    )

    result = runtime.run(analysis_request("分析佩德里最近三场的向前传球变化"))

    claimed = [
        event.actor
        for event in result.events
        if event.event_type == CollaborationEventType.TASK_CLAIMED
    ]
    assert claimed == ["DataAgent", "TacticalAgent", "EvidenceAgent"]
    assert result.workspace.status == "completed"
    assert result.workspace.tactics_board is None
    assert {item.finding_id for item in result.workspace.findings} == {
        "finding:forward_pass_count",
        "finding:completed_forward_pass_count",
    }


def test_multi_agent_runtime_grounds_hybrid_findings_with_knowledge_agent() -> None:
    runtime = FootOpsMultiAgentRuntime(
        provider(),
        InMemoryAnalysisWorkspaceRepository(),
        knowledge_retriever=HybridKnowledgeRetriever(
            vector_index=RedisVectorKnowledgeIndex(Settings(_env_file=None)),
        ),
    )

    result = runtime.run(
        analysis_request(
            "分析佩德里最近三场为什么更靠近半空间，是否与半空间接应有关",
            requires_knowledge=True,
        )
    )

    claimed = [
        event.actor
        for event in result.events
        if event.event_type == CollaborationEventType.TASK_CLAIMED
    ]
    assert claimed == [
        "DataAgent",
        "TacticalAgent",
        "EvidenceAgent",
        "KnowledgeAgent",
        "TacticalAgent",
    ]
    assert result.workspace.status == "tactics_ready"
    assert any(
        event.actor == "KnowledgeAgent"
        and event.event_type == CollaborationEventType.ARTIFACT_PUBLISHED
        for event in result.events
    )


def test_multi_agent_runtime_enforces_round_budget() -> None:
    runtime = FootOpsMultiAgentRuntime(
        provider(),
        InMemoryAnalysisWorkspaceRepository(),
        max_rounds=2,
    )

    with pytest.raises(RuntimeError, match="without an accepted workspace"):
        runtime.run(analysis_request())


def test_multi_agent_api_exposes_sanitized_collaboration_trace() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/multi-agent/analyses",
            json={
                "question": "分析佩德里最近三场的角色变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["runtime"] == "footops_event_driven_multi_agent_v1"
    assert body["model_called"] is False
    assert body["agents"] == [
        "CoordinatorAgent",
        "DataAgent",
        "TacticalAgent",
        "EvidenceAgent",
    ]
    assert body["rounds"] == 4
    assert body["workspace"]["status"] == "tactics_ready"
    assert any(item["event_type"] == "FINAL_ACCEPTED" for item in body["trace"])
    assert all("payload" not in item for item in body["trace"])

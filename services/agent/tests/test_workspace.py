"""Analysis workspace lifecycle and HTTP contract tests."""

import json

import pytest
from fastapi.testclient import TestClient
from test_data_pipeline import provider

from footops_agent.api.main import create_app
from footops_agent.artifacts import (
    AnalysisRequestArtifact,
    AnalysisScope,
    AnalysisWorkspace,
)
from footops_agent.config import Settings
from footops_agent.repositories import InMemoryAnalysisWorkspaceRepository
from footops_agent.services import (
    InvalidWorkspaceTransitionError,
    WorkspaceStateMachine,
)


def request_artifact() -> AnalysisRequestArtifact:
    return AnalysisRequestArtifact(
        question="分析佩德里最近三场的位置变化",
        scope=AnalysisScope(
            competition_id=11,
            season_id=90,
            player="Pedri",
            team="Barcelona",
            match_ids=[1001, 1002, 1003],
        ),
    )


def test_repository_returns_defensive_workspace_copies() -> None:
    repository = InMemoryAnalysisWorkspaceRepository()
    workspace = AnalysisWorkspace(request=request_artifact())

    saved = repository.save(workspace)
    saved.request.scope.match_ids.append(9999)
    restored = repository.get(workspace.workspace_id)

    assert restored is not None
    assert restored.request.scope.match_ids == [1001, 1002, 1003]


def test_state_machine_rejects_skipped_transition() -> None:
    workspace = AnalysisWorkspace(request=request_artifact())

    with pytest.raises(InvalidWorkspaceTransitionError):
        WorkspaceStateMachine().transition(workspace, "metrics_ready")


def test_workspace_api_creates_and_restores_audited_analysis() -> None:
    repository = InMemoryAnalysisWorkspaceRepository()
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
        workspace_repository=repository,
    )
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            json={
                "question": "分析佩德里最近三场的角色变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )
        workspace_id = created.json()["workspace"]["workspace_id"]
        restored = client.get(f"/api/v1/analyses/{workspace_id}")

    assert created.status_code == 201
    assert restored.status_code == 200
    assert restored.json() == {**created.json(), "status": "ready"}
    body = created.json()
    assert body["model_called"] is False
    assert body["real_conclusions_generated"] is False
    assert body["workspace"]["status"] == "tactics_ready"
    assert body["workspace"]["request"]["scope"]["match_ids"] == [
        1001,
        1002,
        1003,
    ]
    assert len(body["workspace"]["findings"]) == 3
    assert body["workspace"]["evidence_review"]["overall_status"] == "passed"
    board = body["workspace"]["tactics_board"]
    assert body["tactics_board_generated"] is True
    assert board["formation"] == "unassigned"
    assert len(board["players"]) == 1
    assert len(board["zones"]) == 2
    assert len(board["arrows"]) == 1
    assert board["passing_lanes"] == []
    assert len(board["finding_refs"]) == 3
    assert board["evidence_refs"]
    assert all(
        0 <= point[axis] <= 100
        for point in [
            board["players"][0]["position"],
            board["arrows"][0]["start"],
            board["arrows"][0]["end"],
        ]
        for axis in ["x", "y"]
    )


def test_workspace_api_returns_uniform_not_found_error() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/analyses/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


def test_workspace_stream_emits_status_before_completed_workspace() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/analyses/stream",
            json={
                "question": "分析佩德里最近三场的位置变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        ) as response:
            lines = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert lines[0] == "event: analysis.status"
    assert lines[2] == "event: analysis.completed"
    status = json.loads(lines[1].removeprefix("data: "))
    completed = json.loads(lines[3].removeprefix("data: "))
    assert status["sequence"] == 1
    assert completed["sequence"] == 2
    assert completed["response"]["workspace"]["status"] == "tactics_ready"


def test_specific_question_only_returns_relevant_finding() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": "佩德里最近三场的平均触球位置有什么变化？",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert [item["finding_id"] for item in body["workspace"]["findings"]] == [
        "finding:average_touch_x"
    ]
    assert body["tactics_board_generated"] is True


def test_supported_non_position_question_does_not_invent_tactics_board() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": "佩德里最近三场的进攻三区触球占比有什么变化？",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace"]["status"] == "completed"
    assert body["workspace"]["tactics_board"] is None
    assert body["tactics_board_generated"] is False
    assert [item["finding_id"] for item in body["workspace"]["findings"]] == [
        "finding:attacking_third_touch_ratio"
    ]


def test_unsupported_question_is_rejected_instead_of_reusing_fixed_answer() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    payload = {
        "question": "你好，你能介绍一下自己吗？",
        "competition_id": 11,
        "season_id": 90,
        "player": "Pedri",
        "requested_window": 3,
    }
    with TestClient(app) as client:
        direct = client.post("/api/v1/analyses", json=payload)
        with client.stream(
            "POST",
            "/api/v1/analyses/stream",
            json=payload,
        ) as streamed:
            lines = [line for line in streamed.iter_lines() if line]

    assert direct.status_code == 422
    assert direct.json()["error"]["code"] == "unsupported_analysis_question"
    assert lines[0] == "event: analysis.status"
    assert lines[2] == "event: analysis.error"
    error = json.loads(lines[3].removeprefix("data: "))
    assert error["error"]["code"] == "unsupported_analysis_question"

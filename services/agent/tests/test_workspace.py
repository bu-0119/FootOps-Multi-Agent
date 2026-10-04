"""Analysis workspace lifecycle and HTTP contract tests."""

import json

import pytest
from fastapi.testclient import TestClient
from test_data_pipeline import provider

from footops_agent.api.main import create_app
from footops_agent.artifacts import (
    AgentDecision,
    AgentToolTrace,
    AnalysisRequestArtifact,
    AnalysisScope,
    AnalysisWorkspace,
    ResolvedAgentScope,
)
from footops_agent.config import Settings
from footops_agent.repositories import InMemoryAnalysisWorkspaceRepository
from footops_agent.runtime.analysis_agent import (
    _decision_from_workspace,
    _safe_clarification,
)
from footops_agent.services import (
    AnalysisWorkspaceService,
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
            player_id=30486,
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


def test_runtime_can_recover_completion_from_trusted_workspace() -> None:
    data_provider = provider()
    service = AnalysisWorkspaceService(
        data_provider,
        InMemoryAnalysisWorkspaceRepository(),
    )
    workspace = service.create(
        "分析佩德里最近三场的角色变化",
        11,
        90,
        "Pedri",
        3,
        30486,
    )

    decision = _decision_from_workspace(workspace)

    assert decision.action == "completed"
    assert decision.resolved_scope.competition_name == "La Liga"
    assert decision.resolved_scope.player_id == 30486
    assert decision.resolved_scope.requested_window == 3


def test_runtime_clarification_does_not_repeat_unverified_season_examples() -> None:
    model_decision = AgentDecision(
        action="clarification_required",
        message="请指定赛季，例如 2025/2026。",
        resolved_scope=ResolvedAgentScope(player="佩德里", requested_window=3),
    )

    decision = _safe_clarification(
        model_decision,
        [
            AgentToolTrace(
                sequence=1,
                tool_name="search_competitions",
                status="completed",
                summary="返回公开目录。",
            )
        ],
    )

    assert "2025/2026" not in decision.message
    assert "公开目录" in decision.message


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
    assert len(body["workspace"]["findings"]) == 6
    assert body["workspace"]["evidence_review"]["overall_status"] == "passed"
    board = body["workspace"]["tactics_board"]
    assert body["tactics_board_generated"] is True
    assert board["formation"] == "unassigned"
    assert len(board["players"]) == 1
    assert len(board["zones"]) == 2
    assert len(board["arrows"]) == 1
    assert board["passing_lanes"] == []
    assert len(board["finding_refs"]) == 6
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


def test_natural_language_agent_requests_clarification_without_fixed_scope() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "分析佩德里最近三场的角色变化"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_required"
    assert body["workspace"] is None
    assert body["data_retrieved"] is False
    assert "赛事和赛季" in body["message"]


def test_agent_routes_greeting_to_chat_without_analysis_workspace() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "你好"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "chat"
    assert body["decision"]["action"] == "chat"
    assert body["workspace"] is None
    assert body["data_retrieved"] is False
    assert "你好" in body["message"]


def test_agent_stream_emits_chat_completion_without_tool_events() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/runs/stream",
            json={"question": "你好"},
        ) as response:
            lines = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert lines[0] == "event: agent.started"
    assert lines[2] == "event: agent.chat_completed"
    completed = json.loads(lines[3].removeprefix("data: "))
    assert completed["response"]["status"] == "chat"
    assert completed["response"]["trace"] == []


def test_agent_executes_workspace_when_optional_scope_is_complete() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={
                "question": "分析佩德里最近三场的角色变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["workspace"]["status"] == "tactics_ready"
    assert body["workspace"]["metrics"]["player"]["player_id"] == 30486


def test_agent_answers_per_match_xg_comparison_with_source_facts() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={
                "question": "哪场 xG 最高",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["message"].startswith("### 单场xG比较")
    assert "2021-01-08" in body["message"]
    assert "Opponent" in body["message"]
    assert "0.45" in body["message"]
    assert "source:1002" in body["message"]


def test_agent_stream_emits_started_before_completed() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/agent/runs/stream",
            json={
                "question": "分析佩德里最近三场的角色变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "requested_window": 3,
            },
        ) as response:
            lines = [line for line in response.iter_lines() if line]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert lines[0] == "event: agent.started"
    assert lines[2] == "event: agent.completed"
    completed = json.loads(lines[3].removeprefix("data: "))
    assert completed["response"]["workspace"]["status"] == "tactics_ready"


def test_agent_rejects_partial_competition_hint() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={
                "question": "分析佩德里",
                "competition_id": 11,
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


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


def test_generic_player_scope_does_not_require_pedri_in_question() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": "分析最近三场的平均触球位置变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedro González López",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace"]["metrics"]["player"]["player_id"] == 30486
    assert [item["finding_id"] for item in body["workspace"]["findings"]] == [
        "finding:average_touch_x"
    ]


@pytest.mark.parametrize(
    "question",
    [
        "分析最近三场表现",
        "最近三场踢得怎么样",
        "看看近期的活动趋势",
    ],
)
def test_common_broad_questions_select_supported_findings(question: str) -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": question,
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    assert len(response.json()["workspace"]["findings"]) == 6


@pytest.mark.parametrize(
    ("question", "expected_ids"),
    [
        (
            "最近三场向前传球有什么变化",
            [
                "finding:forward_pass_count",
                "finding:completed_forward_pass_count",
            ],
        ),
        ("最近三场推进带球有什么变化", ["finding:progressive_carry_count"]),
        ("最近三场关键传球有什么变化", ["finding:key_pass_count"]),
        ("最近三场射门表现怎么样", ["finding:shot_count"]),
        ("最近三场射门参与有什么变化", ["finding:shot_involvement_count"]),
        ("最近三场禁区触球有什么变化", ["finding:penalty_area_touch_ratio"]),
    ],
)
def test_new_metrics_select_only_requested_findings(
    question: str,
    expected_ids: list[str],
) -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": question,
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 201
    workspace = response.json()["workspace"]
    assert [item["finding_id"] for item in workspace["findings"]] == expected_ids
    assert workspace["evidence_review"]["support_rate"] == 1
    assert workspace["tactics_board"] is None


@pytest.mark.parametrize(
    "question",
    [
        "分析最近三场进球和助攻",
        "最近三场射门和预期进球变化",
    ],
)
def test_unsupported_metrics_are_not_mapped_to_generic_findings(
    question: str,
) -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": question,
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 3,
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_analysis_question"


def test_unknown_player_returns_explicit_data_boundary() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            json={
                "question": "分析最近三场的角色变化",
                "competition_id": 11,
                "season_id": 90,
                "player": "Unknown Player",
                "requested_window": 3,
            },
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "player_not_found"


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

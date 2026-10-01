"""ScopeAgent grounding, harness, and natural-language multi-agent API tests."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_data_pipeline import provider

from footops_agent.api.main import create_app
from footops_agent.artifacts import (
    AgentAnalysisInput,
    CompetitionSeason,
    PlayerCatalogEntry,
    PlayerRef,
    ResolvedAgentScope,
    ScopeResolutionArtifact,
    TeamRef,
)
from footops_agent.config import Settings
from footops_agent.harness import FootOpsMultiAgentHarness
from footops_agent.repositories import InMemoryAnalysisWorkspaceRepository
from footops_agent.runtime import FootOpsMultiAgentRuntime, ScopeAgentResult
from footops_agent.runtime.scope_agent import DeepSeekScopeAgentRuntime
from footops_agent.services import DataCatalogService
from footops_agent.tools import AgentToolContext


class ResolvedStubScopeRuntime:
    mode = "mock"
    provider = "none"
    model_name = "scope-stub"
    model_called = False

    async def run(self, _request: AgentAnalysisInput) -> ScopeAgentResult:
        return ScopeAgentResult(
            artifact=ScopeResolutionArtifact(
                status="resolved",
                message="范围已由测试目录确认。",
                scope=ResolvedAgentScope(
                    competition_id=11,
                    season_id=90,
                    competition_name="La Liga",
                    season_name="2020/2021",
                    player="Pedri",
                    player_id=30486,
                    requested_window=3,
                ),
            ),
            trace=[],
        )


def test_resolved_scope_artifact_requires_complete_catalog_identity() -> None:
    with pytest.raises(ValidationError):
        ScopeResolutionArtifact(
            status="resolved",
            message="invalid",
            scope=ResolvedAgentScope(player="Pedri"),
        )


def test_scope_agent_rejects_model_ids_without_hint_or_catalog_result() -> None:
    artifact = ScopeResolutionArtifact(
        status="resolved",
        message="model claimed a scope",
        scope=ResolvedAgentScope(
            competition_id=999,
            season_id=999,
            player="Invented Player",
            player_id=999,
            requested_window=5,
        ),
    )

    grounded = DeepSeekScopeAgentRuntime._ground_artifact(
        artifact,
        AgentAnalysisInput(question="分析某球员最近五场"),
        AgentToolContext(),
    )

    assert grounded.status == "clarification_required"
    assert grounded.scope.competition_id is None


def test_scope_agent_overwrites_model_ids_with_catalog_candidates() -> None:
    context = AgentToolContext(
        resolved_competition=CompetitionSeason(
            competition_id=11,
            season_id=90,
            country_name="Spain",
            competition_name="La Liga",
            season_name="2020/2021",
        ),
        resolved_player=PlayerCatalogEntry(
            player=PlayerRef(player_id=30486, player_name="Pedro González López"),
            teams=[TeamRef(team_id=217, team_name="Barcelona")],
            appearance_count=35,
            first_match_date=date(2020, 9, 27),
            last_match_date=date(2021, 5, 22),
        ),
    )
    artifact = ScopeResolutionArtifact(
        status="resolved",
        message="resolved",
        scope=ResolvedAgentScope(
            competition_id=999,
            season_id=999,
            player="Invented Player",
            player_id=999,
            requested_window=3,
        ),
    )

    grounded = DeepSeekScopeAgentRuntime._ground_artifact(
        artifact,
        AgentAnalysisInput(question="分析佩德里在西甲最近三场"),
        context,
    )

    assert grounded.status == "resolved"
    assert grounded.scope.competition_id == 11
    assert grounded.scope.season_id == 90
    assert grounded.scope.player_id == 30486
    assert grounded.scope.player == "Pedro González López"


def test_natural_language_multi_agent_api_runs_after_scope_resolution() -> None:
    data_provider = provider()
    repository = InMemoryAnalysisWorkspaceRepository()
    multi_runtime = FootOpsMultiAgentRuntime(data_provider, repository)
    multi_harness = FootOpsMultiAgentHarness(
        Settings(_env_file=None, llm_mode="mock"),
        DataCatalogService(data_provider),
        multi_runtime,
        scope_runtime_factory=ResolvedStubScopeRuntime,
    )
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=data_provider,
        workspace_repository=repository,
        multi_agent_harness=multi_harness,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/multi-agent/runs",
            json={
                "question": "分析佩德里在西甲 2020/21 最近三场的角色变化"
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["scope"]["status"] == "resolved"
    assert body["scope"]["scope"]["player_id"] == 30486
    assert body["agents"][0] == "FootOpsScopeAgent"
    assert body["workspace"]["status"] == "tactics_ready"
    assert any(item["event_type"] == "FINAL_ACCEPTED" for item in body["trace"])


def test_natural_language_multi_agent_sse_exposes_collaboration_trace() -> None:
    data_provider = provider()
    repository = InMemoryAnalysisWorkspaceRepository()
    multi_runtime = FootOpsMultiAgentRuntime(data_provider, repository)
    multi_harness = FootOpsMultiAgentHarness(
        Settings(_env_file=None, llm_mode="mock"),
        DataCatalogService(data_provider),
        multi_runtime,
        scope_runtime_factory=ResolvedStubScopeRuntime,
    )
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=data_provider,
        workspace_repository=repository,
        multi_agent_harness=multi_harness,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/multi-agent/runs/stream",
            json={"question": "分析佩德里在西甲 2020/21 最近三场的角色变化"},
        )

    assert response.status_code == 200
    assert "multi_agent.started" in response.text
    assert "multi_agent.collaboration" in response.text
    assert "FINAL_ACCEPTED" in response.text
    assert "multi_agent.completed" in response.text


def test_mock_scope_agent_requests_clarification_without_explicit_scope() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/multi-agent/runs",
            json={"question": "分析佩德里最近三场"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_required"
    assert body["workspace"] is None
    assert body["agents"] == []


def test_multi_agent_entry_does_not_run_data_for_rule_knowledge_request() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/multi-agent/runs",
            json={"question": "越位规则中的主动触球怎么判断？"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["execution_plan"]["intent"] == "rule_qa"
    assert body["execution_plan"]["need_rule_rag"] is True
    assert body["scope"] is None
    assert body["workspace"] is None

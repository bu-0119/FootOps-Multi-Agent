"""Golden-task evaluation harness tests."""

from pathlib import Path

import pytest

from footops_agent.artifacts import AgentModelUsage, AgentScopeHint, CompetitionSeason
from footops_agent.evaluation import (
    EvaluationObservation,
    EvaluationService,
    GoldenTask,
    GoldenTaskExpectation,
    GoldenTaskSuite,
)
from footops_agent.tools.analysis import _competition_matches

ROOT = Path(__file__).resolve().parents[3]


class StubRunner:
    mode = "single_agent"

    def __init__(self, observation: EvaluationObservation) -> None:
        self.observation = observation

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        return self.observation


def task() -> GoldenTask:
    return GoldenTask(
        task_id="golden",
        question="分析 Pedri 最近三场的角色变化",
        scope_hint=AgentScopeHint(
            competition_id=11,
            season_id=90,
            player="Pedri",
            player_id=30486,
            requested_window=3,
        ),
        expectation=GoldenTaskExpectation(
            status="completed",
            require_workspace=True,
            required_agent_tools=[
                "search_players",
                "run_player_role_analysis",
            ],
        ),
    )


@pytest.mark.asyncio
async def test_evaluation_passes_supported_workspace_and_tool_sequence() -> None:
    observation = EvaluationObservation(
        mode="single_agent",
        status="completed",
        message="done",
        duration_ms=125,
        model_called=True,
        model_name="deepseek-test",
        tool_sequence=[
            "search_competitions",
            "search_players",
            "run_player_role_analysis",
        ],
        workspace_id="workspace-1",
        finding_count=3,
        claim_support_rate=1,
        usage=AgentModelUsage(input_tokens=100, output_tokens=20),
        stopping_reason="completed",
    )

    report = await EvaluationService([StubRunner(observation)]).run(
        GoldenTaskSuite(suite_id="test-suite", description="test", tasks=[task()])
    )

    result = report.results[0]
    assert result.passed is True
    assert result.assertions.tool_sequence_match is True
    assert result.assertions.supported_claims is True
    assert report.summaries[0].pass_rate == 1
    assert report.summaries[0].total_input_tokens == 100
    assert report.summaries[0].estimated_cost_usd is None


@pytest.mark.asyncio
async def test_evaluation_rejects_completion_without_workspace() -> None:
    observation = EvaluationObservation(
        mode="single_agent",
        status="completed",
        message="unsupported claim",
        duration_ms=10,
        model_called=True,
        model_name="deepseek-test",
        stopping_reason="completed",
    )

    report = await EvaluationService([StubRunner(observation)]).run(
        GoldenTaskSuite(suite_id="test-suite", description="test", tasks=[task()])
    )

    result = report.results[0]
    assert result.passed is False
    assert result.assertions.no_unsupported_completion is False
    assert report.summaries[0].unsupported_completion_count == 1


def test_checked_in_golden_suite_is_valid_and_covers_boundaries() -> None:
    suite = GoldenTaskSuite.model_validate_json(
        (ROOT / "data/evaluation/player-role-v1.json").read_text(encoding="utf-8")
    )

    assert len(suite.tasks) == 9
    assert {item.expectation.status for item in suite.tasks} == {
        "chat",
        "completed",
        "clarification_required",
        "unsupported",
    }


def test_competition_search_matches_name_and_season_inside_question() -> None:
    competition = CompetitionSeason(
        competition_id=11,
        season_id=90,
        country_name="Spain",
        competition_name="La Liga",
        season_name="2020/2021",
    )

    assert _competition_matches("西甲 2020/21 赛季", competition) is True
    assert _competition_matches("分析佩德里在西甲 2020/21 的表现", competition) is True
    assert _competition_matches("西甲 2019/20", competition) is False

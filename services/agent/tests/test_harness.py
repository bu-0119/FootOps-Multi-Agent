"""Harness behavior and safety-boundary tests."""

import asyncio

import pytest

from footops_agent.agents import AnalysisPlanner
from footops_agent.config import Settings
from footops_agent.harness import (
    FootOpsAgentHarness,
    InputTooLongError,
    RunTimeoutError,
)
from footops_agent.runtime import MockModelAdapter


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


@pytest.mark.asyncio
async def test_mock_run_is_explicitly_non_model_and_non_evidentiary() -> None:
    harness = FootOpsAgentHarness(make_settings(llm_mode="mock"))

    response = await harness.run_plan("如何规划一次球队表现分析？")

    assert response.status == "planned"
    assert response.mode == "mock"
    assert response.model_called is False
    assert response.data_retrieved is False
    assert response.real_conclusions_generated is False
    assert "未调用模型" in response.message
    assert any("不能作为真实分析结论" in item for item in response.plan.limitations)
    assert len(response.run_id) == 32


@pytest.mark.asyncio
async def test_harness_rejects_input_over_configured_limit() -> None:
    harness = FootOpsAgentHarness(
        make_settings(llm_mode="mock", footops_input_max_chars=4),
    )

    with pytest.raises(InputTooLongError) as error:
        await harness.run_plan("12345")

    assert error.value.status_code == 413
    assert error.value.run_id is not None


@pytest.mark.asyncio
async def test_harness_times_out_planner() -> None:
    class SlowMockAdapter(MockModelAdapter):
        async def create_plan(self, question: str):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0.1)
            return await super().create_plan(question)

    harness = FootOpsAgentHarness(
        make_settings(
            llm_mode="mock",
            footops_request_timeout_seconds=0.01,
        ),
        planner_factory=lambda: AnalysisPlanner(SlowMockAdapter()),
    )

    with pytest.raises(RunTimeoutError):
        await harness.run_plan("测试超时")

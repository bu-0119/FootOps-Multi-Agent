"""AgentScope integration tests without making provider requests."""

from unittest.mock import AsyncMock

import pytest
from agentscope.agent import Agent
from agentscope.message import AssistantMsg
from agentscope.model import DeepSeekChatModel
from pydantic import SecretStr

from footops_agent.artifacts import (
    AnalysisPlan,
    AnalysisPlanStep,
    QuestionUnderstanding,
)
from footops_agent.config import Settings
from footops_agent.runtime import DeepSeekModelAdapter


@pytest.mark.asyncio
async def test_deepseek_adapter_uses_agent_and_structured_schema() -> None:
    settings = Settings(
        _env_file=None,
        llm_mode="deepseek",
        deepseek_api_key=SecretStr("test-key"),
    )
    adapter = DeepSeekModelAdapter(settings)
    output = AnalysisPlan(
        understanding=QuestionUnderstanding(intent="准备分析", subjects=[]),
        steps=[
            AnalysisPlanStep(
                title="收集数据",
                purpose="准备证据",
                required_data=[],
                output="待执行的数据清单",
            ),
        ],
        limitations=["未检索数据，未生成结论。"],
    )
    adapter.agent.reply = AsyncMock(
        return_value=AssistantMsg(
            name="FootOpsPlanner",
            content="structured",
            structured_output=output.model_dump(),
        ),
    )

    result = await adapter.create_plan("规划问题")

    assert isinstance(adapter.agent, Agent)
    assert isinstance(adapter.agent.model, DeepSeekChatModel)
    assert adapter.agent.react_config.max_iters == 3
    assert result == output
    assert adapter.agent.reply.await_args.kwargs["structured_schema"] is AnalysisPlan

"""Model-provider adapters used by the planning agent."""

from typing import Protocol

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.model import DeepSeekChatModel

from footops_agent.artifacts import (
    AnalysisPlan,
    AnalysisPlanStep,
    QuestionUnderstanding,
)
from footops_agent.config import Settings
from footops_agent.prompts import PLANNER_SYSTEM_PROMPT


class ModelAdapter(Protocol):
    """Provider-independent interface consumed by the planner."""

    mode: str
    provider: str
    model_name: str
    model_called: bool

    async def create_plan(self, question: str) -> AnalysisPlan:
        """Create a structured, non-executed analysis plan."""


class MockModelAdapter:
    """Deterministic adapter that never invokes a model or data source."""

    mode = "mock"
    provider = "none"
    model_name = "mock"
    model_called = False

    async def create_plan(self, question: str) -> AnalysisPlan:
        """Return a transparent placeholder plan for local development."""
        return AnalysisPlan(
            understanding=QuestionUnderstanding(
                intent=f"为用户问题准备分析方案：{question}",
                subjects=[],
                requested_comparisons=[],
                requested_evidence=[],
                ambiguities=["mock 模式不解析实体或补全比赛范围。"],
            ),
            steps=[
                AnalysisPlanStep(
                    title="确认分析范围",
                    purpose="明确研究对象、赛事范围、时间范围和比较基线。",
                    required_data=[],
                    output="一份待用户确认的分析口径。",
                ),
                AnalysisPlanStep(
                    title="规划证据收集",
                    purpose="列出后续分析所需的数据类型和验证方式。",
                    required_data=["经授权且可追溯的比赛数据"],
                    output="一份尚未执行的数据需求清单。",
                ),
            ],
            clarifying_questions=["是否需要补充赛事、时间范围或比较基线？"],
            assumptions=[],
            limitations=[
                "当前为 mock 模式，未调用任何 LLM。",
                "当前请求未检索或读取任何比赛数据。",
                "此结果仅是接口占位计划，不能作为真实分析结论。",
            ],
        )


class DeepSeekModelAdapter:
    """AgentScope 2.0.5 adapter for DeepSeek structured planning."""

    mode = "deepseek"
    provider = "deepseek"
    model_called = True

    def __init__(self, settings: Settings) -> None:
        if settings.deepseek_api_key is None:
            raise ValueError("DeepSeek API key is required")

        self.model_name = settings.deepseek_model
        credential = DeepSeekCredential(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        model = DeepSeekChatModel(
            credential=credential,
            model=settings.deepseek_model,
            parameters=DeepSeekChatModel.Parameters(
                max_tokens=1800,
                temperature=0.1,
            ),
            stream=False,
            max_retries=1,
            client_kwargs={"timeout": settings.footops_request_timeout_seconds},
        )
        self.agent = Agent(
            name="FootOpsPlanner",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            model=model,
            react_config=ReActConfig(
                max_iters=settings.footops_agent_max_iters,
            ),
        )

    async def create_plan(self, question: str) -> AnalysisPlan:
        """Ask AgentScope's Agent for schema-validated structured output."""
        response = await self.agent.reply(
            UserMsg(name="user", content=question),
            structured_schema=AnalysisPlan,
        )
        if response.structured_output is None:
            raise RuntimeError("DeepSeek returned no structured planning output")
        return AnalysisPlan.model_validate(response.structured_output)

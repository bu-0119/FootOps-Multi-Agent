"""Run lifecycle and safety envelope for planning requests."""

import asyncio
from collections.abc import Callable
from uuid import uuid4

from footops_agent.agents import AnalysisPlanner
from footops_agent.api.schemas import AnalysisPlanResponse
from footops_agent.config import Settings
from footops_agent.runtime import DeepSeekModelAdapter, MockModelAdapter

from .errors import (
    HarnessError,
    InputTooLongError,
    ModelUnavailableError,
    RunTimeoutError,
    UpstreamModelError,
)

PlannerFactory = Callable[[], AnalysisPlanner]


class FootOpsAgentHarness:
    """Own run IDs, limits, timeouts, and uniform planning responses."""

    def __init__(
        self,
        settings: Settings,
        planner_factory: PlannerFactory | None = None,
    ) -> None:
        self.settings = settings
        self._planner_factory = planner_factory

    def _build_planner(self) -> AnalysisPlanner:
        if self._planner_factory is not None:
            return self._planner_factory()
        if self.settings.llm_mode == "mock":
            return AnalysisPlanner(MockModelAdapter())
        return AnalysisPlanner(DeepSeekModelAdapter(self.settings))

    async def run_plan(self, question: str) -> AnalysisPlanResponse:
        """Execute one bounded planning run."""
        run_id = uuid4().hex
        if len(question) > self.settings.footops_input_max_chars:
            raise InputTooLongError(
                "输入超过允许的字符上限 "
                f"({self.settings.footops_input_max_chars})。",
                run_id,
            )
        if (
            self.settings.llm_mode == "deepseek"
            and not self.settings.deepseek_key_configured
        ):
            raise ModelUnavailableError(
                "DeepSeek 模式缺少 DEEPSEEK_API_KEY。",
                run_id,
            )

        planner = self._build_planner()
        try:
            plan = await asyncio.wait_for(
                planner.plan(question),
                timeout=self.settings.footops_request_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RunTimeoutError("分析计划请求超时。", run_id) from exc
        except HarnessError:
            raise
        except Exception as exc:
            raise UpstreamModelError("模型未能生成有效的结构化计划。", run_id) from exc

        adapter = planner.adapter
        if self.settings.llm_mode == "mock":
            message = (
                "mock 模式：未调用模型、未检索数据，返回内容不能作为真实结论。"
            )
        else:
            message = "模型仅生成分析计划；未检索数据，也未生成真实结论。"

        return AnalysisPlanResponse(
            run_id=run_id,
            mode=self.settings.llm_mode,
            provider=adapter.provider,
            model=adapter.model_name,
            model_called=adapter.model_called,
            data_retrieved=False,
            real_conclusions_generated=False,
            message=message,
            plan=plan,
        )

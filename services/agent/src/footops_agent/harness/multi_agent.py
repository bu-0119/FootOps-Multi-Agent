"""Harness that resolves natural-language scope before multi-agent collaboration."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from footops_agent.artifacts import AgentAnalysisInput, ExecutionPlanArtifact
from footops_agent.collaboration import MultiAgentAnalysisRequest
from footops_agent.config import Settings
from footops_agent.runtime import (
    DeepSeekScopeAgentRuntime,
    FootOpsMultiAgentRuntime,
    MockScopeAgentRuntime,
    MultiAgentRunResult,
    ScopeAgentResult,
    ScopeAgentRuntime,
)
from footops_agent.services import DataCatalogService, RequestIntentRouter

from .errors import (
    InputTooLongError,
    ModelUnavailableError,
    RunTimeoutError,
    UpstreamModelError,
)

ScopeRuntimeFactory = Callable[[], ScopeAgentRuntime]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MultiAgentHarnessResult:
    """Scope outcome plus an optional accepted collaboration result."""

    run_id: str
    status: str
    execution_plan: ExecutionPlanArtifact
    scope_result: ScopeAgentResult | None
    collaboration: MultiAgentRunResult | None
    duration_ms: float
    scope_mode: str
    scope_provider: str
    scope_model: str
    scope_model_called: bool


class FootOpsMultiAgentHarness:
    """Keep scope resolution outside the collaboration board and data workers."""

    def __init__(
        self,
        settings: Settings,
        catalog: DataCatalogService,
        runtime: FootOpsMultiAgentRuntime,
        scope_runtime_factory: ScopeRuntimeFactory | None = None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.runtime = runtime
        self._scope_runtime_factory = scope_runtime_factory
        self.intent_router = RequestIntentRouter()

    def _build_scope_runtime(self) -> ScopeAgentRuntime:
        if self._scope_runtime_factory is not None:
            return self._scope_runtime_factory()
        if self.settings.llm_mode == "mock":
            return MockScopeAgentRuntime()
        return DeepSeekScopeAgentRuntime(self.settings, self.catalog)

    async def run(self, request: AgentAnalysisInput) -> MultiAgentHarnessResult:
        run_id = uuid4().hex
        if len(request.question) > self.settings.footops_input_max_chars:
            raise InputTooLongError(
                "输入超过允许的字符上限 "
                f"({self.settings.footops_input_max_chars})。",
                run_id,
            )
        execution_plan = self.intent_router.plan(request)
        if execution_plan.intent == "chat" or execution_plan.need_rule_rag:
            return MultiAgentHarnessResult(
                run_id=run_id,
                status="unsupported",
                execution_plan=execution_plan,
                scope_result=None,
                collaboration=None,
                duration_ms=0,
                scope_mode="none",
                scope_provider="none",
                scope_model="none",
                scope_model_called=False,
            )
        if (
            self.settings.llm_mode == "deepseek"
            and not self.settings.deepseek_key_configured
        ):
            raise ModelUnavailableError(
                "DeepSeek 模式缺少 DEEPSEEK_API_KEY。",
                run_id,
            )

        scope_runtime = self._build_scope_runtime()
        started_at = perf_counter()
        try:
            scope_result = await asyncio.wait_for(
                scope_runtime.run(request),
                timeout=self.settings.footops_agent_run_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RunTimeoutError("ScopeAgent 范围解析超时。", run_id) from exc
        except Exception as exc:
            logger.exception(
                "ScopeAgent run %s failed with %s",
                run_id,
                type(exc).__name__,
            )
            raise UpstreamModelError(
                "ScopeAgent 未能返回可验证的分析范围。",
                run_id,
            ) from exc

        if scope_result.artifact.status != "resolved":
            return MultiAgentHarnessResult(
                run_id=run_id,
                status="clarification_required",
                execution_plan=execution_plan,
                scope_result=scope_result,
                collaboration=None,
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                scope_mode=scope_runtime.mode,
                scope_provider=scope_runtime.provider,
                scope_model=scope_runtime.model_name,
                scope_model_called=scope_runtime.model_called,
            )

        scope = scope_result.artifact.scope
        if (
            scope.competition_id is None
            or scope.season_id is None
            or scope.player is None
            or scope.player_id is None
            or scope.requested_window is None
        ):
            raise UpstreamModelError(
                "ScopeAgent 返回的范围缺少必要字段。",
                run_id,
            )
        try:
            collaboration = await asyncio.wait_for(
                asyncio.to_thread(
                    self.runtime.run,
                    MultiAgentAnalysisRequest(
                        question=request.question,
                        competition_id=scope.competition_id,
                        season_id=scope.season_id,
                        player_query=scope.player,
                        requested_window=scope.requested_window,
                        player_id=scope.player_id,
                        requires_knowledge=execution_plan.need_tactical_rag,
                    ),
                ),
                timeout=self.settings.footops_agent_run_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RunTimeoutError("多 Agent 协作执行超时。", run_id) from exc

        return MultiAgentHarnessResult(
            run_id=collaboration.run_id,
            status="completed",
            execution_plan=execution_plan,
            scope_result=scope_result,
            collaboration=collaboration,
            duration_ms=round((perf_counter() - started_at) * 1000, 3),
            scope_mode=scope_runtime.mode,
            scope_provider=scope_runtime.provider,
            scope_model=scope_runtime.model_name,
            scope_model_called=scope_runtime.model_called,
        )

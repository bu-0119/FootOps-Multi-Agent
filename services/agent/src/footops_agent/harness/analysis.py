"""Safety envelope for natural-language Agent analysis runs."""

import asyncio
import logging
from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from footops_agent.api.schemas import AgentAnalysisResponse
from footops_agent.artifacts import (
    AgentAnalysisInput,
    AgentDecision,
    AgentToolTrace,
    ResolvedAgentScope,
)
from footops_agent.config import Settings
from footops_agent.rag import HybridKnowledgeRetriever
from footops_agent.runtime import (
    AnalysisAgentRuntime,
    ChatAgentRuntime,
    DeepSeekAnalysisAgentRuntime,
    DeepSeekChatAgentRuntime,
    DeepSeekKnowledgeAgentRuntime,
    KnowledgeAgentRuntime,
    MockAnalysisAgentRuntime,
    MockChatAgentRuntime,
    MockKnowledgeAgentRuntime,
)
from footops_agent.services import (
    AnalysisWorkspaceService,
    DataCatalogService,
    RequestIntentRouter,
)

from .errors import (
    HarnessError,
    InputTooLongError,
    ModelUnavailableError,
    RunTimeoutError,
    UpstreamModelError,
)
from .multi_agent import FootOpsMultiAgentHarness, MultiAgentHarnessResult

RuntimeFactory = Callable[[], AnalysisAgentRuntime]
ChatRuntimeFactory = Callable[[], ChatAgentRuntime]
KnowledgeRuntimeFactory = Callable[[], KnowledgeAgentRuntime]
logger = logging.getLogger(__name__)


class FootOpsAnalysisHarness:
    """Validate, bound and audit one AgentScope analysis loop."""

    def __init__(
        self,
        settings: Settings,
        catalog: DataCatalogService,
        workspace_service: AnalysisWorkspaceService,
        runtime_factory: RuntimeFactory | None = None,
        chat_runtime_factory: ChatRuntimeFactory | None = None,
        knowledge_runtime_factory: KnowledgeRuntimeFactory | None = None,
        multi_agent_harness: FootOpsMultiAgentHarness | None = None,
        knowledge_retriever: HybridKnowledgeRetriever | None = None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.workspace_service = workspace_service
        self._runtime_factory = runtime_factory
        self._chat_runtime_factory = chat_runtime_factory
        self._knowledge_runtime_factory = knowledge_runtime_factory
        self.knowledge_retriever = knowledge_retriever or HybridKnowledgeRetriever()
        self.multi_agent_harness = multi_agent_harness
        self.intent_router = RequestIntentRouter()

    def _multi_agent_response(
        self,
        result: MultiAgentHarnessResult,
        started_at: float,
    ) -> AgentAnalysisResponse:
        """Project Board output back into the existing user-facing Agent contract."""
        scope_result = result.scope_result
        scope_artifact = scope_result.artifact if scope_result else None
        resolved_scope = (
            ResolvedAgentScope.model_validate(scope_artifact.scope.model_dump())
            if scope_artifact and scope_artifact.scope
            else ResolvedAgentScope()
        )
        collaboration = result.collaboration
        hypothesis = collaboration.hypothesis if collaboration else None
        message = (
            hypothesis.hypothesis
            if hypothesis and hypothesis.status == "grounded"
            else "数据与战术知识已完成联合审核，但当前证据不足以形成受限关联。"
        )
        limitations = list(hypothesis.limitations) if hypothesis else []
        if not limitations:
            limitations = ["当前关联不替代完整比赛视频复盘。"]
        traces = [
            AgentToolTrace(
                sequence=index,
                tool_name=f"{event.actor}:{event.event_type.value}",
                status=(
                    "insufficient"
                    if event.event_type.value
                    in {"CRITIQUE_CREATED", "BUDGET_EXHAUSTED"}
                    else "completed"
                ),
                summary=event.message or event.event_type.value,
            )
            for index, event in enumerate(
                collaboration.events if collaboration else (),
                start=1,
            )
        ]
        status = "completed" if collaboration else result.status
        decision = AgentDecision(
            action=status,  # type: ignore[arg-type]
            message=message,
            resolved_scope=resolved_scope,
            limitations=limitations,
        )
        return AgentAnalysisResponse(
            run_id=result.run_id,
            status=status,  # type: ignore[arg-type]
            mode=result.scope_mode,  # type: ignore[arg-type]
            provider=result.scope_provider,  # type: ignore[arg-type]
            model=result.scope_model,
            model_called=result.scope_model_called,
            data_retrieved=collaboration is not None,
            message=message,
            decision=decision,
            trace=traces,
            duration_ms=round((perf_counter() - started_at) * 1000, 3),
            execution_plan=result.execution_plan,
            usage=scope_result.usage if scope_result else None,
            workspace=collaboration.workspace if collaboration else None,
        )

    def _build_runtime(
        self,
        trace_callback: Callable[[AgentToolTrace], None] | None = None,
    ) -> AnalysisAgentRuntime:
        if self._runtime_factory is not None:
            return self._runtime_factory()
        if self.settings.llm_mode == "mock":
            return MockAnalysisAgentRuntime(
                self.catalog,
                self.workspace_service,
                trace_callback,
            )
        return DeepSeekAnalysisAgentRuntime(
            self.settings,
            self.catalog,
            self.workspace_service,
            trace_callback,
        )

    def _build_chat_runtime(self) -> ChatAgentRuntime:
        if self._chat_runtime_factory is not None:
            return self._chat_runtime_factory()
        if self.settings.llm_mode == "mock":
            return MockChatAgentRuntime()
        return DeepSeekChatAgentRuntime(self.settings)

    def _build_knowledge_runtime(
        self,
        trace_callback: Callable[[AgentToolTrace], None] | None = None,
    ) -> KnowledgeAgentRuntime:
        if self._knowledge_runtime_factory is not None:
            return self._knowledge_runtime_factory()
        if self.settings.llm_mode == "mock":
            return MockKnowledgeAgentRuntime(
                retriever=self.knowledge_retriever,
                trace_callback=trace_callback,
            )
        return DeepSeekKnowledgeAgentRuntime(
            self.settings,
            retriever=self.knowledge_retriever,
            trace_callback=trace_callback,
        )

    async def run(
        self,
        request: AgentAnalysisInput,
        trace_callback: Callable[[AgentToolTrace], None] | None = None,
    ) -> AgentAnalysisResponse:
        """Execute one bounded loop and reject untrusted completion claims."""
        run_id = uuid4().hex
        if len(request.question) > self.settings.footops_input_max_chars:
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

        started_at = perf_counter()
        execution_plan = self.intent_router.plan(request)
        if execution_plan.intent == "chat":
            chat_runtime = self._build_chat_runtime()
            try:
                chat_result = await asyncio.wait_for(
                    chat_runtime.run(request),
                    timeout=self.settings.footops_agent_run_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RunTimeoutError("普通对话请求超时。", run_id) from exc
            except Exception as exc:
                logger.exception(
                    "Conversation run %s failed with %s",
                    run_id,
                    type(exc).__name__,
                )
                raise UpstreamModelError(
                    "普通对话暂时无法完成，请稍后重试。",
                    run_id,
                ) from exc
            decision = AgentDecision(
                action="chat",
                message=chat_result.message,
                resolved_scope=ResolvedAgentScope(),
                limitations=["本次普通对话没有检索或计算比赛数据。"],
            )
            return AgentAnalysisResponse(
                run_id=run_id,
                status="chat",
                mode=chat_runtime.mode,  # type: ignore[arg-type]
                provider=chat_runtime.provider,  # type: ignore[arg-type]
                model=chat_runtime.model_name,
                model_called=chat_runtime.model_called,
                data_retrieved=False,
                message=chat_result.message,
                decision=decision,
                trace=[],
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                execution_plan=execution_plan,
                usage=chat_result.usage,
                workspace=None,
            )

        if execution_plan.need_match_data and (
            execution_plan.need_rule_rag or execution_plan.need_metric_rag
        ):
            message = (
                "比赛数据与规则或指标口径的联合链路尚未开放，请先分别提问。"
            )
            decision = AgentDecision(
                action="unsupported",
                message=message,
                resolved_scope=ResolvedAgentScope(),
                limitations=["当前规则/指标知识链与比赛数据链保持独立。"],
            )
            return AgentAnalysisResponse(
                run_id=run_id,
                status="unsupported",
                mode=self.settings.llm_mode,
                provider="none",
                model="none",
                model_called=False,
                data_retrieved=False,
                message=message,
                decision=decision,
                trace=[],
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                execution_plan=execution_plan,
                usage=None,
                workspace=None,
            )

        if execution_plan.intent == "hybrid_tactical_analysis":
            if self.multi_agent_harness is None:
                raise UpstreamModelError(
                    "多 Agent 战术联合运行时未配置。",
                    run_id,
                )
            try:
                result = await self.multi_agent_harness.run(request)
            except HarnessError:
                raise
            except Exception as exc:
                logger.exception(
                    "Hybrid multi-agent run %s failed with %s",
                    run_id,
                    type(exc).__name__,
                )
                raise UpstreamModelError(
                    "多 Agent 未能完成数据与战术知识联合分析。",
                    run_id,
                ) from exc
            return self._multi_agent_response(result, started_at)

        if (
            execution_plan.need_rule_rag
            or execution_plan.need_tactical_rag
            or execution_plan.need_metric_rag
        ):
            domains = tuple(
                domain
                for required, domain in (
                    (execution_plan.need_rule_rag, "rule"),
                    (execution_plan.need_tactical_rag, "tactics"),
                    (execution_plan.need_metric_rag, "metric_definition"),
                )
                if required
            )
            knowledge_runtime = self._build_knowledge_runtime(trace_callback)
            try:
                knowledge_result = await asyncio.wait_for(
                    knowledge_runtime.run(request, domains),  # type: ignore[arg-type]
                    timeout=self.settings.footops_agent_run_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RunTimeoutError("KnowledgeAgent 知识检索超时。", run_id) from exc
            except Exception as exc:
                logger.exception(
                    "KnowledgeAgent run %s failed with %s",
                    run_id,
                    type(exc).__name__,
                )
                raise UpstreamModelError(
                    "KnowledgeAgent 未能返回可验证的知识答案。",
                    run_id,
                ) from exc

            answered = knowledge_result.answer.status == "answered"
            decision = AgentDecision(
                action="completed" if answered else "unsupported",
                message=knowledge_result.answer.answer,
                resolved_scope=ResolvedAgentScope(),
                limitations=knowledge_result.answer.limitations,
            )
            return AgentAnalysisResponse(
                run_id=run_id,
                status=decision.action,
                mode=knowledge_runtime.mode,  # type: ignore[arg-type]
                provider=knowledge_runtime.provider,  # type: ignore[arg-type]
                model=knowledge_runtime.model_name,
                model_called=knowledge_runtime.model_called,
                data_retrieved=False,
                message=decision.message,
                decision=decision,
                trace=knowledge_result.trace,
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                execution_plan=execution_plan,
                usage=knowledge_result.usage,
                knowledge_evidence=knowledge_result.evidence,
                knowledge_answer=knowledge_result.answer,
                workspace=None,
            )

        runtime = self._build_runtime(trace_callback)
        try:
            result = await asyncio.wait_for(
                runtime.run(request),
                timeout=self.settings.footops_agent_run_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RunTimeoutError("Agent 分析请求超时。", run_id) from exc
        except HarnessError:
            raise
        except Exception as exc:
            logger.exception(
                "Agent run %s failed with %s",
                run_id,
                type(exc).__name__,
            )
            raise UpstreamModelError(
                "Agent 未能完成有效的工具调度，请稍后重试。",
                run_id,
            ) from exc

        if result.decision.action == "completed" and result.workspace is None:
            raise UpstreamModelError(
                "Agent 返回了无工作区的完成状态。",
                run_id,
            )
        return AgentAnalysisResponse(
            run_id=run_id,
            status=result.decision.action,
            mode=runtime.mode,
            provider=runtime.provider,  # type: ignore[arg-type]
            model=runtime.model_name,
            model_called=runtime.model_called,
            data_retrieved=result.workspace is not None,
            message=result.decision.message,
            decision=result.decision,
            trace=result.trace,
            duration_ms=round((perf_counter() - started_at) * 1000, 3),
            execution_plan=execution_plan,
            usage=result.usage,
            workspace=result.workspace,
        )

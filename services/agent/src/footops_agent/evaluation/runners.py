"""Adapters that expose three comparison modes through one eval interface."""

import asyncio
from time import perf_counter
from typing import Protocol

from footops_agent.artifacts import AgentAnalysisInput, AnalysisWorkspace
from footops_agent.collaboration import (
    CollaborationEventType,
    MultiAgentAnalysisRequest,
)
from footops_agent.harness import FootOpsAnalysisHarness, HarnessError
from footops_agent.runtime import (
    DeepSeekDirectLlmRuntime,
    FootOpsMultiAgentRuntime,
    ScopeAgentRuntime,
)
from footops_agent.services import (
    AnalysisWorkspaceService,
    InsufficientDataError,
    PlayerNotFoundError,
    RequestIntentRouter,
    UnsupportedAnalysisQuestionError,
)

from .models import EvaluationMode, EvaluationObservation, GoldenTask


class EvaluationRunner(Protocol):
    mode: EvaluationMode

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        """Execute one golden task without raising an expected run failure."""


class DeterministicEvaluationRunner:
    """Call the deterministic workspace service with explicit scope only."""

    mode: EvaluationMode = "deterministic"

    def __init__(self, workspace_service: AnalysisWorkspaceService) -> None:
        self.workspace_service = workspace_service

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        started_at = perf_counter()
        hint = task.scope_hint
        if (
            hint.competition_id is None
            or hint.season_id is None
            or hint.player is None
        ):
            return self._observation(
                "clarification_required",
                "确定性直调需要显式赛事、赛季和球员范围。",
                started_at,
            )
        try:
            workspace = await asyncio.to_thread(
                self.workspace_service.create,
                task.question,
                hint.competition_id,
                hint.season_id,
                hint.player,
                hint.requested_window or 5,
                hint.player_id,
            )
        except UnsupportedAnalysisQuestionError:
            return self._observation(
                "unsupported",
                UnsupportedAnalysisQuestionError.public_message,
                started_at,
            )
        except (PlayerNotFoundError, InsufficientDataError) as exc:
            return self._observation(
                "clarification_required",
                str(exc),
                started_at,
            )
        except Exception as exc:
            return self._observation(
                "error",
                "确定性链路执行失败。",
                started_at,
                error_type=type(exc).__name__,
            )
        return EvaluationObservation(
            mode=self.mode,
            status="completed",
            message="确定性链路已完成。",
            duration_ms=_elapsed_ms(started_at),
            model_called=False,
            model_name="none",
            workspace_id=workspace.workspace_id,
            finding_count=len(workspace.findings),
            claim_support_rate=_claim_support_rate(workspace),
            stopping_reason=workspace.status,
        )

    def _observation(
        self,
        status: str,
        message: str,
        started_at: float,
        error_type: str | None = None,
    ) -> EvaluationObservation:
        return EvaluationObservation(
            mode=self.mode,
            status=status,  # type: ignore[arg-type]
            message=message,
            duration_ms=_elapsed_ms(started_at),
            model_called=False,
            model_name="none",
            stopping_reason=status,
            error_type=error_type,
        )


class DirectLlmEvaluationRunner:
    """Run one model response without data or tools."""

    mode: EvaluationMode = "direct_llm"

    def __init__(self, runtime: DeepSeekDirectLlmRuntime) -> None:
        self.runtime = runtime

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        started_at = perf_counter()
        try:
            result = await self.runtime.run(_request(task))
        except Exception as exc:
            return EvaluationObservation(
                mode=self.mode,
                status="error",
                message="直接 LLM 基线执行失败。",
                duration_ms=_elapsed_ms(started_at),
                model_called=True,
                model_name=self.runtime.model_name,
                stopping_reason="error",
                error_type=type(exc).__name__,
            )
        return EvaluationObservation(
            mode=self.mode,
            status=result.decision.action,
            message=result.decision.message,
            duration_ms=_elapsed_ms(started_at),
            model_called=True,
            model_name=self.runtime.model_name,
            usage=result.usage,
            stopping_reason=result.decision.action,
        )


class SingleAgentEvaluationRunner:
    """Run the current AgentScope ReAct + Skill + Tools implementation."""

    mode: EvaluationMode = "single_agent"

    def __init__(self, harness: FootOpsAnalysisHarness) -> None:
        self.harness = harness

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        try:
            response = await self.harness.run(_request(task))
        except HarnessError as exc:
            return EvaluationObservation(
                mode=self.mode,
                status="error",
                message=exc.public_message,
                duration_ms=0,
                model_called=True,
                model_name=self.harness.settings.deepseek_model,
                stopping_reason=exc.code,
                error_type=type(exc).__name__,
            )
        workspace = response.workspace
        return EvaluationObservation(
            mode=self.mode,
            status=response.status,
            message=response.message,
            duration_ms=response.duration_ms,
            model_called=response.model_called,
            model_name=response.model,
            tool_sequence=[item.tool_name for item in response.trace],
            workspace_id=workspace.workspace_id if workspace is not None else None,
            finding_count=len(workspace.findings) if workspace is not None else 0,
            claim_support_rate=(
                _claim_support_rate(workspace) if workspace is not None else None
            ),
            usage=response.usage,
            stopping_reason=response.status,
        )


class MultiAgentEvaluationRunner:
    """Run the MindBridge-style event-driven domain-agent collaboration."""

    mode: EvaluationMode = "multi_agent"

    def __init__(
        self,
        runtime: FootOpsMultiAgentRuntime,
        scope_runtime: ScopeAgentRuntime,
    ) -> None:
        self.runtime = runtime
        self.scope_runtime = scope_runtime
        self.intent_router = RequestIntentRouter()

    async def run(self, task: GoldenTask) -> EvaluationObservation:
        started_at = perf_counter()
        request = _request(task)
        execution_plan = self.intent_router.plan(request)
        if execution_plan.intent == "chat":
            return EvaluationObservation(
                mode=self.mode,
                status="chat",
                message="普通对话由入口路由直接回复，不启动多 Agent。",
                duration_ms=_elapsed_ms(started_at),
                model_called=False,
                model_name="none",
                stopping_reason="chat_bypass",
            )
        if execution_plan.need_rule_rag or execution_plan.need_tactical_rag:
            return EvaluationObservation(
                mode=self.mode,
                status="unsupported",
                message="Knowledge RAG 尚未接入，未启动 ScopeAgent 或比赛数据工具。",
                duration_ms=_elapsed_ms(started_at),
                model_called=False,
                model_name="none",
                stopping_reason="knowledge_rag_unavailable",
            )
        try:
            scope_result = await self.scope_runtime.run(request)
        except Exception as exc:
            return EvaluationObservation(
                mode=self.mode,
                status="error",
                message="ScopeAgent 范围解析失败。",
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                stopping_reason="scope_error",
                error_type=type(exc).__name__,
            )
        scope_artifact = scope_result.artifact
        if scope_artifact.status != "resolved":
            return EvaluationObservation(
                mode=self.mode,
                status="clarification_required",
                message=scope_artifact.message,
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                tool_sequence=[item.tool_name for item in scope_result.trace],
                usage=scope_result.usage,
                stopping_reason="clarification_required",
            )
        scope = scope_artifact.scope
        if (
            scope.competition_id is None
            or scope.season_id is None
            or scope.player is None
            or scope.player_id is None
            or scope.requested_window is None
        ):
            return EvaluationObservation(
                mode=self.mode,
                status="error",
                message="ScopeAgent 返回的范围不完整。",
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                tool_sequence=[item.tool_name for item in scope_result.trace],
                usage=scope_result.usage,
                stopping_reason="invalid_scope",
            )
        try:
            result = await asyncio.to_thread(
                self.runtime.run,
                MultiAgentAnalysisRequest(
                    question=task.question,
                    competition_id=scope.competition_id,
                    season_id=scope.season_id,
                    player_query=scope.player,
                    requested_window=scope.requested_window,
                    player_id=scope.player_id,
                ),
            )
        except UnsupportedAnalysisQuestionError:
            return EvaluationObservation(
                mode=self.mode,
                status="unsupported",
                message=UnsupportedAnalysisQuestionError.public_message,
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                usage=scope_result.usage,
                stopping_reason="unsupported",
            )
        except (PlayerNotFoundError, InsufficientDataError) as exc:
            return EvaluationObservation(
                mode=self.mode,
                status="clarification_required",
                message=str(exc),
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                usage=scope_result.usage,
                stopping_reason="clarification_required",
            )
        except Exception as exc:
            return EvaluationObservation(
                mode=self.mode,
                status="error",
                message="多 Agent 编排执行失败。",
                duration_ms=_elapsed_ms(started_at),
                model_called=self.scope_runtime.model_called,
                model_name=self.scope_runtime.model_name,
                usage=scope_result.usage,
                stopping_reason="error",
                error_type=type(exc).__name__,
            )
        workspace = result.workspace
        return EvaluationObservation(
            mode=self.mode,
            status="completed",
            message="多 Agent 已完成协作并由 CoordinatorAgent 采纳。",
            duration_ms=_elapsed_ms(started_at),
            model_called=self.scope_runtime.model_called,
            model_name=self.scope_runtime.model_name,
            tool_sequence=[item.tool_name for item in scope_result.trace]
            + [
                event.actor
                for event in result.events
                if event.event_type == CollaborationEventType.TASK_CLAIMED
            ],
            workspace_id=workspace.workspace_id,
            finding_count=len(workspace.findings),
            claim_support_rate=_claim_support_rate(workspace),
            usage=scope_result.usage,
            stopping_reason="final_accepted",
        )


def _request(task: GoldenTask) -> AgentAnalysisInput:
    return AgentAnalysisInput(question=task.question, scope_hint=task.scope_hint)


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def _claim_support_rate(workspace: AnalysisWorkspace) -> float:
    findings = workspace.findings
    review = workspace.evidence_review
    if not findings or review is None:
        return 0.0
    accepted = {
        item.finding_id
        for item in review.reviews
        if item.status == "supported"
    }
    return len(accepted.intersection(item.finding_id for item in findings)) / len(
        findings
    )

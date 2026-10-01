"""FastAPI application for the FootOps analysis service."""

import asyncio
from collections.abc import AsyncIterator
from importlib.metadata import version
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from footops_agent.artifacts import AgentAnalysisInput, AgentToolTrace
from footops_agent.collaboration import MultiAgentAnalysisRequest
from footops_agent.config import Settings
from footops_agent.harness import (
    FootOpsAgentHarness,
    FootOpsAnalysisHarness,
    FootOpsMultiAgentHarness,
    HarnessError,
)
from footops_agent.providers import (
    DataProviderError,
    FootballDataProvider,
    StatsBombOpenDataProvider,
)
from footops_agent.rag import HybridKnowledgeRetriever, RedisVectorKnowledgeIndex
from footops_agent.repositories import (
    AnalysisWorkspaceRepository,
    InMemoryAnalysisWorkspaceRepository,
    WorkspaceNotFoundError,
)
from footops_agent.runtime import FootOpsMultiAgentRuntime
from footops_agent.services import (
    AnalysisWorkspaceService,
    DataCatalogService,
    InsufficientDataError,
    PlayerNotFoundError,
    PlayerRoleAnalysisService,
    PlayerRoleFindingReviewService,
    UnsupportedAnalysisQuestionError,
)

from .schemas import (
    AgentAnalysisRequest,
    AgentAnalysisResponse,
    AgentRunStreamEvent,
    AnalysisPlanRequest,
    AnalysisPlanResponse,
    AnalysisStreamEvent,
    AnalysisWorkspaceCreateRequest,
    AnalysisWorkspaceResponse,
    CompetitionCatalogResponse,
    DataCoverageAuditResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    LlmStatusResponse,
    MultiAgentAnalysisResponse,
    MultiAgentRunResponse,
    MultiAgentStreamEvent,
    MultiAgentTraceEvent,
    PlayerCatalogResponse,
    PlayerDataRequest,
    PlayerRoleFindingReviewResponse,
    PlayerRoleMetricsResponse,
)


def _sse(event: BaseModel) -> str:
    return f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"


def create_app(
    settings: Settings | None = None,
    harness: FootOpsAgentHarness | None = None,
    data_provider: FootballDataProvider | None = None,
    workspace_repository: AnalysisWorkspaceRepository | None = None,
    analysis_harness: FootOpsAnalysisHarness | None = None,
    multi_agent_harness: FootOpsMultiAgentHarness | None = None,
) -> FastAPI:
    """Build the application with injectable settings for tests."""
    settings = settings or Settings()
    harness = harness or FootOpsAgentHarness(settings)
    data_provider = data_provider or StatsBombOpenDataProvider(settings)
    data_catalog = DataCatalogService(data_provider)
    player_role_service = PlayerRoleAnalysisService(data_provider)
    finding_review_service = PlayerRoleFindingReviewService(data_provider)
    vector_index = (
        RedisVectorKnowledgeIndex(settings)
        if settings.footops_vector_rag_enabled
        else None
    )
    knowledge_retriever = HybridKnowledgeRetriever(vector_index=vector_index)
    workspace_repository = workspace_repository or InMemoryAnalysisWorkspaceRepository()
    workspace_service = AnalysisWorkspaceService(data_provider, workspace_repository)
    multi_agent_runtime = FootOpsMultiAgentRuntime(
        data_provider,
        workspace_repository,
        knowledge_retriever=knowledge_retriever,
    )
    multi_agent_harness = multi_agent_harness or FootOpsMultiAgentHarness(
        settings,
        data_catalog,
        multi_agent_runtime,
    )
    analysis_harness = analysis_harness or FootOpsAnalysisHarness(
        settings,
        data_catalog,
        workspace_service,
        multi_agent_harness=multi_agent_harness,
        knowledge_retriever=knowledge_retriever,
    )
    app = FastAPI(title="FootOps Agent API", version="0.1.0")
    app.state.knowledge_retriever = knowledge_retriever
    if vector_index is not None:
        app.router.add_event_handler("shutdown", vector_index.close)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.footops_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(HarnessError)
    async def handle_harness_error(
        _request: Request,
        exc: HarnessError,
    ) -> JSONResponse:
        body = ErrorResponse(
            run_id=exc.run_id,
            error=ErrorBody(code=exc.code, message=exc.public_message),
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="invalid_request",
                message="请求体必须包含非空字符串 question。",
            ),
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(DataProviderError)
    async def handle_data_provider_error(
        _request: Request,
        _exc: DataProviderError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="data_provider_error",
                message="公开比赛数据暂时不可用或返回了无效内容。",
            ),
        )
        return JSONResponse(status_code=502, content=body.model_dump())

    @app.exception_handler(InsufficientDataError)
    async def handle_insufficient_data(
        _request: Request,
        _exc: InsufficientDataError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="insufficient_data",
                message="公开数据不足以构成至少两场比赛的分析窗口。",
            ),
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(PlayerNotFoundError)
    async def handle_player_not_found(
        _request: Request,
        _exc: PlayerNotFoundError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="player_not_found",
                message="所选赛事和赛季中没有找到该球员的公开出场数据。",
            ),
        )
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(WorkspaceNotFoundError)
    async def handle_workspace_not_found(
        _request: Request,
        _exc: WorkspaceNotFoundError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="workspace_not_found",
                message="未找到指定的分析工作区。",
            ),
        )
        return JSONResponse(status_code=404, content=body.model_dump())

    @app.exception_handler(UnsupportedAnalysisQuestionError)
    async def handle_unsupported_question(
        _request: Request,
        _exc: UnsupportedAnalysisQuestionError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorBody(
                code="unsupported_analysis_question",
                message=UnsupportedAnalysisQuestionError.public_message,
            ),
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1/llm/status", response_model=LlmStatusResponse)
    async def llm_status() -> LlmStatusResponse:
        if settings.llm_mode == "mock":
            return LlmStatusResponse(
                status="ready",
                mode="mock",
                provider="none",
                model="mock",
                key_configured=False,
                agentscope_version=version("agentscope"),
                message="mock 模式可用；不会调用模型或检索数据。",
            )
        is_ready = settings.deepseek_key_configured
        return LlmStatusResponse(
            status="ready" if is_ready else "unavailable",
            mode="deepseek",
            provider="deepseek",
            model=settings.deepseek_model,
            key_configured=is_ready,
            agentscope_version=version("agentscope"),
            message=(
                "DeepSeek 配置可用。"
                if is_ready
                else "缺少 DEEPSEEK_API_KEY，计划接口将返回 503。"
            ),
        )

    @app.get(
        "/api/v1/catalog/competitions",
        response_model=CompetitionCatalogResponse,
        responses={502: {"model": ErrorResponse}},
    )
    def list_competitions() -> CompetitionCatalogResponse:
        return CompetitionCatalogResponse(
            competitions=data_catalog.list_competitions(),
        )

    @app.get(
        "/api/v1/catalog/players",
        response_model=PlayerCatalogResponse,
        responses={502: {"model": ErrorResponse}},
    )
    def list_players(
        competition_id: int,
        season_id: int,
    ) -> PlayerCatalogResponse:
        competition, players = data_catalog.list_players(
            competition_id,
            season_id,
        )
        return PlayerCatalogResponse(
            competition=competition,
            players=players,
        )

    @app.post(
        "/api/v1/agent/runs",
        response_model=AgentAnalysisResponse,
        responses={
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def run_analysis_agent(
        payload: AgentAnalysisRequest,
    ) -> AgentAnalysisResponse:
        return await analysis_harness.run(
            AgentAnalysisInput(
                question=payload.question,
                scope_hint=payload.to_scope_hint(),
                history=payload.history,
            )
        )

    @app.post(
        "/api/v1/agent/runs/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "Versioned Agent harness business events.",
                "content": {"text/event-stream": {}},
            },
            422: {"model": ErrorResponse},
        },
    )
    async def stream_analysis_agent(
        payload: AgentAnalysisRequest,
    ) -> StreamingResponse:
        request_id = uuid4().hex
        request = AgentAnalysisInput(
            question=payload.question,
            scope_hint=payload.to_scope_hint(),
            history=payload.history,
        )

        async def events() -> AsyncIterator[str]:
            queue: asyncio.Queue[AgentToolTrace] = asyncio.Queue()
            sequence = 1
            yield _sse(
                AgentRunStreamEvent(
                    event="agent.started",
                    request_id=request_id,
                    sequence=sequence,
                    message="Agent 正在解析问题并选择受控工具。",
                )
            )

            task = asyncio.create_task(
                analysis_harness.run(request, queue.put_nowait)
            )
            while not task.done() or not queue.empty():
                try:
                    trace = await asyncio.wait_for(queue.get(), timeout=0.1)
                except TimeoutError:
                    continue
                sequence += 1
                yield _sse(
                    AgentRunStreamEvent(
                        event="agent.tool.completed",
                        request_id=request_id,
                        sequence=sequence,
                        message=trace.summary,
                        trace=trace,
                    )
                )

            try:
                response = await task
            except HarnessError as exc:
                sequence += 1
                yield _sse(
                    AgentRunStreamEvent(
                        event="agent.error",
                        request_id=request_id,
                        sequence=sequence,
                        message="Agent 执行失败。",
                        error=ErrorBody(
                            code=exc.code,
                            message=exc.public_message,
                        ),
                    )
                )
                return

            final_event = {
                "chat": "agent.chat_completed",
                "completed": "agent.completed",
                "clarification_required": "agent.clarification_required",
                "unsupported": "agent.unsupported",
            }[response.status]
            sequence += 1
            yield _sse(
                AgentRunStreamEvent(
                    event=final_event,  # type: ignore[arg-type]
                    request_id=request_id,
                    sequence=sequence,
                    message=response.message,
                    response=response,
                )
            )

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post(
        "/api/v1/multi-agent/runs",
        response_model=MultiAgentRunResponse,
        responses={
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def run_natural_language_multi_agent(
        payload: AgentAnalysisRequest,
    ) -> MultiAgentRunResponse:
        result = await multi_agent_harness.run(
            AgentAnalysisInput(
                question=payload.question,
                scope_hint=payload.to_scope_hint(),
                history=payload.history,
            )
        )
        collaboration = result.collaboration
        if result.status == "unsupported":
            return MultiAgentRunResponse(
                run_id=result.run_id,
                status="unsupported",
                model_called=False,
                model="none",
                message=(
                    "该请求需要普通对话或 Knowledge RAG；当前多 Agent 数据分析入口"
                    "没有启动范围解析和比赛工具。"
                ),
                duration_ms=result.duration_ms,
                execution_plan=result.execution_plan,
            )
        if collaboration is None:
            if result.scope_result is None:
                raise RuntimeError("scope result is required for clarification")
            return MultiAgentRunResponse(
                run_id=result.run_id,
                status="clarification_required",
                model_called=result.scope_model_called,
                model=result.scope_model,
                message=result.scope_result.artifact.message,
                duration_ms=result.duration_ms,
                execution_plan=result.execution_plan,
                scope=result.scope_result.artifact,
                scope_trace=result.scope_result.trace,
                usage=result.scope_result.usage,
            )
        rounds = max(
            (
                int(event.metadata["round"])
                for event in collaboration.events
                if "round" in event.metadata
            ),
            default=1,
        )
        return MultiAgentRunResponse(
            run_id=result.run_id,
            status="completed",
            model_called=result.scope_model_called,
            model=result.scope_model,
            message="范围已核验，多 Agent 已完成分析并通过证据审核。",
            duration_ms=result.duration_ms,
            execution_plan=result.execution_plan,
            scope=result.scope_result.artifact,
            scope_trace=result.scope_result.trace,
            usage=result.scope_result.usage,
            agents=["FootOpsScopeAgent", *collaboration.agent_names],
            rounds=rounds,
            trace=[
                MultiAgentTraceEvent(
                    sequence=index,
                    event_type=event.event_type.value,
                    actor=event.actor,
                    task_id=event.task_id,
                    artifact_id=event.artifact_id,
                    message=event.message,
                )
                for index, event in enumerate(collaboration.events, start=1)
            ],
            workspace=collaboration.workspace,
        )

    @app.post(
        "/api/v1/multi-agent/runs/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": (
                    "Versioned user-facing multi-agent collaboration events."
                ),
                "content": {"text/event-stream": {}},
            },
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def stream_natural_language_multi_agent(
        payload: AgentAnalysisRequest,
    ) -> StreamingResponse:
        request_id = uuid4().hex

        async def events() -> AsyncIterator[str]:
            sequence = 1
            yield _sse(
                MultiAgentStreamEvent(
                    event="multi_agent.started",
                    request_id=request_id,
                    sequence=sequence,
                    message="正在处理你的问题。",
                )
            )
            try:
                response = await run_natural_language_multi_agent(payload)
            except HarnessError as exc:
                sequence += 1
                yield _sse(
                    MultiAgentStreamEvent(
                        event="multi_agent.error",
                        request_id=request_id,
                        sequence=sequence,
                        message="处理失败。",
                        error=ErrorBody(
                            code=exc.code,
                            message=exc.public_message,
                        ),
                    )
                )
                return

            for trace in response.trace:
                sequence += 1
                yield _sse(
                    MultiAgentStreamEvent(
                        event="multi_agent.collaboration",
                        request_id=request_id,
                        sequence=sequence,
                        message=trace.message or trace.event_type,
                        trace=trace,
                    )
                )
            sequence += 1
            final_event = {
                "completed": "multi_agent.completed",
                "clarification_required": "multi_agent.clarification_required",
                "unsupported": "multi_agent.unsupported",
            }[response.status]
            yield _sse(
                MultiAgentStreamEvent(
                    event=final_event,  # type: ignore[arg-type]
                    request_id=request_id,
                    sequence=sequence,
                    message=response.message,
                    response=response,
                )
            )

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post(
        "/api/v1/multi-agent/analyses",
        response_model=MultiAgentAnalysisResponse,
        status_code=201,
        responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def run_multi_agent_analysis(
        payload: AnalysisWorkspaceCreateRequest,
    ) -> MultiAgentAnalysisResponse:
        result = multi_agent_runtime.run(
            MultiAgentAnalysisRequest(
                question=payload.question,
                competition_id=payload.competition_id,
                season_id=payload.season_id,
                player_query=payload.player,
                requested_window=payload.requested_window,
                player_id=payload.player_id,
            )
        )
        rounds = max(
            (
                int(event.metadata["round"])
                for event in result.events
                if "round" in event.metadata
            ),
            default=1,
        )
        return MultiAgentAnalysisResponse(
            run_id=result.run_id,
            agents=list(result.agent_names),
            rounds=rounds,
            trace=[
                MultiAgentTraceEvent(
                    sequence=index,
                    event_type=event.event_type.value,
                    actor=event.actor,
                    task_id=event.task_id,
                    artifact_id=event.artifact_id,
                    message=event.message,
                )
                for index, event in enumerate(result.events, start=1)
            ],
            workspace=result.workspace,
        )

    @app.post(
        "/api/v1/analyses",
        response_model=AnalysisWorkspaceResponse,
        status_code=201,
        responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def create_analysis_workspace(
        payload: AnalysisWorkspaceCreateRequest,
    ) -> AnalysisWorkspaceResponse:
        workspace = workspace_service.create(
            payload.question,
            payload.competition_id,
            payload.season_id,
            payload.player,
            payload.requested_window,
            payload.player_id,
        )
        return AnalysisWorkspaceResponse(
            workspace=workspace,
            tactics_board_generated=workspace.tactics_board is not None,
        )

    @app.post(
        "/api/v1/analyses/stream",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": "Versioned analysis business events.",
                "content": {"text/event-stream": {}},
            },
            422: {"model": ErrorResponse},
        },
    )
    async def stream_analysis_workspace(
        payload: AnalysisWorkspaceCreateRequest,
    ) -> StreamingResponse:
        request_id = str(uuid4())

        async def events() -> AsyncIterator[str]:
            yield _sse(
                AnalysisStreamEvent(
                    event="analysis.status",
                    request_id=request_id,
                    sequence=1,
                    message="正在校验问题范围并准备确定性分析。",
                )
            )
            try:
                workspace = await asyncio.to_thread(
                    workspace_service.create,
                    payload.question,
                    payload.competition_id,
                    payload.season_id,
                    payload.player,
                    payload.requested_window,
                    payload.player_id,
                )
            except DataProviderError:
                yield _sse(
                    AnalysisStreamEvent(
                        event="analysis.error",
                        request_id=request_id,
                        sequence=2,
                        message="分析失败。",
                        error=ErrorBody(
                            code="data_provider_error",
                            message="公开比赛数据暂时不可用或返回了无效内容。",
                        ),
                    )
                )
                return
            except InsufficientDataError:
                yield _sse(
                    AnalysisStreamEvent(
                        event="analysis.error",
                        request_id=request_id,
                        sequence=2,
                        message="分析失败。",
                        error=ErrorBody(
                            code="insufficient_data",
                            message="公开数据不足以构成至少两场比赛的分析窗口。",
                        ),
                    )
                )
                return
            except PlayerNotFoundError:
                yield _sse(
                    AnalysisStreamEvent(
                        event="analysis.error",
                        request_id=request_id,
                        sequence=2,
                        message="未找到球员数据。",
                        error=ErrorBody(
                            code="player_not_found",
                            message=("所选赛事和赛季中没有找到该球员的公开出场数据。"),
                        ),
                    )
                )
                return
            except UnsupportedAnalysisQuestionError:
                yield _sse(
                    AnalysisStreamEvent(
                        event="analysis.error",
                        request_id=request_id,
                        sequence=2,
                        message="当前问题不在可执行范围内。",
                        error=ErrorBody(
                            code="unsupported_analysis_question",
                            message=UnsupportedAnalysisQuestionError.public_message,
                        ),
                    )
                )
                return

            response = AnalysisWorkspaceResponse(
                workspace=workspace,
                tactics_board_generated=workspace.tactics_board is not None,
            )
            yield _sse(
                AnalysisStreamEvent(
                    event="analysis.completed",
                    request_id=request_id,
                    sequence=2,
                    message="分析工作区已生成。",
                    response=response,
                )
            )

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get(
        "/api/v1/analyses/{workspace_id}",
        response_model=AnalysisWorkspaceResponse,
        responses={404: {"model": ErrorResponse}},
    )
    def get_analysis_workspace(workspace_id: str) -> AnalysisWorkspaceResponse:
        workspace = workspace_service.get(workspace_id)
        return AnalysisWorkspaceResponse(
            workspace=workspace,
            tactics_board_generated=workspace.tactics_board is not None,
        )

    @app.post(
        "/api/v1/analyses/plan",
        response_model=AnalysisPlanResponse,
        responses={
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            502: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
            504: {"model": ErrorResponse},
        },
    )
    async def create_analysis_plan(
        payload: AnalysisPlanRequest,
    ) -> AnalysisPlanResponse:
        return await harness.run_plan(payload.question)

    @app.post(
        "/api/v1/data/coverage-audit",
        response_model=DataCoverageAuditResponse,
        responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def audit_player_data(payload: PlayerDataRequest) -> DataCoverageAuditResponse:
        audit = data_catalog.audit_player(
            payload.competition_id,
            payload.season_id,
            payload.player,
            payload.requested_window,
            payload.player_id,
        )
        return DataCoverageAuditResponse(audit=audit)

    @app.post(
        "/api/v1/metrics/player-role",
        response_model=PlayerRoleMetricsResponse,
        responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def calculate_player_role_metrics(
        payload: PlayerDataRequest,
    ) -> PlayerRoleMetricsResponse:
        audit, metrics = player_role_service.calculate(
            payload.competition_id,
            payload.season_id,
            payload.player,
            payload.requested_window,
            payload.player_id,
        )
        return PlayerRoleMetricsResponse(audit=audit, metrics=metrics)

    @app.post(
        "/api/v1/findings/player-role/review",
        response_model=PlayerRoleFindingReviewResponse,
        responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    )
    def review_player_role_findings(
        payload: PlayerDataRequest,
    ) -> PlayerRoleFindingReviewResponse:
        audit, metrics, findings, evidence, review = finding_review_service.review(
            payload.competition_id,
            payload.season_id,
            payload.player,
            payload.requested_window,
            payload.player_id,
        )
        return PlayerRoleFindingReviewResponse(
            audit=audit,
            metrics=metrics,
            findings=findings,
            evidence=evidence,
            evidence_review=review,
        )

    return app


app = create_app()


def run() -> None:
    """Run the local development server."""
    uvicorn.run(
        "footops_agent.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()

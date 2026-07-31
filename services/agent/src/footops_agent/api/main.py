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

from footops_agent.config import Settings
from footops_agent.harness import FootOpsAgentHarness, HarnessError
from footops_agent.providers import (
    DataProviderError,
    FootballDataProvider,
    StatsBombOpenDataProvider,
)
from footops_agent.repositories import (
    AnalysisWorkspaceRepository,
    InMemoryAnalysisWorkspaceRepository,
    WorkspaceNotFoundError,
)
from footops_agent.services import (
    AnalysisWorkspaceService,
    DataCatalogService,
    InsufficientDataError,
    PlayerRoleAnalysisService,
    PlayerRoleFindingReviewService,
)

from .schemas import (
    AnalysisPlanRequest,
    AnalysisPlanResponse,
    AnalysisStreamEvent,
    AnalysisWorkspaceCreateRequest,
    AnalysisWorkspaceResponse,
    DataCoverageAuditResponse,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    LlmStatusResponse,
    PlayerDataRequest,
    PlayerRoleFindingReviewResponse,
    PlayerRoleMetricsResponse,
)


def _sse(event: AnalysisStreamEvent) -> str:
    return f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"


def create_app(
    settings: Settings | None = None,
    harness: FootOpsAgentHarness | None = None,
    data_provider: FootballDataProvider | None = None,
    workspace_repository: AnalysisWorkspaceRepository | None = None,
) -> FastAPI:
    """Build the application with injectable settings for tests."""
    settings = settings or Settings()
    harness = harness or FootOpsAgentHarness(settings)
    data_provider = data_provider or StatsBombOpenDataProvider(settings)
    data_catalog = DataCatalogService(data_provider)
    player_role_service = PlayerRoleAnalysisService(data_provider)
    finding_review_service = PlayerRoleFindingReviewService(data_provider)
    workspace_repository = (
        workspace_repository or InMemoryAnalysisWorkspaceRepository()
    )
    workspace_service = AnalysisWorkspaceService(data_provider, workspace_repository)
    app = FastAPI(title="FootOps Agent API", version="0.1.0")
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
                message="公开数据不足以构成至少三场比赛的分析窗口。",
            ),
        )
        return JSONResponse(status_code=422, content=body.model_dump())

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
        )
        return AnalysisWorkspaceResponse(workspace=workspace)

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
                    message="正在检索公开比赛数据并执行确定性分析。",
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
                            message="公开数据不足以构成至少三场比赛的分析窗口。",
                        ),
                    )
                )
                return

            response = AnalysisWorkspaceResponse(workspace=workspace)
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
        return AnalysisWorkspaceResponse(workspace=workspace_service.get(workspace_id))

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

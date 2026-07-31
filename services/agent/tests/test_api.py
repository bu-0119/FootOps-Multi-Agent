"""FastAPI contract tests."""

from fastapi.testclient import TestClient

from footops_agent.api.main import create_app
from footops_agent.config import Settings


def make_client(**overrides: object) -> TestClient:
    settings = Settings(_env_file=None, **overrides)
    return TestClient(create_app(settings=settings))


def test_health_and_mock_status() -> None:
    with make_client(llm_mode="mock") as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "service": "footops-agent",
        }
        status = client.get("/api/v1/llm/status").json()

    assert status["status"] == "ready"
    assert status["mode"] == "mock"
    assert status["key_configured"] is False
    assert status["agentscope_version"] == "2.0.5"


def test_mock_plan_contract() -> None:
    with make_client(llm_mode="mock") as client:
        response = client.post(
            "/api/v1/analyses/plan",
            json={"question": "请规划如何分析一场比赛"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["model_called"] is False
    assert body["data_retrieved"] is False
    assert body["real_conclusions_generated"] is False
    assert body["plan"]["steps"]


def test_deepseek_without_key_returns_503() -> None:
    with make_client(llm_mode="deepseek", deepseek_api_key=None) as client:
        status = client.get("/api/v1/llm/status")
        response = client.post(
            "/api/v1/analyses/plan",
            json={"question": "规划一次分析"},
        )

    assert status.json()["status"] == "unavailable"
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"
    assert response.json()["run_id"]


def test_input_limit_and_validation_use_uniform_errors() -> None:
    with make_client(llm_mode="mock", footops_input_max_chars=3) as client:
        too_long = client.post(
            "/api/v1/analyses/plan",
            json={"question": "1234"},
        )
        invalid = client.post(
            "/api/v1/analyses/plan",
            json={"question": "   "},
        )

    assert too_long.status_code == 413
    assert too_long.json()["status"] == "error"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"


def test_frontend_origin_is_allowed_by_cors() -> None:
    with make_client(llm_mode="mock") as client:
        response = client.options(
            "/api/v1/analyses/plan",
            headers={
                "Origin": "http://127.0.0.1:4173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:4173"
    )

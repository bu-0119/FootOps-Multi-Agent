"""Knowledge RAG retrieval, grounding, and API integration tests."""

from fastapi.testclient import TestClient
from test_data_pipeline import provider

from footops_agent.api.main import create_app
from footops_agent.config import Settings
from footops_agent.rag import (
    HybridKnowledgeRetriever,
    RedisVectorKnowledgeIndex,
)


def redis_retriever() -> HybridKnowledgeRetriever:
    return HybridKnowledgeRetriever(
        vector_index=RedisVectorKnowledgeIndex(Settings(_env_file=None)),
    )


def test_rule_retrieval_ranks_deliberate_play_first() -> None:
    evidence = redis_retriever().search(
        "越位规则中的主动触球怎么判断？",
        ("rule",),
    )

    assert evidence.status == "ready"
    assert evidence.corpus_version == "footops-knowledge-2026-08.v1"
    assert evidence.references[0].document_id == (
        "ifab-2026-27-law11-deliberate-play"
    )
    assert evidence.references[0].source_authority.endswith("(IFAB)")
    assert evidence.references[0].source_version == "Laws of the Game 2026/27"
    assert evidence.references[0].content_form == "paraphrase"


def test_tactical_retrieval_ranks_third_man_first() -> None:
    evidence = redis_retriever().search(
        "什么是三人出球？",
        ("tactics",),
    )

    assert evidence.status == "ready"
    assert evidence.references[0].document_id == "footops-tactics-third-man"


def test_metric_definition_retrieval_ranks_shot_involvement_first() -> None:
    evidence = redis_retriever().search(
        "射门参与是什么意思，和 xG 有什么区别？",
        ("metric_definition",),
    )

    assert evidence.status == "ready"
    assert evidence.references[0].document_id == (
        "footops-metric-shot-involvement-v1"
    )


def test_knowledge_corpus_does_not_store_match_facts() -> None:
    retriever = HybridKnowledgeRetriever()

    assert {document.domain for document in retriever.documents} == {
        "rule",
        "tactics",
        "metric_definition",
    }
    assert all(
        "pedri" not in document.search_text.casefold()
        for document in retriever.documents
    )
    assert all(
        "比赛事件" not in document.search_text for document in retriever.documents
    )


def test_redis_vector_index_persists_searchable_document_content() -> None:
    index = RedisVectorKnowledgeIndex(Settings(_env_file=None))
    try:
        documents = index.load_documents(HybridKnowledgeRetriever().documents)
        assert len(documents) >= 13
        deliberate_play = next(
            item
            for item in documents
            if item.document_id == "ifab-2026-27-law11-deliberate-play"
        )
        assert "主动处理球" in deliberate_play.summary
        assert deliberate_play.source_url.startswith("https://www.theifab.com/")
        assert index.client.hlen(index.documents_key) == len(documents)
    finally:
        index.close()


def test_rule_question_runs_knowledge_agent_without_match_data() -> None:
    app = create_app(settings=Settings(_env_file=None, llm_mode="mock"))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "越位规则中的主动触球怎么判断？"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["model_called"] is False
    assert body["data_retrieved"] is False
    assert body["workspace"] is None
    assert body["execution_plan"]["intent"] == "rule_qa"
    assert body["trace"][0]["tool_name"] == "search_knowledge"
    assert body["knowledge_answer"]["status"] == "answered"
    assert body["knowledge_evidence"]["references"][0]["document_id"] == (
        "ifab-2026-27-law11-deliberate-play"
    )
    valid_ids = {
        reference["evidence_id"]
        for reference in body["knowledge_evidence"]["references"]
    }
    assert set(body["knowledge_answer"]["citation_ids"]) <= valid_ids


def test_tactical_question_runs_knowledge_agent_with_tactical_corpus() -> None:
    app = create_app(settings=Settings(_env_file=None, llm_mode="mock"))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "什么是三人出球？"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["execution_plan"]["intent"] == "tactical_knowledge"
    assert body["knowledge_answer"]["status"] == "answered"
    assert body["knowledge_evidence"]["status"] == "ready"


def test_metric_question_runs_knowledge_agent_with_metric_corpus() -> None:
    app = create_app(settings=Settings(_env_file=None, llm_mode="mock"))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "射门参与是什么意思，和 xG 有什么区别？"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["model_called"] is False
    assert body["data_retrieved"] is False
    assert body["execution_plan"]["intent"] == "metric_knowledge"
    assert body["execution_plan"]["need_metric_rag"] is True
    assert body["trace"][0]["tool_name"] == "search_knowledge"
    assert body["knowledge_answer"]["status"] == "answered"
    assert body["knowledge_evidence"]["references"][0]["document_id"] == (
        "footops-metric-shot-involvement-v1"
    )


def test_hybrid_request_asks_for_scope_before_multi_agent_execution() -> None:
    app = create_app(settings=Settings(_env_file=None, llm_mode="mock"))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={"question": "分析佩德里最近五场为什么更靠近禁区"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "clarification_required"
    assert body["knowledge_evidence"] is None
    assert body["workspace"] is None


def test_hybrid_request_runs_board_with_explicit_scope() -> None:
    app = create_app(
        settings=Settings(_env_file=None, llm_mode="mock"),
        data_provider=provider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/runs",
            json={
                "question": "分析佩德里最近五场为什么更靠近禁区",
                "competition_id": 11,
                "season_id": 90,
                "player": "Pedri",
                "player_id": 30486,
                "requested_window": 5,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["workspace"]["status"] == "tactics_ready"
    assert "knowledge:" in body["message"]
    assert any(
        item["tool_name"].startswith("KnowledgeAgent:")
        for item in body["trace"]
    )

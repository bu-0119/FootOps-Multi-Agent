"""Entry intent routing tests."""

from footops_agent.artifacts import AgentAnalysisInput, AgentScopeHint
from footops_agent.services import RequestIntentRouter


def test_greeting_routes_to_chat_even_without_scope() -> None:
    route = RequestIntentRouter().route(AgentAnalysisInput(question="你好"))

    assert route.intent == "chat"
    assert route.confidence == 1


def test_analysis_language_routes_to_analysis() -> None:
    route = RequestIntentRouter().route(
        AgentAnalysisInput(question="分析佩德里最近三场的角色变化")
    )

    assert route.intent == "analysis"


def test_explicit_scope_routes_ambiguous_question_to_analysis() -> None:
    route = RequestIntentRouter().route(
        AgentAnalysisInput(
            question="看看他最近怎么样",
            scope_hint=AgentScopeHint(
                competition_id=11,
                season_id=90,
                player="Pedri",
                requested_window=3,
            ),
        )
    )

    assert route.intent == "analysis"


def test_rule_question_requires_rule_rag_without_match_data() -> None:
    plan = RequestIntentRouter().plan(
        AgentAnalysisInput(question="越位规则中的主动触球怎么判断？")
    )

    assert plan.intent == "rule_qa"
    assert plan.need_rule_rag is True
    assert plan.need_match_data is False
    assert plan.scope_required is False


def test_tactical_concept_question_requires_tactical_rag_only() -> None:
    plan = RequestIntentRouter().plan(
        AgentAnalysisInput(question="什么是三人出球？")
    )

    assert plan.intent == "tactical_knowledge"
    assert plan.need_tactical_rag is True
    assert plan.need_match_data is False


def test_metric_definition_question_requires_metric_rag_only() -> None:
    plan = RequestIntentRouter().plan(
        AgentAnalysisInput(question="射门参与是什么意思，和 xG 有什么区别？")
    )

    assert plan.intent == "metric_knowledge"
    assert plan.need_metric_rag is True
    assert plan.need_match_data is False


def test_causal_match_question_builds_hybrid_execution_plan() -> None:
    plan = RequestIntentRouter().plan(
        AgentAnalysisInput(question="分析佩德里最近五场为什么更靠近禁区")
    )

    assert plan.intent == "hybrid_tactical_analysis"
    assert plan.need_match_data is True
    assert plan.need_tactical_rag is True
    assert plan.need_multi_agent is True
    assert plan.scope_required is True

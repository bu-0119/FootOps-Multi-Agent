"""Fast entry routing before any analysis or multi-agent execution."""

from dataclasses import dataclass
from typing import Literal

from footops_agent.artifacts import AgentAnalysisInput, ExecutionPlanArtifact

type RequestIntent = Literal["chat", "analysis"]


@dataclass(frozen=True)
class IntentRoute:
    intent: RequestIntent
    confidence: float
    reason: str


class RequestIntentRouter:
    """Build a composable plan before selecting data, knowledge, or agents."""

    _greetings = {
        "你好",
        "您好",
        "嗨",
        "哈喽",
        "hello",
        "hi",
        "hey",
        "在吗",
        "谢谢",
        "感谢",
        "再见",
    }
    _analysis_terms = (
        "分析",
        "最近几场",
        "最近两场",
        "近两场",
        "最近2场",
        "近2场",
        "最近三场",
        "最近五场",
        "角色变化",
        "比赛数据",
        "触球",
        "接球",
        "传球",
        "推进带球",
        "关键传球",
        "射门参与",
        "战术板",
        "趋势",
        "近3场",
        "近5场",
        "analyze",
        "analysis",
    )
    _rule_terms = (
        "规则",
        "越位",
        "手球",
        "犯规",
        "红牌",
        "黄牌",
        "点球判罚",
        "var",
        "laws of the game",
        "offside",
        "handball",
    )
    _tactical_terms = (
        "半空间",
        "第三人",
        "三人出球",
        "压迫触发",
        "高位压迫",
        "低位防守",
        "阵型职责",
        "战术概念",
        "战术模板",
        "rest defence",
        "overload",
    )
    _knowledge_question_terms = (
        "什么是",
        "什么意思",
        "解释",
        "区别",
        "如何理解",
    )
    _metric_terms = (
        "指标",
        "口径",
        "定义",
        "怎么算",
        "射门参与",
        "触球代理",
        "touch_event_count",
        "shot involvement",
        "xg",
        "射正",
        "向前传球次数",
        "推进带球次数",
    )
    _hybrid_terms = (
        "为什么",
        "原因",
        "是否更像",
        "是不是更像",
        "战术职责",
        "角色原因",
        "参考案例",
        "对照案例",
    )
    _match_analysis_markers = (
        "分析",
        "比赛数据",
        "最近",
        "近3场",
        "近5场",
        "趋势",
        "多场",
        "本场",
    )

    def route(self, request: AgentAnalysisInput) -> IntentRoute:
        plan = self.plan(request)
        if plan.intent == "chat":
            return IntentRoute("chat", plan.confidence, plan.reason)
        return IntentRoute("analysis", plan.confidence, plan.reason)

    def plan(self, request: AgentAnalysisInput) -> ExecutionPlanArtifact:
        """Classify independent resource needs instead of one exclusive path."""
        normalized = request.question.strip().casefold().rstrip("!！?？。,. ")
        if normalized in self._greetings:
            return ExecutionPlanArtifact(
                intent="chat",
                confidence=1.0,
                reason="matched ordinary greeting",
            )

        mentions_rule = any(term in normalized for term in self._rule_terms)
        mentions_tactics = any(term in normalized for term in self._tactical_terms)
        asks_for_knowledge = any(
            term in normalized for term in self._knowledge_question_terms
        )
        asks_for_analysis = any(term in normalized for term in self._analysis_terms)
        asks_for_hybrid = any(term in normalized for term in self._hybrid_terms)
        asks_for_metric_knowledge = any(
            term in normalized for term in self._metric_terms
        )
        has_match_analysis_context = any(
            term in normalized for term in self._match_analysis_markers
        )

        if mentions_rule and not has_match_analysis_context:
            return ExecutionPlanArtifact(
                intent="rule_qa",
                need_rule_rag=True,
                confidence=0.95,
                reason="matched football rule knowledge request",
            )
        if mentions_tactics and asks_for_knowledge and not has_match_analysis_context:
            return ExecutionPlanArtifact(
                intent="tactical_knowledge",
                need_tactical_rag=True,
                confidence=0.93,
                reason="matched tactical concept knowledge request",
            )
        if (
            asks_for_metric_knowledge
            and asks_for_knowledge
            and not has_match_analysis_context
        ):
            return ExecutionPlanArtifact(
                intent="metric_knowledge",
                need_metric_rag=True,
                confidence=0.93,
                reason="matched FootOps metric definition knowledge request",
            )
        if asks_for_analysis and (asks_for_hybrid or mentions_tactics or mentions_rule):
            return ExecutionPlanArtifact(
                intent="hybrid_tactical_analysis",
                need_match_data=True,
                need_rule_rag=mentions_rule,
                need_tactical_rag=mentions_tactics or asks_for_hybrid,
                need_metric_rag=asks_for_metric_knowledge,
                need_multi_agent=True,
                scope_required=True,
                confidence=0.92,
                reason="analysis requires match evidence and tactical knowledge",
            )
        if asks_for_analysis:
            return ExecutionPlanArtifact(
                intent="data_analysis",
                need_match_data=True,
                scope_required=True,
                confidence=0.95,
                reason="matched executable match-data analysis",
            )
        if request.scope_hint.model_dump(exclude_none=True):
            return ExecutionPlanArtifact(
                intent="data_analysis",
                need_match_data=True,
                scope_required=True,
                confidence=0.9,
                reason="explicit analysis scope was supplied",
            )
        return ExecutionPlanArtifact(
            intent="chat",
            confidence=0.7,
            reason="no executable data or knowledge intent was detected",
        )

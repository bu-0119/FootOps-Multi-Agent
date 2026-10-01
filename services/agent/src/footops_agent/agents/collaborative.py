"""FootOps worker agents for event-driven analysis collaboration."""

from uuid import uuid4

from footops_agent.artifacts import (
    EvidenceSetArtifact,
    FindingSetArtifact,
    TacticalHypothesisArtifact,
)
from footops_agent.collaboration import (
    AgentCapability,
    AgentProfile,
    ClaimDecision,
    CollaborationArtifact,
    CollaborationBoard,
    CollaborationTask,
    CollaborationTurnResult,
    DataBundle,
    FindingBundle,
    KnowledgeBundle,
    ReviewBundle,
    TacticsBundle,
)
from footops_agent.providers import FootballDataProvider
from footops_agent.rag import HybridKnowledgeRetriever
from footops_agent.services import PlayerRoleAnalysisService
from footops_agent.services.evidence_gate import EvidenceGate
from footops_agent.services.finding_builder import DeterministicFindingBuilder
from footops_agent.services.question_scope import PlayerRoleQuestionRouter
from footops_agent.services.tactics_board import DeterministicTacticsBoardBuilder


def _artifact(
    owner: str,
    kind: str,
    payload: object,
    task: CollaborationTask,
    revision_round: int = 0,
) -> CollaborationArtifact:
    return CollaborationArtifact(
        artifact_id=f"{owner}:{kind}:{uuid4().hex[:10]}",
        owner=owner,
        kind=kind,
        payload=payload,
        task_id=task.task_id,
        revision_round=revision_round,
    )


class DataAgent:
    """Own provider access and deterministic metric calculation."""

    profile = AgentProfile(
        name="DataAgent",
        capabilities=frozenset({AgentCapability.DATA}),
        tool_permissions=frozenset({"provider.read", "metrics.calculate"}),
    )

    def __init__(self, provider: FootballDataProvider) -> None:
        self.analysis = PlayerRoleAnalysisService(provider)

    def decide(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> ClaimDecision:
        if board.latest_artifact("data_bundle") is not None:
            return ClaimDecision(False, reason="data artifact already exists")
        return ClaimDecision(
            task.metadata.get("kind") == "data",
            0.95,
            "player-role metrics require provider and metric permissions",
        )

    def act(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> CollaborationTurnResult:
        request = board.request
        audit, metrics = self.analysis.calculate(
            request.competition_id,
            request.season_id,
            request.player_query,
            request.requested_window,
            request.player_id,
        )
        return CollaborationTurnResult(
            artifacts=(
                _artifact(
                    self.profile.name,
                    "data_bundle",
                    DataBundle(audit=audit, metrics=metrics),
                    task,
                ),
            )
        )


class TacticalAgent:
    """Turn metrics into candidate findings and an approved tactics board."""

    profile = AgentProfile(
        name="TacticalAgent",
        capabilities=frozenset({AgentCapability.TACTICAL}),
        tool_permissions=frozenset({"findings.build", "tactics.build"}),
    )

    def __init__(self) -> None:
        self.router = PlayerRoleQuestionRouter()
        self.finding_builder = DeterministicFindingBuilder()
        self.tactics_builder = DeterministicTacticsBoardBuilder()

    def decide(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> ClaimDecision:
        kind = task.metadata.get("kind")
        if kind == "findings":
            ready = board.latest_artifact("data_bundle") is not None
            missing = board.latest_artifact("finding_bundle") is None
            return ClaimDecision(
                ready and missing,
                0.9,
                "metrics are ready for tactical finding generation",
            )
        if kind == "tactics":
            review = board.latest_artifact("review_bundle")
            ready = (
                review is not None
                and review.payload.review.overall_status == "passed"
            )
            return ClaimDecision(
                ready and board.latest_artifact("tactics_bundle") is None,
                0.88,
                "evidence-approved findings can be projected to the tactics board",
            )
        if kind == "revision":
            review = board.latest_artifact("review_bundle")
            return ClaimDecision(
                review is not None
                and review.payload.review.overall_status != "passed",
                0.91,
                "critique identifies unsupported findings that require revision",
            )
        return ClaimDecision(False, reason="task is outside tactical permissions")

    def act(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> CollaborationTurnResult:
        data = board.latest_artifact("data_bundle")
        if data is None:
            raise RuntimeError("TacticalAgent requires data_bundle")
        if task.metadata.get("kind") == "findings":
            selection = self.router.select(
                board.request.question,
                board.request.player_query,
            )

        if task.metadata.get("kind") == "revision":
            findings = board.latest_artifact("finding_bundle")
            review = board.latest_artifact("review_bundle")
            if findings is None or review is None:
                raise RuntimeError("TacticalAgent requires findings and critique")
            supported_ids = {
                item.finding_id
                for item in review.payload.review.reviews
                if item.status == "supported"
            }
            revised_findings = [
                item
                for item in findings.payload.findings.findings
                if item.finding_id in supported_ids
            ]
            if not revised_findings:
                raise RuntimeError("critique left no supported findings to revise")
            revised = FindingBundle(
                findings=FindingSetArtifact(
                    generated_at=findings.payload.findings.generated_at,
                    findings=revised_findings,
                ),
                evidence=findings.payload.evidence,
            )
            return CollaborationTurnResult(
                artifacts=(
                    _artifact(
                        self.profile.name,
                        "finding_bundle",
                        revised,
                        task,
                        revision_round=task.metadata.get("revision_round", 1),
                    ),
                )
            )
        if task.metadata.get("kind") == "findings":
            finding_set, evidence = self.finding_builder.build(data.payload.metrics)
            selected = _select_findings(
                finding_set,
                evidence,
                set(selection.finding_ids),
            )
            return CollaborationTurnResult(
                artifacts=(
                    _artifact(
                        self.profile.name,
                        "finding_bundle",
                        selected,
                        task,
                    ),
                )
            )

        findings = board.latest_artifact("finding_bundle")
        review = board.latest_artifact("review_bundle")
        if findings is None or review is None:
            raise RuntimeError("TacticalAgent requires findings and evidence review")
        tactics_board = self.tactics_builder.build(
            data.payload.metrics,
            findings.payload.findings.findings,
            review.payload.review,
        )
        return CollaborationTurnResult(
            artifacts=(
                _artifact(
                    self.profile.name,
                    "tactics_bundle",
                    TacticsBundle(tactics_board=tactics_board),
                    task,
                    revision_round=findings.revision_round,
                ),
            )
        )


class EvidenceAgent:
    """Independently review candidate findings against metric evidence."""

    profile = AgentProfile(
        name="EvidenceAgent",
        capabilities=frozenset({AgentCapability.EVIDENCE}),
        tool_permissions=frozenset({"evidence.review"}),
    )

    def __init__(self) -> None:
        self.gate = EvidenceGate()

    def decide(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> ClaimDecision:
        ready = (
            board.latest_artifact("data_bundle") is not None
            and board.latest_artifact("finding_bundle") is not None
        )
        findings = board.latest_artifact("finding_bundle")
        review = board.latest_artifact("review_bundle")
        expected_round = task.metadata.get("revision_round", 0)
        missing = (
            findings is not None
            and findings.revision_round == expected_round
            and (review is None or review.revision_round < expected_round)
        )
        return ClaimDecision(
            task.metadata.get("kind") == "evidence_review" and ready and missing,
            0.97,
            "candidate findings require independent deterministic review",
        )

    def act(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> CollaborationTurnResult:
        data = board.latest_artifact("data_bundle")
        findings = board.latest_artifact("finding_bundle")
        if data is None or findings is None:
            raise RuntimeError("EvidenceAgent requires data and finding bundles")
        review = self.gate.review(
            findings.payload.findings,
            findings.payload.evidence,
            data.payload.metrics,
        )
        return CollaborationTurnResult(
            artifacts=(
                _artifact(
                    self.profile.name,
                    "review_bundle",
                    ReviewBundle(review=review),
                    task,
                    revision_round=findings.revision_round,
                ),
            )
        )


class KnowledgeAgent:
    """Ground hybrid findings in the versioned tactical knowledge corpus."""

    profile = AgentProfile(
        name="KnowledgeAgent",
        capabilities=frozenset({AgentCapability.KNOWLEDGE}),
        tool_permissions=frozenset({"knowledge.search", "hypothesis.ground"}),
    )

    def __init__(
        self,
        retriever: HybridKnowledgeRetriever | None = None,
    ) -> None:
        self.retriever = retriever or HybridKnowledgeRetriever()

    def decide(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> ClaimDecision:
        ready = (
            board.latest_artifact("data_bundle") is not None
            and board.latest_artifact("finding_bundle") is not None
            and board.latest_artifact("review_bundle") is not None
        )
        return ClaimDecision(
            task.metadata.get("kind") == "knowledge"
            and board.request.requires_knowledge
            and ready
            and board.latest_artifact("knowledge_bundle") is None,
            0.93,
            "approved match findings require versioned tactical knowledge grounding",
        )

    def act(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> CollaborationTurnResult:
        findings = board.latest_artifact("finding_bundle")
        if findings is None:
            raise RuntimeError("KnowledgeAgent requires finding_bundle")
        evidence = self.retriever.search(board.request.question, ("tactics",))
        if evidence.status != "ready":
            hypothesis = TacticalHypothesisArtifact(
                status="insufficient",
                hypothesis="当前战术知识证据不足，不能把比赛数据解释为战术原因。",
                limitations=["需要补充版本化战术概念或授权案例。"],
            )
        else:
            selected_findings = findings.payload.findings.findings
            metric_refs = list(
                dict.fromkeys(
                    ref
                    for finding in selected_findings
                    for ref in finding.metric_refs
                )
            )[:12]
            fact_refs = [finding.finding_id for finding in selected_findings]
            knowledge_refs = [
                reference.evidence_id for reference in evidence.references
            ]
            observation_text = "\n".join(
                f"{index}. {finding.statement}"
                for index, finding in enumerate(selected_findings[:6], start=1)
            )
            knowledge_text = "\n".join(
                f"- {reference.title}：{reference.summary} [{reference.evidence_id}]"
                for reference in evidence.references[:2]
            )
            hypothesis = TacticalHypothesisArtifact(
                status="grounded",
                hypothesis=(
                    f"比赛数据报告\n数据观察：\n{observation_text}\n\n"
                    f"战术参照：\n{knowledge_text}\n\n"
                    "解读边界：以上数值是所选比赛的事件数据对比。战术概念只提供"
                    "后续看录像时的观察角度，不能单凭触球位置证明球员职责或战术原因。"
                ),
                fact_refs=fact_refs,
                metric_refs=metric_refs,
                knowledge_refs=knowledge_refs,
                limitations=["当前为证据关联假设，不替代完整视频复盘。"],
            )
        return CollaborationTurnResult(
            artifacts=(
                _artifact(
                    self.profile.name,
                    "knowledge_bundle",
                    KnowledgeBundle(evidence=evidence, hypothesis=hypothesis),
                    task,
                ),
            )
        )


class CoordinatorAgent:
    """Own task creation, budgets and the final acceptance policy."""

    name = "CoordinatorAgent"


def _select_findings(
    finding_set: FindingSetArtifact,
    evidence: EvidenceSetArtifact,
    selected_ids: set[str],
) -> FindingBundle:
    findings = [
        finding
        for finding in finding_set.findings
        if finding.finding_id in selected_ids
    ]
    if not findings:
        raise ValueError("selected findings are missing from generated artifacts")
    reference_ids = {
        reference
        for finding in findings
        for reference in (*finding.metric_refs, *finding.source_refs)
    }
    references = [
        reference
        for reference in evidence.references
        if reference.evidence_id in reference_ids
    ]
    return FindingBundle(
        findings=FindingSetArtifact(
            generated_at=finding_set.generated_at,
            findings=findings,
        ),
        evidence=EvidenceSetArtifact(
            generated_at=evidence.generated_at,
            references=references,
        ),
    )

"""AgentScope tool boundary for versioned football knowledge retrieval."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from agentscope.tool import FunctionTool

from footops_agent.artifacts import AgentToolTrace, KnowledgeEvidenceArtifact
from footops_agent.rag import HybridKnowledgeRetriever, KnowledgeDomain


@dataclass
class KnowledgeToolContext:
    """Per-run evidence kept outside model-authored structured output."""

    traces: list[AgentToolTrace] = field(default_factory=list)
    evidence: KnowledgeEvidenceArtifact | None = None
    on_trace: Callable[[AgentToolTrace], None] | None = None

    def record(self, status: str, summary: str) -> None:
        trace = AgentToolTrace(
            sequence=len(self.traces) + 1,
            tool_name="search_knowledge",
            status=status,  # type: ignore[arg-type]
            summary=summary,
        )
        self.traces.append(trace)
        if self.on_trace is not None:
            self.on_trace(trace)


def build_knowledge_tools(
    retriever: HybridKnowledgeRetriever,
    allowed_domains: tuple[KnowledgeDomain, ...],
    context: KnowledgeToolContext,
) -> list[FunctionTool]:
    """Build a read-only search tool with Harness-controlled domain filters."""

    async def search_knowledge(query: str, top_k: int = 4) -> dict:
        """Search versioned football knowledge and return citable evidence."""
        evidence = await asyncio.to_thread(
            retriever.search,
            query,
            allowed_domains,
            top_k,
        )
        context.evidence = evidence
        context.record(
            "completed" if evidence.status == "ready" else "insufficient",
            (
                f"知识检索返回 {len(evidence.references)} 条版本化证据。"
                if evidence.status == "ready"
                else "当前知识域没有达到检索阈值的证据。"
            ),
        )
        return {
            "status": evidence.status,
            "corpus_version": evidence.corpus_version,
            "retrieval_method": evidence.retrieval_method,
            "references": [
                reference.model_dump(mode="json")
                for reference in evidence.references
            ],
            "instruction": (
                "只能依据 references 回答，并在每个关键结论后标注 evidence_id。"
                if evidence.status == "ready"
                else "停止回答并返回 insufficient，不能使用模型记忆补齐。"
            ),
        }

    return [FunctionTool(search_knowledge, is_read_only=True)]

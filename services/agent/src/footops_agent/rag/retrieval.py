"""Deterministic hybrid retrieval for versioned FootOps knowledge."""

import logging
import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence

from redis.exceptions import RedisError

from footops_agent.artifacts import (
    KnowledgeEvidenceArtifact,
    KnowledgeEvidenceReference,
)

from .corpus import (
    FOOTOPS_KNOWLEDGE_CORPUS_VERSION,
    FOOTOPS_KNOWLEDGE_DOCUMENTS,
    KnowledgeDocument,
    KnowledgeDomain,
)
from .redis_vector import RedisVectorKnowledgeIndex

logger = logging.getLogger(__name__)

_LATIN_OR_NUMBER = re.compile(r"[a-z0-9]+")
_CJK_SEQUENCE = re.compile(r"[\u3400-\u9fff]+")


def _tokens(value: str) -> list[str]:
    normalized = value.casefold()
    tokens = _LATIN_OR_NUMBER.findall(normalized)
    for sequence in _CJK_SEQUENCE.findall(normalized):
        tokens.extend(sequence)
        tokens.extend(
            sequence[index : index + 2] for index in range(len(sequence) - 1)
        )
    return tokens


class HybridKnowledgeRetriever:
    """BM25 plus character-vector retrieval with deterministic reranking."""

    def __init__(
        self,
        documents: Sequence[KnowledgeDocument] = FOOTOPS_KNOWLEDGE_DOCUMENTS,
        corpus_version: str = FOOTOPS_KNOWLEDGE_CORPUS_VERSION,
        vector_index: RedisVectorKnowledgeIndex | None = None,
    ) -> None:
        self.documents = tuple(documents)
        self.corpus_version = corpus_version
        self.vector_index = vector_index

    def search(
        self,
        query: str,
        domains: Iterable[KnowledgeDomain],
        top_k: int = 4,
    ) -> KnowledgeEvidenceArtifact:
        requested_domains = list(dict.fromkeys(domains))
        if self.vector_index is None:
            logger.error("Knowledge retrieval requested without Redis Vector Sets")
            return self._insufficient(query, requested_domains)
        try:
            indexed_documents = self.vector_index.load_documents(self.documents)
            vector_scores = self.vector_index.search(
                query,
                indexed_documents,
                len(indexed_documents),
            )
        except (RedisError, ValueError) as exc:
            logger.exception(
                "Redis knowledge retrieval failed with %s",
                type(exc).__name__,
            )
            return self._insufficient(query, requested_domains)

        candidates = [
            document
            for document in indexed_documents
            if document.domain in requested_domains
        ]
        if not query.strip() or not candidates:
            return self._insufficient(query, requested_domains)

        query_tokens = _tokens(query)
        document_tokens = [_tokens(self._retrieval_text(item)) for item in candidates]
        bm25_scores = self._bm25(query_tokens, document_tokens)
        max_bm25 = max(bm25_scores, default=0.0)
        ranked: list[tuple[float, float, float, KnowledgeDocument]] = []
        normalized_query = query.casefold()
        for document, bm25 in zip(
            candidates,
            bm25_scores,
            strict=True,
        ):
            normalized_bm25 = bm25 / max_bm25 if max_bm25 > 0 else 0.0
            keyword_hits = sum(
                1
                for keyword in document.keywords
                if keyword.casefold() in normalized_query
            )
            phrase_boost = min(0.24, keyword_hits * 0.08)
            vector = vector_scores.get(document.document_id, 0.0)
            rerank = (
                0.45 * normalized_bm25
                + 0.55 * vector
                + phrase_boost
            )
            ranked.append((rerank, bm25, vector, document))

        ranked.sort(key=lambda item: (item[0], item[3].document_id), reverse=True)
        selected = [
            item
            for item in ranked[: max(1, min(top_k, 8))]
            if item[0] >= 0.12
        ]
        if not selected:
            return self._insufficient(query, requested_domains)

        references = [
            KnowledgeEvidenceReference(
                evidence_id=f"knowledge:{index}",
                document_id=document.document_id,
                domain=document.domain,
                title=document.title,
                section=document.section,
                summary=document.summary,
                source_url=document.source_url,
                source_authority=document.source_authority,
                source_version=document.source_version,
                effective_from=document.effective_from,
                language=document.language,
                bm25_score=round(bm25, 6),
                vector_score=round(vector, 6),
                rerank_score=round(rerank, 6),
            )
            for index, (rerank, bm25, vector, document) in enumerate(
                selected,
                start=1,
            )
        ]
        return KnowledgeEvidenceArtifact(
            query=query,
            requested_domains=requested_domains,
            corpus_version=self.corpus_version,
            retrieval_method="redis_char_vector_bm25_hybrid_v1",
            status="ready",
            references=references,
        )

    @staticmethod
    def _retrieval_text(document: KnowledgeDocument) -> str:
        return " ".join(
            (
                document.title,
                document.section,
                document.search_text,
                document.summary,
                *document.keywords,
            )
        )

    @staticmethod
    def _bm25(query: list[str], documents: list[list[str]]) -> list[float]:
        if not query or not documents:
            return [0.0 for _ in documents]
        document_frequency = Counter(
            token for document in documents for token in set(document)
        )
        average_length = sum(map(len, documents)) / len(documents)
        scores: list[float] = []
        k1 = 1.5
        b = 0.75
        for document in documents:
            frequencies = Counter(document)
            score = 0.0
            for token in set(query):
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                count = document_frequency[token]
                inverse_frequency = math.log(
                    1 + (len(documents) - count + 0.5) / (count + 0.5)
                )
                denominator = frequency + k1 * (
                    1 - b + b * len(document) / max(1, average_length)
                )
                score += inverse_frequency * frequency * (k1 + 1) / denominator
            scores.append(score)
        return scores

    def _insufficient(
        self,
        query: str,
        domains: list[KnowledgeDomain],
    ) -> KnowledgeEvidenceArtifact:
        return KnowledgeEvidenceArtifact(
            query=query or "empty query",
            requested_domains=domains or ["rule"],
            corpus_version=self.corpus_version,
            retrieval_method="redis_char_vector_bm25_hybrid_v1",
            status="insufficient",
        )

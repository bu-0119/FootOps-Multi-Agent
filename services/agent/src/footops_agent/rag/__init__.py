"""Versioned football-knowledge corpus and deterministic retrieval."""

from .corpus import (
    FOOTOPS_KNOWLEDGE_CORPUS_VERSION,
    IFAB_CORPUS_VERSION,
    KnowledgeDocument,
    KnowledgeDomain,
)
from .redis_vector import RedisVectorKnowledgeIndex
from .retrieval import HybridKnowledgeRetriever

__all__ = [
    "HybridKnowledgeRetriever",
    "RedisVectorKnowledgeIndex",
    "FOOTOPS_KNOWLEDGE_CORPUS_VERSION",
    "IFAB_CORPUS_VERSION",
    "KnowledgeDocument",
    "KnowledgeDomain",
]

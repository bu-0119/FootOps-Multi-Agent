"""Redis 8 Vector Sets backed by deterministic character feature vectors."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date

from redis import Redis

from footops_agent.config import Settings

from .corpus import KnowledgeDocument

VECTOR_DIMENSIONS = 512
VECTOR_ALGORITHM_VERSION = "char-ngram-hash-redis-docs-v2"


def _vectorize(text: str) -> list[float]:
    normalized = re.sub(r"[^a-z0-9\u3400-\u9fff]", "", text.casefold())
    vector = [0.0] * VECTOR_DIMENSIONS
    for size in (2, 3):
        for index in range(max(0, len(normalized) - size + 1)):
            feature = normalized[index : index + size].encode("utf-8")
            digest = hashlib.blake2s(feature, digest_size=8).digest()
            slot = int.from_bytes(digest[:4], "little") % VECTOR_DIMENSIONS
            vector[slot] += 1.0 if digest[4] & 1 else -1.0
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


class RedisVectorKnowledgeIndex:
    """Lazily synchronize the curated corpus and query Redis Vector Sets."""

    def __init__(self, settings: Settings) -> None:
        self.client = Redis.from_url(settings.footops_redis_url, decode_responses=True)
        self.index_key = "footops:knowledge:vectors:char-ngram-v2"
        self.manifest_key = f"{self.index_key}:manifest"
        self.documents_key = "footops:knowledge:documents:v1"

    @staticmethod
    def _document_text(document: KnowledgeDocument) -> str:
        return "\n".join(
            (
                document.title,
                document.section,
                document.summary,
                document.search_text,
                " ".join(document.keywords),
            )
        )

    def _synchronize(self, documents: Sequence[KnowledgeDocument]) -> None:
        serialized = [
            {
                **asdict(document),
                "effective_from": document.effective_from.isoformat()
                if document.effective_from
                else None,
            }
            for document in documents
        ]
        fingerprint = hashlib.sha256(
            json.dumps(
                [VECTOR_ALGORITHM_VERSION, serialized],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if (
            self.client.get(self.manifest_key) == fingerprint
            and self.client.hlen(self.documents_key) == len(documents)
        ):
            return

        self.client.delete(self.manifest_key, self.index_key, self.documents_key)
        for document, payload in zip(documents, serialized, strict=True):
            vector = _vectorize(self._document_text(document))
            self.client.execute_command(
                "VADD",
                self.index_key,
                "VALUES",
                len(vector),
                *(format(value, ".9g") for value in vector),
                document.document_id,
                "NOQUANT",
            )
            self.client.hset(
                self.documents_key,
                document.document_id,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )
        self.client.set(self.manifest_key, fingerprint)

    def load_documents(
        self,
        seed_documents: Sequence[KnowledgeDocument],
    ) -> tuple[KnowledgeDocument, ...]:
        """Sync the curated source once, then read indexed passages from Redis."""
        self._synchronize(seed_documents)
        stored = self.client.hgetall(self.documents_key)
        documents: list[KnowledgeDocument] = []
        for payload in stored.values():
            value = json.loads(payload)
            value["effective_from"] = (
                date.fromisoformat(value["effective_from"])
                if value.get("effective_from")
                else None
            )
            value["keywords"] = tuple(value["keywords"])
            documents.append(KnowledgeDocument(**value))
        return tuple(documents)

    def search(
        self,
        query: str,
        documents: Sequence[KnowledgeDocument],
        top_k: int,
    ) -> dict[str, float]:
        if not documents:
            return {}
        self._synchronize(documents)
        query_vector = _vectorize(query)
        values = self.client.execute_command(
            "VSIM",
            self.index_key,
            "VALUES",
            len(query_vector),
            *(format(value, ".9g") for value in query_vector),
            "WITHSCORES",
            "COUNT",
            min(len(documents), max(top_k * 3, top_k)),
        )
        if isinstance(values, Mapping):
            return {str(element): float(score) for element, score in values.items()}
        return {
            str(values[index]): float(values[index + 1])
            for index in range(0, len(values), 2)
        }

    def close(self) -> None:
        self.client.close()

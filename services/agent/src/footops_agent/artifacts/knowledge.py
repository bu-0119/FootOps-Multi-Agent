"""Versioned knowledge evidence and grounded-answer contracts."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import StrictModel, utc_now


class KnowledgeEvidenceReference(StrictModel):
    """One retrievable, versioned knowledge passage with source provenance."""

    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    domain: Literal["rule", "tactics", "case", "metric_definition"]
    title: str = Field(min_length=1)
    section: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_authority: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    effective_from: date | None = None
    language: str = Field(min_length=2)
    content_form: Literal["paraphrase", "quotation"] = "paraphrase"
    bm25_score: float = Field(ge=0)
    vector_score: float = Field(ge=0, le=1)
    rerank_score: float = Field(ge=0)


class KnowledgeEvidenceArtifact(StrictModel):
    """Auditable output from one bounded knowledge retrieval request."""

    schema_version: Literal["1.0"] = "1.0"
    query: str = Field(min_length=1)
    requested_domains: list[
        Literal["rule", "tactics", "case", "metric_definition"]
    ] = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    retrieval_method: Literal["redis_char_vector_bm25_hybrid_v1"] = (
        "redis_char_vector_bm25_hybrid_v1"
    )
    status: Literal["ready", "insufficient"]
    references: list[KnowledgeEvidenceReference] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_status(self) -> "KnowledgeEvidenceArtifact":
        if self.status == "ready" and not self.references:
            raise ValueError("ready knowledge evidence requires references")
        if self.status == "insufficient" and self.references:
            raise ValueError("insufficient knowledge evidence cannot expose references")
        return self


class KnowledgeAnswerArtifact(StrictModel):
    """KnowledgeAgent answer whose citations must resolve to retrieved evidence."""

    schema_version: Literal["1.0"] = "1.0"
    status: Literal["answered", "insufficient"]
    answer: str = Field(min_length=1, max_length=5000)
    citation_ids: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_citations(self) -> "KnowledgeAnswerArtifact":
        if self.status == "answered" and not self.citation_ids:
            raise ValueError("answered knowledge output requires citations")
        if self.status == "insufficient" and self.citation_ids:
            raise ValueError("insufficient knowledge output cannot cite evidence")
        return self

"""Shared primitives for versioned FootOps artifacts."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return one timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class StrictModel(BaseModel):
    """Reject undeclared fields in internal and external contracts."""

    model_config = ConfigDict(extra="forbid")


class SourceReference(StrictModel):
    """Trace one artifact back to the dataset resource that produced it."""

    provider: str
    dataset: str
    source_url: str
    retrieved_at: datetime = Field(default_factory=utc_now)
    attribution: str
    license_url: str

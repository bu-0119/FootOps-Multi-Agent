"""Versioned schemas for analysis planning."""

from pydantic import Field

from .base import StrictModel


class QuestionUnderstanding(StrictModel):
    """A structured interpretation of the user's analysis request."""

    intent: str = Field(description="The analysis goal, without answering it.")
    subjects: list[str] = Field(
        default_factory=list,
        description="Teams, players, matches, or concepts named by the user.",
    )
    requested_comparisons: list[str] = Field(default_factory=list)
    requested_evidence: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class AnalysisPlanStep(StrictModel):
    """One non-executed step in a future evidence-based analysis."""

    title: str
    purpose: str
    required_data: list[str] = Field(default_factory=list)
    output: str


class AnalysisPlan(StrictModel):
    """Structured question understanding and analysis plan."""

    understanding: QuestionUnderstanding
    steps: list[AnalysisPlanStep] = Field(min_length=1, max_length=8)
    clarifying_questions: list[str] = Field(default_factory=list, max_length=5)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, min_length=1, max_length=8)

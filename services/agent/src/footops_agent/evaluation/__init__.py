"""Golden-task evaluation for FootOps orchestration modes."""

from .models import (
    EvaluationCaseResult,
    EvaluationMode,
    EvaluationObservation,
    EvaluationReport,
    EvaluationSummary,
    GoldenTask,
    GoldenTaskExpectation,
    GoldenTaskSuite,
)
from .service import EvaluationService

__all__ = [
    "EvaluationCaseResult",
    "EvaluationMode",
    "EvaluationObservation",
    "EvaluationReport",
    "EvaluationService",
    "EvaluationSummary",
    "GoldenTask",
    "GoldenTaskExpectation",
    "GoldenTaskSuite",
]

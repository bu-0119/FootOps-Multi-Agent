"""Question-understanding and analysis-planning agent boundary."""

from footops_agent.artifacts import AnalysisPlan
from footops_agent.runtime.model_adapter import ModelAdapter


class AnalysisPlanner:
    """Coordinates structured planning through a provider adapter."""

    def __init__(self, adapter: ModelAdapter) -> None:
        self.adapter = adapter

    async def plan(self, question: str) -> AnalysisPlan:
        """Understand a question and return a non-executed analysis plan."""
        return await self.adapter.create_plan(question)

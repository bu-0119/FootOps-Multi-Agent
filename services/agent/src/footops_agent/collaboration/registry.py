"""Capability registry used by agents to claim collaboration tasks."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from .events import CollaborationBoard, CollaborationTask, CollaborationTurnResult


class AgentCapability(StrEnum):
    DATA = "DATA"
    TACTICAL = "TACTICAL"
    EVIDENCE = "EVIDENCE"
    KNOWLEDGE = "KNOWLEDGE"


@dataclass(frozen=True)
class AgentProfile:
    name: str
    capabilities: frozenset[AgentCapability]
    tool_permissions: frozenset[str]


@dataclass(frozen=True)
class ClaimDecision:
    claim: bool
    confidence: float = 0.0
    reason: str = ""


class CollaborativeAgent(Protocol):
    profile: AgentProfile

    def decide(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> ClaimDecision: ...

    def act(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> CollaborationTurnResult: ...


@dataclass(frozen=True)
class AgentCandidate:
    agent: CollaborativeAgent
    decision: ClaimDecision


class AgentRegistry:
    def __init__(self, agents: list[CollaborativeAgent]) -> None:
        self._agents = list(agents)

    @property
    def agent_names(self) -> list[str]:
        return [agent.profile.name for agent in self._agents]

    def candidates_for(
        self,
        task: CollaborationTask,
        board: CollaborationBoard,
    ) -> list[AgentCandidate]:
        candidates: list[AgentCandidate] = []
        for agent in self._agents:
            capabilities = {item.value for item in agent.profile.capabilities}
            if task.capability not in capabilities:
                continue
            decision = agent.decide(task, board)
            if decision.claim:
                candidates.append(AgentCandidate(agent, decision))
        return sorted(
            candidates,
            key=lambda item: (item.decision.confidence, item.agent.profile.name),
            reverse=True,
        )

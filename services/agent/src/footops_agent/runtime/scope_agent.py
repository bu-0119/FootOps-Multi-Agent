"""Dedicated AgentScope runtime for catalog-grounded analysis scope resolution."""

import json
from dataclasses import dataclass
from typing import Protocol

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.model import DeepSeekChatModel
from agentscope.state import AgentState
from agentscope.tool import Toolkit

from footops_agent.artifacts import (
    AgentAnalysisInput,
    AgentModelUsage,
    AgentToolTrace,
    ResolvedAgentScope,
    ScopeResolutionArtifact,
)
from footops_agent.config import Settings
from footops_agent.prompts import SCOPE_AGENT_SYSTEM_PROMPT
from footops_agent.services import DataCatalogService
from footops_agent.tools import AgentToolContext, build_scope_tools

from .usage import collect_agent_model_usage


@dataclass(frozen=True)
class ScopeAgentResult:
    """Trusted ScopeAgent output consumed before collaboration starts."""

    artifact: ScopeResolutionArtifact
    trace: list[AgentToolTrace]
    usage: AgentModelUsage | None = None


class ScopeAgentRuntime(Protocol):
    mode: str
    provider: str
    model_name: str
    model_called: bool

    async def run(self, request: AgentAnalysisInput) -> ScopeAgentResult:
        """Resolve one request without executing football analysis."""


class MockScopeAgentRuntime:
    """Credential-free runtime that only accepts a complete explicit scope."""

    mode = "mock"
    provider = "none"
    model_name = "mock"
    model_called = False

    async def run(self, request: AgentAnalysisInput) -> ScopeAgentResult:
        hint = request.scope_hint
        if (
            hint.competition_id is None
            or hint.season_id is None
            or hint.player is None
            or hint.player_id is None
        ):
            artifact = ScopeResolutionArtifact(
                status="clarification_required",
                message="请补充赛事、赛季和球员，mock ScopeAgent 不推断缺失范围。",
            )
            return ScopeAgentResult(artifact=artifact, trace=[])
        artifact = ScopeResolutionArtifact(
            status="resolved",
            message="已使用显式约束确认分析范围。",
            scope=ResolvedAgentScope(
                competition_id=hint.competition_id,
                season_id=hint.season_id,
                player=hint.player,
                player_id=hint.player_id,
                requested_window=hint.requested_window or 5,
            ),
        )
        return ScopeAgentResult(artifact=artifact, trace=[])


class DeepSeekScopeAgentRuntime:
    """AgentScope role limited to competition and player catalog tools."""

    mode = "deepseek"
    provider = "deepseek"
    model_called = True

    def __init__(self, settings: Settings, catalog: DataCatalogService) -> None:
        if settings.deepseek_api_key is None:
            raise ValueError("DeepSeek API key is required")
        self.settings = settings
        self.catalog = catalog
        self.model_name = settings.deepseek_model

    def _build_model(self) -> DeepSeekChatModel:
        return DeepSeekChatModel(
            credential=DeepSeekCredential(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
            ),
            model=self.settings.deepseek_model,
            parameters=DeepSeekChatModel.Parameters(
                max_tokens=1200,
                temperature=0,
            ),
            stream=False,
            max_retries=1,
            client_kwargs={
                "timeout": self.settings.footops_request_timeout_seconds,
            },
        )

    def _build_agent(self, context: AgentToolContext) -> Agent:
        return Agent(
            name="FootOpsScopeAgent",
            system_prompt=SCOPE_AGENT_SYSTEM_PROMPT,
            model=self._build_model(),
            toolkit=Toolkit(tools=build_scope_tools(self.catalog, context)),
            state=AgentState(
                middle_context={"footops_capability": "analysis_scope_resolution"}
            ),
            react_config=ReActConfig(max_iters=6, structured_output_grace_iters=2),
        )

    async def run(self, request: AgentAnalysisInput) -> ScopeAgentResult:
        context = AgentToolContext()
        agent = self._build_agent(context)
        response = await agent.reply(
            UserMsg(
                name="user",
                content=json.dumps(
                    {
                        "question": request.question,
                        "conversation_history": [
                            turn.model_dump() for turn in request.history
                        ],
                        "scope_hint": request.scope_hint.model_dump(
                            exclude_none=True
                        ),
                    },
                    ensure_ascii=False,
                ),
            ),
            structured_schema=ScopeResolutionArtifact,
        )
        if response.structured_output is None:
            raise RuntimeError("ScopeAgent returned no structured scope")
        artifact = ScopeResolutionArtifact.model_validate(response.structured_output)
        artifact = self._ground_artifact(artifact, request, context)
        return ScopeAgentResult(
            artifact=artifact,
            trace=context.traces,
            usage=collect_agent_model_usage(agent, self.settings),
        )

    @staticmethod
    def _ground_artifact(
        artifact: ScopeResolutionArtifact,
        request: AgentAnalysisInput,
        context: AgentToolContext,
    ) -> ScopeResolutionArtifact:
        """Reject resolved IDs that did not originate from hints or catalog tools."""
        if artifact.status != "resolved":
            return artifact

        hint = request.scope_hint
        competition = context.resolved_competition
        player = context.resolved_player
        if hint.competition_id is not None and hint.season_id is not None:
            competition_id = hint.competition_id
            season_id = hint.season_id
            competition_name = artifact.scope.competition_name
            season_name = artifact.scope.season_name
        elif competition is not None:
            competition_id = competition.competition_id
            season_id = competition.season_id
            competition_name = competition.competition_name
            season_name = competition.season_name
        else:
            return ScopeResolutionArtifact(
                status="clarification_required",
                message="没有从公开赛事目录确认唯一赛事和赛季，请补充范围。",
            )

        if hint.player and hint.player_id is not None:
            player_name = hint.player
            player_id = hint.player_id
        elif player is not None:
            player_name = player.player.player_nickname or player.player.player_name
            player_id = player.player.player_id
        else:
            return ScopeResolutionArtifact(
                status="clarification_required",
                message="没有从所选赛事目录确认唯一球员，请补充完整姓名。",
            )

        return artifact.model_copy(
            update={
                "scope": ResolvedAgentScope(
                    competition_id=competition_id,
                    season_id=season_id,
                    competition_name=competition_name,
                    season_name=season_name,
                    player=player_name,
                    player_id=player_id,
                    requested_window=(
                        hint.requested_window
                        or artifact.scope.requested_window
                        or 5
                    ),
                )
            }
        )

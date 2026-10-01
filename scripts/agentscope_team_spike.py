"""Verify AgentScope TeamCreate/AgentCreate against local SQL + Redis."""

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/agent/src"))

from agentscope.agent import ContextConfig, ReActConfig
from agentscope.app._tool._agent_create import AgentCreate
from agentscope.app._tool._team_create import TeamCreate
from agentscope.app._tool._team_delete import TeamDelete
from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import (
    AgentData,
    AsyncSQLAlchemyStorage,
    ChatModelConfig,
    SessionConfig,
)
from agentscope.app.storage._model._agent import AgentRecord
from agentscope.app.workspace_manager import LocalWorkspaceManager
from footops_agent.runtime.agentscope_app import DEFAULT_TEAM_TEMPLATES


def _texts(chunk: object) -> list[str]:
    return [
        block.text
        for block in getattr(chunk, "content", [])
        if hasattr(block, "text")
    ]


async def run() -> None:
    database_url = os.environ.get("FOOTOPS_AGENT_SCOPE_DATABASE_URL")
    if not database_url:
        raise SystemExit("FOOTOPS_AGENT_SCOPE_DATABASE_URL is required")

    user_id = "footops-team-spike"
    storage = AsyncSQLAlchemyStorage(database_url, create_tables=True)
    message_bus = RedisMessageBus(host="127.0.0.1", port=6379, db=15)
    workspace_manager = LocalWorkspaceManager(
        str(ROOT / ".runtime/agentscope-workspaces"),
    )

    async with storage, message_bus:
        leader = AgentRecord(
            user_id=user_id,
            data=AgentData(
                name="FootOps Coordinator",
                system_prompt="Coordinate FootOps analysis tasks.",
                context_config=ContextConfig(),
                react_config=ReActConfig(),
            ),
        )
        await storage.upsert_agent(user_id, leader)
        workspace_id = workspace_manager.assign_workspace_id(
            user_id=user_id,
            agent_id=leader.id,
            session_id="team-spike",
        )
        leader_session = await storage.upsert_session(
            user_id=user_id,
            agent_id=leader.id,
            config=SessionConfig(
                workspace_id=workspace_id,
                name="FootOps Team Spike",
                chat_model_config=ChatModelConfig(
                    type="openai",
                    credential_id="spike-placeholder",
                    model="deepseek-chat",
                    parameters={},
                ),
            ),
        )

        team_create = TeamCreate(
            storage,
            message_bus,
            workspace_manager,
            user_id,
            leader_session.id,
            leader.id,
        )
        created_team = await team_create(
            name="FootOps Tactical Review",
            description="Coordinate data, knowledge, tactical and evidence work.",
        )
        leader_session = await storage.get_session(
            user_id,
            leader.id,
            leader_session.id,
        )
        if leader_session is None or leader_session.team_id is None:
            raise RuntimeError("TeamCreate did not link the leader session")
        team = await storage.get_team(user_id, leader_session.team_id)
        if team is None:
            raise RuntimeError("TeamCreate did not persist a team")

        agent_create = AgentCreate(
            storage,
            message_bus,
            workspace_manager,
            user_id,
            leader_session.id,
            leader.id,
            {template.type: template for template in DEFAULT_TEAM_TEMPLATES},
        )
        created_member = await agent_create(
            name="data-worker",
            description="Collects authorized match data.",
            prompt="Prepare a MatchDataSnapshot artifact reference for the coordinator.",
            subagent_type="data",
        )
        persisted_team = await storage.get_team(user_id, team.id)
        if persisted_team is None or len(persisted_team.data.members) != 1:
            raise RuntimeError("AgentCreate did not persist the team member")

        result = {
            "status": "ready",
            "team_id": team.id,
            "team_create": _texts(created_team),
            "member_create": _texts(created_member),
            "member_role": persisted_team.data.members[0].role,
            "member_session_id": persisted_team.data.members[0].session_id,
        }
        print(json.dumps(result, ensure_ascii=False))

        # The spike leaves schema intact but removes its temporary records.
        await TeamDelete(
            storage,
            message_bus,
            workspace_manager,
            user_id,
            leader_session.id,
            leader.id,
        )()


if __name__ == "__main__":
    asyncio.run(run())

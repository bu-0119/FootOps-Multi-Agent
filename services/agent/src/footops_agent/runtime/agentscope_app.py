"""Optional AgentScope App/Team containers for the Phase 3B spike.

This module deliberately does not replace the FootOps business harness.  It
provides the service-layer container that can host a future Team Leader while
the existing Coordinator, Board, Artifact and Evidence Gate remain the
business control plane.
"""

from pathlib import Path

from agentscope.app import SubAgentTemplate
from agentscope.app import create_app as create_agentscope_app
from agentscope.app.message_bus import RedisMessageBus
from agentscope.app.storage import AsyncSQLAlchemyStorage, RedisStorage
from agentscope.app.workspace_manager import LocalWorkspaceManager

DEFAULT_TEAM_TEMPLATES = (
    SubAgentTemplate(
        type="data",
        description=(
            "Reads match provider data and publishes MatchDataSnapshot artifacts."
        ),
        system_prompt_template=(
            "You are the FootOps data agent. Only read authorized provider data. "
            "Publish a versioned MatchDataSnapshot reference and never infer tactics "
            "from missing events."
        ),
    ),
    SubAgentTemplate(
        type="knowledge",
        description="Retrieves rules, tactical concepts and metric definitions.",
        system_prompt_template=(
            "You are the FootOps knowledge agent. Use only the registered knowledge "
            "retrieval tool and publish cited KnowledgeEvidence or KnowledgeAnswer "
            "artifacts. Do not invent match cases."
        ),
    ),
    SubAgentTemplate(
        type="tactical",
        description="Builds bounded tactical findings from approved artifacts.",
        system_prompt_template=(
            "You are the FootOps tactical agent. Read approved data and knowledge "
            "artifacts, publish bounded findings or hypotheses, and state what the "
            "evidence cannot establish."
        ),
    ),
    SubAgentTemplate(
        type="evidence",
        description="Audits citations, metric values and claim support.",
        system_prompt_template=(
            "You are the FootOps evidence agent. Independently check artifact "
            "references and reject unsupported claims. You may publish only an "
            "EvidenceReview artifact."
        ),
    ),
)


def _create_app(
    *,
    storage: object,
    redis_host: str,
    redis_port: int,
    redis_db: int,
    workspace_root: str | Path,
):
    """Build the common AgentScope App shell for either storage backend."""

    message_bus = RedisMessageBus(
        host=redis_host,
        port=redis_port,
        db=redis_db,
    )
    workspace_manager = LocalWorkspaceManager(str(workspace_root))
    return create_agentscope_app(
        storage=storage,
        message_bus=message_bus,
        workspace_manager=workspace_manager,
        custom_subagent_templates=list(DEFAULT_TEAM_TEMPLATES),
        title="FootOps AgentScope Runtime",
        version="0.1.0-spike",
    )


def create_footops_agentscope_app(
    *,
    redis_host: str = "127.0.0.1",
    redis_port: int = 6379,
    redis_db: int = 15,
    workspace_root: str | Path = ".runtime/agentscope-workspaces",
):
    """Create the optional AgentScope App using local Redis infrastructure."""

    storage = RedisStorage(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        key_ttl=86400,
    )

    return _create_app(
        storage=storage,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        workspace_root=workspace_root,
    )


def create_footops_agentscope_sql_app(
    database_url: str,
    *,
    redis_host: str = "127.0.0.1",
    redis_port: int = 6379,
    redis_db: int = 15,
    workspace_root: str | Path = ".runtime/agentscope-workspaces",
):
    """Create the App with SQL Storage and Redis for live messaging."""

    storage = AsyncSQLAlchemyStorage(
        database_url,
        create_tables=True,
    )
    return _create_app(
        storage=storage,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db,
        workspace_root=workspace_root,
    )

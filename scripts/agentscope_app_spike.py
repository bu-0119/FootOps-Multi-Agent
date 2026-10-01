"""Smoke-check the optional AgentScope App/Team service layer."""

import json
import sys
from argparse import ArgumentParser
from os import environ
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/agent/src"))

from footops_agent.runtime.agentscope_app import (
    create_footops_agentscope_app,
    create_footops_agentscope_sql_app,
)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--storage",
        choices=("redis", "mysql"),
        default="redis",
        help="AgentScope durable storage backend to verify.",
    )
    args = parser.parse_args()

    if args.storage == "mysql":
        database_url = environ.get("FOOTOPS_AGENT_SCOPE_DATABASE_URL")
        if not database_url:
            raise SystemExit(
                "FOOTOPS_AGENT_SCOPE_DATABASE_URL is required for --storage mysql",
            )
        app = create_footops_agentscope_sql_app(
            database_url,
            workspace_root=ROOT / ".runtime/agentscope-workspaces",
        )
    else:
        app = create_footops_agentscope_app(
            workspace_root=ROOT / ".runtime/agentscope-workspaces",
        )
    with TestClient(app) as client:
        response = client.get("/openapi.json")
        response.raise_for_status()
        schema = response.json()

    routes = set(schema["paths"])
    template_types = sorted(app.state.custom_subagent_templates)
    print(
        json.dumps(
            {
                "status": "ready",
                "storage": args.storage,
                "app_title": schema["info"]["title"],
                "template_types": template_types,
                "service_routes_present": all(
                    route in routes
                    for route in ("/agent/", "/sessions/", "/chat/")
                ),
                "route_count": len(routes),
            },
            ensure_ascii=False,
        ),
    )


if __name__ == "__main__":
    main()

"""Audit public event-data coverage and optionally calculate v1 metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from footops_agent.config import Settings
from footops_agent.providers import StatsBombOpenDataProvider
from footops_agent.services import DataCatalogService, PlayerRoleAnalysisService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit StatsBomb Open Data coverage for one player window.",
    )
    parser.add_argument("--competition-id", type=int, required=True)
    parser.add_argument("--season-id", type=int, required=True)
    parser.add_argument("--player", required=True)
    parser.add_argument("--window", type=int, choices=range(3, 11), default=5)
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Download the suggested event window and calculate v1 metrics.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    settings = Settings()
    provider = StatsBombOpenDataProvider(settings)
    if args.metrics:
        audit, metrics = PlayerRoleAnalysisService(provider).calculate(
            args.competition_id,
            args.season_id,
            args.player,
            args.window,
        )
        payload = {
            "audit": audit.model_dump(mode="json"),
            "metrics": metrics.model_dump(mode="json"),
        }
    else:
        audit = DataCatalogService(provider).audit_player(
            args.competition_id,
            args.season_id,
            args.player,
            args.window,
        )
        payload = {"audit": audit.model_dump(mode="json")}

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()

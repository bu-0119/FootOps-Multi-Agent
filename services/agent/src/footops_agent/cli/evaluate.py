"""Run the deterministic, LLM, single-Agent and multi-Agent comparison."""

import argparse
import asyncio
import json
from pathlib import Path

from footops_agent.config import Settings
from footops_agent.evaluation import EvaluationService, GoldenTaskSuite
from footops_agent.evaluation.runners import (
    DeterministicEvaluationRunner,
    DirectLlmEvaluationRunner,
    EvaluationRunner,
    MultiAgentEvaluationRunner,
    SingleAgentEvaluationRunner,
)
from footops_agent.harness import FootOpsAnalysisHarness
from footops_agent.providers import StatsBombOpenDataProvider
from footops_agent.repositories import InMemoryAnalysisWorkspaceRepository
from footops_agent.runtime import (
    DeepSeekDirectLlmRuntime,
    DeepSeekScopeAgentRuntime,
    FootOpsMultiAgentRuntime,
)
from footops_agent.services import AnalysisWorkspaceService, DataCatalogService

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SUITE = ROOT / "data/evaluation/player-role-v1.json"
DEFAULT_REPORT = ROOT / "data/evaluation/reports/phase3-latest.json"
VALID_MODES = ("deterministic", "direct_llm", "single_agent", "multi_agent")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare deterministic, direct LLM, single and multi-Agent modes.",
    )
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--modes",
        default=",".join(VALID_MODES),
        help=(
            "Comma-separated modes: deterministic,direct_llm,single_agent,"
            "multi_agent"
        ),
    )
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Run only the named task_id; may be supplied more than once.",
    )
    return parser.parse_args()


def _parse_modes(raw: str) -> list[str]:
    modes = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = sorted(set(modes).difference(VALID_MODES))
    if unknown:
        raise ValueError(f"unknown evaluation modes: {', '.join(unknown)}")
    if not modes:
        raise ValueError("at least one evaluation mode is required")
    return modes


def _load_suite(path: Path, selected_tasks: list[str]) -> GoldenTaskSuite:
    suite = GoldenTaskSuite.model_validate_json(path.read_text(encoding="utf-8"))
    if not selected_tasks:
        return suite
    selected = set(selected_tasks)
    tasks = [task for task in suite.tasks if task.task_id in selected]
    missing = sorted(selected.difference(task.task_id for task in tasks))
    if missing:
        raise ValueError(f"unknown task ids: {', '.join(missing)}")
    return suite.model_copy(update={"tasks": tasks})


def _build_runners(settings: Settings, modes: list[str]) -> list[EvaluationRunner]:
    model_modes = {"direct_llm", "single_agent", "multi_agent"}.intersection(modes)
    if model_modes and not settings.deepseek_key_configured:
        raise ValueError(
            "DEEPSEEK_API_KEY is required for direct_llm or single_agent mode"
        )

    provider = StatsBombOpenDataProvider(settings)
    repository = InMemoryAnalysisWorkspaceRepository()
    catalog = DataCatalogService(provider)
    workspace_service = AnalysisWorkspaceService(provider, repository)
    runners: list[EvaluationRunner] = []
    for mode in modes:
        if mode == "deterministic":
            runners.append(DeterministicEvaluationRunner(workspace_service))
        elif mode == "direct_llm":
            runners.append(
                DirectLlmEvaluationRunner(DeepSeekDirectLlmRuntime(settings))
            )
        elif mode == "single_agent":
            runners.append(
                SingleAgentEvaluationRunner(
                    FootOpsAnalysisHarness(
                        settings.model_copy(update={"llm_mode": "deepseek"}),
                        catalog,
                        workspace_service,
                    )
                )
            )
        elif mode == "multi_agent":
            runners.append(
                MultiAgentEvaluationRunner(
                    FootOpsMultiAgentRuntime(provider, repository),
                    DeepSeekScopeAgentRuntime(
                        settings.model_copy(update={"llm_mode": "deepseek"}),
                        catalog,
                    ),
                )
            )
    return runners


async def _run(args: argparse.Namespace) -> int:
    modes = _parse_modes(args.modes)
    suite = _load_suite(args.suite, args.task)
    report = await EvaluationService(
        _build_runners(Settings(), modes),
    ).run(suite)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"report: {args.output}")
    for summary in report.summaries:
        print(
            f"{summary.mode}: {summary.passed_cases}/{summary.total_cases} passed, "
            f"avg {summary.average_latency_ms:.1f} ms, "
            f"tokens {summary.total_input_tokens + summary.total_output_tokens}"
        )
    return 0


def run() -> int:
    """Console-script entry point."""
    try:
        return asyncio.run(_run(_arguments()))
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(run())

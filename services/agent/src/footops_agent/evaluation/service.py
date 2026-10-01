"""Evaluation orchestration and aggregate metric calculation."""

from collections import defaultdict
from uuid import uuid4

from .models import (
    EvaluationAssertions,
    EvaluationCaseResult,
    EvaluationMode,
    EvaluationObservation,
    EvaluationReport,
    EvaluationSummary,
    GoldenTask,
    GoldenTaskSuite,
)
from .runners import EvaluationRunner


class EvaluationService:
    """Run the same golden tasks against configured comparison modes."""

    def __init__(self, runners: list[EvaluationRunner]) -> None:
        self.runners = runners

    async def run(self, suite: GoldenTaskSuite) -> EvaluationReport:
        results: list[EvaluationCaseResult] = []
        for task in suite.tasks:
            for runner in self.runners:
                observation = await runner.run(task)
                assertions = _assertions(task, observation)
                checks = [
                    assertions.status_match,
                    assertions.workspace_match,
                    assertions.no_unsupported_completion,
                ]
                if assertions.tool_sequence_match is not None:
                    checks.append(assertions.tool_sequence_match)
                if assertions.supported_claims is not None:
                    checks.append(assertions.supported_claims)
                results.append(
                    EvaluationCaseResult(
                        task_id=task.task_id,
                        mode=runner.mode,
                        passed=all(checks),
                        observation=observation,
                        assertions=assertions,
                    )
                )
        return EvaluationReport(
            report_id=uuid4().hex,
            suite_id=suite.suite_id,
            results=results,
            summaries=_summaries(results),
            notes=[
                "直接 LLM 基线不提供工具或比赛数据，完成型任务失败是有效对照结果。",
                "费用仅在配置每百万 Token 单价后估算；未配置时保留为 null。",
                "评测不保存模型思维过程或 API Key。",
            ],
        )


def _assertions(
    task: GoldenTask,
    observation: EvaluationObservation,
) -> EvaluationAssertions:
    status = observation.status
    workspace_id = observation.workspace_id
    mode = observation.mode
    tool_sequence = observation.tool_sequence
    claim_support_rate = observation.claim_support_rate
    expected = task.expectation
    status_match = status == expected.status
    workspace_match = (workspace_id is not None) == expected.require_workspace
    tool_match = None
    if mode == "single_agent" and expected.required_agent_tools:
        tool_match = _is_subsequence(expected.required_agent_tools, tool_sequence)
    supported_claims = None
    if workspace_id is not None:
        supported_claims = claim_support_rate == 1.0
    return EvaluationAssertions(
        status_match=status_match,
        workspace_match=workspace_match,
        tool_sequence_match=tool_match,
        supported_claims=supported_claims,
        no_unsupported_completion=not (
            status == "completed" and workspace_id is None
        ),
    )


def _is_subsequence(required: list[str], actual: list[str]) -> bool:
    index = 0
    for tool_name in actual:
        if index < len(required) and tool_name == required[index]:
            index += 1
    return index == len(required)


def _summaries(results: list[EvaluationCaseResult]) -> list[EvaluationSummary]:
    grouped: dict[EvaluationMode, list[EvaluationCaseResult]] = defaultdict(list)
    for result in results:
        grouped[result.mode].append(result)

    summaries: list[EvaluationSummary] = []
    for mode, rows in grouped.items():
        usage_rows = [row.observation.usage for row in rows if row.observation.usage]
        known_costs = [
            usage.estimated_cost_usd
            for usage in usage_rows
            if usage is not None and usage.estimated_cost_usd is not None
        ]
        tool_rows = [
            row.assertions.tool_sequence_match
            for row in rows
            if row.assertions.tool_sequence_match is not None
        ]
        support_rows = [
            row.observation.claim_support_rate
            for row in rows
            if row.observation.claim_support_rate is not None
        ]
        summaries.append(
            EvaluationSummary(
                mode=mode,
                total_cases=len(rows),
                passed_cases=sum(row.passed for row in rows),
                pass_rate=sum(row.passed for row in rows) / len(rows),
                average_latency_ms=round(
                    sum(row.observation.duration_ms for row in rows) / len(rows),
                    3,
                ),
                total_input_tokens=sum(
                    usage.input_tokens for usage in usage_rows if usage is not None
                ),
                total_output_tokens=sum(
                    usage.output_tokens for usage in usage_rows if usage is not None
                ),
                estimated_cost_usd=(
                    round(sum(known_costs), 8)
                    if len(known_costs) == len(usage_rows) and usage_rows
                    else None
                ),
                tool_sequence_accuracy=(
                    sum(bool(value) for value in tool_rows) / len(tool_rows)
                    if tool_rows
                    else None
                ),
                average_claim_support_rate=(
                    sum(support_rows) / len(support_rows)
                    if support_rows
                    else None
                ),
                unsupported_completion_count=sum(
                    not row.assertions.no_unsupported_completion for row in rows
                ),
                error_count=sum(
                    row.observation.status == "error" for row in rows
                ),
            )
        )
    return summaries

"""Build descriptive findings without asking a language model to calculate."""

from collections.abc import Callable
from dataclasses import dataclass
from statistics import fmean

from footops_agent.artifacts import (
    EvidenceReference,
    EvidenceSetArtifact,
    FindingArtifact,
    FindingSetArtifact,
    FindingTimeRange,
    PlayerRoleMetricArtifact,
)


@dataclass(frozen=True)
class MetricFindingSpec:
    field: str
    label: str
    stable_threshold: float
    formatter: Callable[[float], str]


METRIC_FINDING_SPECS = (
    MetricFindingSpec(
        field="average_touch_x",
        label="平均触球纵向坐标",
        stable_threshold=2.0,
        formatter=lambda value: f"{value:.1f}",
    ),
    MetricFindingSpec(
        field="attacking_third_touch_ratio",
        label="进攻三区触球占比",
        stable_threshold=0.05,
        formatter=lambda value: f"{value * 100:.0f}%",
    ),
    MetricFindingSpec(
        field="average_receipt_x",
        label="平均接球纵向坐标",
        stable_threshold=2.0,
        formatter=lambda value: f"{value:.1f}",
    ),
)


class DeterministicFindingBuilder:
    """Compare the first and last portions of one audited match window."""

    def build(
        self,
        metrics: PlayerRoleMetricArtifact,
    ) -> tuple[FindingSetArtifact, EvidenceSetArtifact]:
        rows = metrics.matches
        if len(rows) < 3:
            raise ValueError("at least three metric rows are required")
        if len(metrics.sources) != len(rows):
            raise ValueError("each metric row must have one source reference")

        references = self._source_references(metrics)
        findings: list[FindingArtifact] = []
        for spec in METRIC_FINDING_SPECS:
            result = self._finding_for_metric(metrics, spec)
            if result is None:
                continue
            finding, metric_references = result
            findings.append(finding)
            references.extend(metric_references)
        if not findings:
            raise ValueError("no complete metric series is available for findings")
        return (
            FindingSetArtifact(findings=findings),
            EvidenceSetArtifact(references=references),
        )

    def _source_references(
        self,
        metrics: PlayerRoleMetricArtifact,
    ) -> list[EvidenceReference]:
        return [
            EvidenceReference(
                evidence_id=f"source:{row.match_id}",
                kind="source",
                source_url=source.source_url,
                match_id=row.match_id,
                detail=f"{row.match_date.isoformat()} 比赛事件数据",
            )
            for row, source in zip(metrics.matches, metrics.sources, strict=True)
        ]

    def _finding_for_metric(
        self,
        metrics: PlayerRoleMetricArtifact,
        spec: MetricFindingSpec,
    ) -> tuple[FindingArtifact, list[EvidenceReference]] | None:
        values = [getattr(row, spec.field) for row in metrics.matches]
        if any(value is None for value in values):
            return None
        numeric_values = [float(value) for value in values if value is not None]
        comparison_size = max(1, len(numeric_values) // 2)
        early_mean = fmean(numeric_values[:comparison_size])
        late_mean = fmean(numeric_values[-comparison_size:])
        delta = late_mean - early_mean
        direction = _direction(delta, spec.stable_threshold)
        direction_text = {
            "increase": "上升至",
            "decrease": "下降至",
            "stable": "保持在",
        }[direction]
        rows = metrics.matches
        metric_refs = [f"metric:{spec.field}:{row.match_id}" for row in rows]
        source_refs = [f"source:{row.match_id}" for row in rows]
        finding = FindingArtifact(
            finding_id=f"finding:{spec.field}",
            statement=(
                f"在所选五场样本中，{spec.label}由前{comparison_size}场均值"
                f" {spec.formatter(early_mean)} {direction_text}"
                f"后{comparison_size}场均值"
                f" {spec.formatter(late_mean)}。"
            ),
            claim_type="descriptive",
            metric_refs=metric_refs,
            source_refs=source_refs,
            time_range=FindingTimeRange(
                start_date=rows[0].match_date,
                end_date=rows[-1].match_date,
                match_ids=[row.match_id for row in rows],
            ),
            direction=direction,
            confidence=0.9,
            limitations=[
                "这是样本内的描述性比较，不等同于战术角色变化。",
                "前后分段均值会受到对手、比分和出场时间影响。",
            ],
        )
        metric_evidence = [
            EvidenceReference(
                evidence_id=reference_id,
                kind="metric",
                match_id=row.match_id,
                metric_name=spec.field,
                metric_value=getattr(row, spec.field),
                detail=f"{row.match_date.isoformat()} · {spec.label}",
            )
            for reference_id, row in zip(metric_refs, rows, strict=True)
        ]
        return finding, metric_evidence


def _direction(delta: float, stable_threshold: float) -> str:
    if delta > stable_threshold:
        return "increase"
    if delta < -stable_threshold:
        return "decrease"
    return "stable"

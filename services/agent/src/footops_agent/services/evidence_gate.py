"""Deterministic support checks for finding references and metric values."""

from math import isclose

from footops_agent.artifacts import (
    EvidenceReviewArtifact,
    EvidenceSetArtifact,
    FindingArtifact,
    FindingEvidenceReview,
    FindingSetArtifact,
    PlayerRoleMetricArtifact,
)


class EvidenceGate:
    """Reject claims that cannot be reproduced from the supplied artifacts."""

    def review(
        self,
        findings: FindingSetArtifact,
        evidence: EvidenceSetArtifact,
        metrics: PlayerRoleMetricArtifact,
    ) -> EvidenceReviewArtifact:
        evidence_by_id = {item.evidence_id: item for item in evidence.references}
        duplicate_ids = len(evidence_by_id) != len(evidence.references)
        metric_rows = {row.match_id: row for row in metrics.matches}
        source_urls = {source.source_url for source in metrics.sources}
        reviews = [
            self._review_finding(
                finding,
                evidence_by_id,
                metric_rows,
                source_urls,
                duplicate_ids,
            )
            for finding in findings.findings
        ]
        supported = sum(review.status == "supported" for review in reviews)
        if supported == len(reviews):
            overall_status = "passed"
        elif supported == 0 and all(review.status == "rejected" for review in reviews):
            overall_status = "rejected"
        else:
            overall_status = "partial"
        return EvidenceReviewArtifact(
            overall_status=overall_status,
            support_rate=round(supported / len(reviews), 4),
            reviews=reviews,
            limitations=[
                "门禁只核验结构化引用、数值和范围，不负责判断完整战术因果。",
                "仅有事件数据支持描述性 Finding；战术推断仍需额外证据。",
            ],
        )

    def _review_finding(
        self,
        finding: FindingArtifact,
        evidence_by_id: dict[str, object],
        metric_rows: dict[int, object],
        source_urls: set[str],
        duplicate_ids: bool,
    ) -> FindingEvidenceReview:
        reasons: list[str] = []
        accepted_metric_refs: list[str] = []
        accepted_source_refs: list[str] = []
        if duplicate_ids:
            reasons.append("证据集合包含重复 evidence_id。")

        for reference_id in finding.metric_refs:
            reference = evidence_by_id.get(reference_id)
            if reference is None or getattr(reference, "kind", None) != "metric":
                reasons.append(f"指标引用不存在或类型错误：{reference_id}")
                continue
            row = metric_rows.get(reference.match_id)
            metric_name = reference.metric_name
            if row is None or metric_name not in row.__class__.model_fields:
                reasons.append(f"指标引用无法定位字段：{reference_id}")
                continue
            actual_value = getattr(row, metric_name)
            if not _same_number(actual_value, reference.metric_value):
                reasons.append(f"指标引用数值不一致：{reference_id}")
                continue
            accepted_metric_refs.append(reference_id)

        for reference_id in finding.source_refs:
            reference = evidence_by_id.get(reference_id)
            if reference is None or getattr(reference, "kind", None) != "source":
                reasons.append(f"来源引用不存在或类型错误：{reference_id}")
                continue
            if reference.source_url not in source_urls:
                reasons.append(f"来源 URL 不属于当前 Metric Artifact：{reference_id}")
                continue
            accepted_source_refs.append(reference_id)

        referenced_match_ids = {
            evidence_by_id[reference_id].match_id
            for reference_id in accepted_metric_refs
        }
        if referenced_match_ids != set(finding.time_range.match_ids):
            reasons.append("Finding 时间范围与指标引用的比赛集合不一致。")
        referenced_rows = [metric_rows[match_id] for match_id in referenced_match_ids]
        if referenced_rows:
            dates = sorted(row.match_date for row in referenced_rows)
            if (
                finding.time_range.start_date != dates[0]
                or finding.time_range.end_date != dates[-1]
            ):
                reasons.append("Finding 起止日期与指标引用不一致。")

        if reasons:
            status = "rejected"
        elif finding.claim_type == "inference":
            status = "needs_more_evidence"
            reasons.append("事件指标只能直接支持描述性观察，不能单独证明战术因果。")
        else:
            status = "supported"
            reasons.append("指标字段、数值、来源和时间范围均通过确定性核验。")
        return FindingEvidenceReview(
            finding_id=finding.finding_id,
            status=status,
            accepted_metric_refs=accepted_metric_refs,
            accepted_source_refs=accepted_source_refs,
            reasons=reasons,
        )


def _same_number(left: object, right: object) -> bool:
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return False
    return isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)

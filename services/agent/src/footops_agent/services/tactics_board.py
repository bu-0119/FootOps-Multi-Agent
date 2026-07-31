"""Build a board visualization from reviewed descriptive findings."""

from statistics import fmean

from footops_agent.artifacts import (
    BoardPoint,
    EvidenceReviewArtifact,
    FindingArtifact,
    PlayerRoleMetricArtifact,
    TacticsAnnotation,
    TacticsArrow,
    TacticsBoardArtifact,
    TacticsPlayerMarker,
    TacticsZone,
)


class DeterministicTacticsBoardBuilder:
    """Map reviewed position observations onto a normalized vertical pitch."""

    def build(
        self,
        metrics: PlayerRoleMetricArtifact,
        findings: list[FindingArtifact],
        review: EvidenceReviewArtifact,
    ) -> TacticsBoardArtifact:
        supported = {
            item.finding_id: item
            for item in review.reviews
            if item.status == "supported"
        }
        reviewed_findings = [
            finding for finding in findings if finding.finding_id in supported
        ]
        touch_finding = next(
            (
                finding
                for finding in reviewed_findings
                if finding.finding_id == "finding:average_touch_x"
            ),
            None,
        )
        if touch_finding is None:
            raise ValueError("a supported average-touch finding is required")

        rows = metrics.matches
        comparison_size = max(1, len(rows) // 2)
        early = self._mean_point(rows[:comparison_size])
        late = self._mean_point(rows[-comparison_size:])
        player_name = metrics.player.player_nickname or metrics.player.player_name
        all_finding_refs = [finding.finding_id for finding in reviewed_findings]
        evidence_refs = sorted(
            {
                reference
                for finding_id in all_finding_refs
                for reference in (
                    supported[finding_id].accepted_metric_refs
                    + supported[finding_id].accepted_source_refs
                )
            }
        )

        return TacticsBoardArtifact(
            title=f"{player_name} 五场样本位置变化",
            players=[
                TacticsPlayerMarker(
                    marker_id="focus:late-touch-position",
                    label=f"{player_name} 后{comparison_size}场平均触球位置",
                    display_label="P",
                    position=late,
                    finding_refs=[touch_finding.finding_id],
                )
            ],
            zones=[
                self._touch_zone(
                    "zone:early-touch",
                    f"前{comparison_size}场平均触球区域",
                    early,
                    touch_finding.finding_id,
                ),
                self._touch_zone(
                    "zone:late-touch",
                    f"后{comparison_size}场平均触球区域",
                    late,
                    touch_finding.finding_id,
                ),
            ],
            arrows=[
                TacticsArrow(
                    arrow_id="arrow:touch-position-change",
                    label="样本前后平均触球位置变化",
                    kind="movement",
                    start=early,
                    end=late,
                    finding_refs=[touch_finding.finding_id],
                )
            ],
            annotations=[
                TacticsAnnotation(
                    annotation_id=f"annotation:{index}",
                    text=finding.statement,
                    finding_refs=[finding.finding_id],
                )
                for index, finding in enumerate(reviewed_findings, start=1)
            ],
            finding_refs=all_finding_refs,
            evidence_refs=evidence_refs,
            limitations=[
                "图层展示样本内平均位置变化，不代表球队阵型或战术因果。",
                "公开事件数据不包含连续追踪坐标，因此不生成传球通道。",
            ],
        )

    @staticmethod
    def _mean_point(rows: list) -> BoardPoint:
        touch_x = [row.average_touch_x for row in rows]
        touch_y = [row.average_touch_y for row in rows]
        if any(value is None for value in [*touch_x, *touch_y]):
            raise ValueError("complete average-touch coordinates are required")
        statsbomb_x = fmean(float(value) for value in touch_x if value is not None)
        statsbomb_y = fmean(float(value) for value in touch_y if value is not None)
        return BoardPoint(
            x=round(statsbomb_y / 80 * 100, 2),
            y=round(100 - statsbomb_x / 120 * 100, 2),
        )

    @staticmethod
    def _touch_zone(
        zone_id: str,
        label: str,
        point: BoardPoint,
        finding_id: str,
    ) -> TacticsZone:
        width = 20.0
        height = 14.0
        return TacticsZone(
            zone_id=zone_id,
            label=label,
            kind="touch_area",
            x=max(0, min(100 - width, point.x - width / 2)),
            y=max(0, min(100 - height, point.y - height / 2)),
            width=width,
            height=height,
            finding_refs=[finding_id],
        )

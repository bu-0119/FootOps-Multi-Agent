"""Deterministic player-role metrics computed from normalized event snapshots."""

from collections.abc import Iterable

from footops_agent.artifacts import (
    MatchDataSnapshot,
    MatchRoleMetrics,
    PlayerEvent,
    PlayerRoleMetricArtifact,
)

TOUCH_EVENT_TYPES = frozenset(
    {
        "Ball Receipt*",
        "Ball Recovery",
        "Carry",
        "Clearance",
        "Dispossessed",
        "Dribble",
        "Interception",
        "Miscontrol",
        "Pass",
        "Shot",
    }
)


class PlayerRoleMetricEngine:
    """Calculate v1 metrics; no model output is accepted as numeric input."""

    progressive_carry_min_x = 10.0

    def compute(
        self,
        snapshots: list[MatchDataSnapshot],
    ) -> PlayerRoleMetricArtifact:
        if not snapshots:
            raise ValueError("at least one match snapshot is required")
        player_id = snapshots[0].player.player_id
        if any(snapshot.player.player_id != player_id for snapshot in snapshots):
            raise ValueError("all snapshots must describe the same player")

        ordered = sorted(snapshots, key=lambda item: item.match.match_date)
        return PlayerRoleMetricArtifact(
            player=ordered[0].player,
            sources=[snapshot.source for snapshot in ordered],
            matches=[self._match_metrics(snapshot) for snapshot in ordered],
            limitations=[
                "触球数是由带坐标的持球事件构成的可复算代理指标，"
                "不等同于商业数据源的官方 touches。",
                "公开事件数据不包含完整无球跑动和连续追踪坐标，不能直接推断全部战术职责。",
                "纵向坐标使用 StatsBomb 120x80 标准化球场；不同数据源不可直接混算。",
            ],
        )

    def _match_metrics(self, snapshot: MatchDataSnapshot) -> MatchRoleMetrics:
        touch_events = [
            event
            for event in snapshot.events
            if event.event_type in TOUCH_EVENT_TYPES and event.location is not None
        ]
        touch_locations = [event.location for event in touch_events if event.location]
        attacking_third = [point for point in touch_locations if point.x >= 80]
        penalty_area = [
            point
            for point in touch_locations
            if point.x >= 102 and 18 <= point.y <= 62
        ]
        receipts = [
            event
            for event in snapshot.events
            if event.event_type == "Ball Receipt*" and event.location is not None
        ]
        receipt_locations = [event.location for event in receipts if event.location]
        forward_passes = [
            event for event in snapshot.events if self._is_forward_pass(event)
        ]
        completed_forward = [
            event for event in forward_passes if self._is_completed_pass(event)
        ]
        progressive_carries = [
            event for event in snapshot.events if self._is_progressive_carry(event)
        ]
        key_passes = [
            event
            for event in snapshot.events
            if event.event_type == "Pass"
            and (
                event.pass_shot_assist
                or event.pass_goal_assist
                or event.pass_assisted_shot_id is not None
            )
        ]
        shots = [event for event in snapshot.events if event.event_type == "Shot"]
        return MatchRoleMetrics(
            match_id=snapshot.match.match_id,
            match_date=snapshot.match.match_date,
            event_count=len(snapshot.events),
            touch_event_count=len(touch_locations),
            average_touch_x=_average(point.x for point in touch_locations),
            average_touch_y=_average(point.y for point in touch_locations),
            attacking_third_touch_count=len(attacking_third),
            attacking_third_touch_ratio=_ratio(
                len(attacking_third),
                len(touch_locations),
            ),
            penalty_area_touch_count=len(penalty_area),
            penalty_area_touch_ratio=_ratio(
                len(penalty_area),
                len(touch_locations),
            ),
            receipt_count=len(receipt_locations),
            average_receipt_x=_average(point.x for point in receipt_locations),
            forward_pass_count=len(forward_passes),
            completed_forward_pass_count=len(completed_forward),
            progressive_carry_count=len(progressive_carries),
            key_pass_count=len(key_passes),
            shot_count=len(shots),
            shot_involvement_count=len(key_passes) + len(shots),
        )

    def _is_forward_pass(self, event: PlayerEvent) -> bool:
        return (
            event.event_type == "Pass"
            and event.location is not None
            and event.end_location is not None
            and event.end_location.x > event.location.x
        )

    def _is_completed_pass(self, event: PlayerEvent) -> bool:
        return event.event_type == "Pass" and event.outcome in {None, "Complete"}

    def _is_progressive_carry(self, event: PlayerEvent) -> bool:
        return (
            event.event_type == "Carry"
            and event.location is not None
            and event.end_location is not None
            and event.end_location.x - event.location.x >= self.progressive_carry_min_x
        )


def _average(values: Iterable[float]) -> float | None:
    items = list(values)
    if not items:
        return None
    return round(sum(items) / len(items), 3)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)

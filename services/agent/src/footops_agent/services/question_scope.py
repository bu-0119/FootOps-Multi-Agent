"""Route Phase 2A questions to supported deterministic findings."""

from dataclasses import dataclass


class UnsupportedAnalysisQuestionError(ValueError):
    """Raised when a question cannot be answered by the golden data slice."""

    public_message = (
        "当前版本只支持 Pedri 最近 3 至 10 场的平均触球位置、进攻三区触球占比、"
        "平均接球位置或综合角色变化。请明确写出“佩德里”和要分析的指标。"
    )


@dataclass(frozen=True)
class PlayerRoleQuestionSelection:
    finding_ids: tuple[str, ...]


class PlayerRoleQuestionRouter:
    """Select deterministic findings without pretending to support open QA."""

    _finding_keywords = {
        "finding:average_touch_x": (
            "平均触球",
            "触球位置",
            "触球坐标",
            "活动位置",
            "位置变化",
            "站位变化",
        ),
        "finding:attacking_third_touch_ratio": (
            "进攻三区",
            "前场触球",
            "进攻区域",
        ),
        "finding:average_receipt_x": (
            "平均接球",
            "接球位置",
            "接球坐标",
            "接应位置",
        ),
    }
    _all_finding_ids = tuple(_finding_keywords)
    _broad_keywords = ("角色变化", "综合分析", "整体变化", "持球变化")
    _time_keywords = ("最近", "近三场", "近五场", "多场", "样本")

    def select(
        self,
        question: str,
        player_query: str,
    ) -> PlayerRoleQuestionSelection:
        normalized = "".join(question.lower().split())
        aliases = {"".join(player_query.lower().split())}
        if "pedri" in aliases:
            aliases.add("佩德里")
        if not any(alias and alias in normalized for alias in aliases):
            raise UnsupportedAnalysisQuestionError

        selected = tuple(
            finding_id
            for finding_id, keywords in self._finding_keywords.items()
            if any(keyword in normalized for keyword in keywords)
        )
        if selected:
            return PlayerRoleQuestionSelection(finding_ids=selected)

        is_broad = any(keyword in normalized for keyword in self._broad_keywords)
        has_time_scope = any(keyword in normalized for keyword in self._time_keywords)
        if is_broad and has_time_scope:
            return PlayerRoleQuestionSelection(finding_ids=self._all_finding_ids)
        raise UnsupportedAnalysisQuestionError

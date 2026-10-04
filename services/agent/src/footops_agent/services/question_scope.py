"""Route Phase 2A questions to supported deterministic findings."""

from dataclasses import dataclass


class UnsupportedAnalysisQuestionError(ValueError):
    """Raised when a question cannot be answered by the golden data slice."""

    public_message = (
        "当前数据链支持已选球员最近 3 至 10 场的位置与触球区域、向前传球、"
        "推进带球、关键传球和射门参与趋势。暂不支持 xG、射正、进球、助攻、"
        "防守和球员评分。"
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
            "touch position",
            "average touch",
        ),
        "finding:attacking_third_touch_ratio": (
            "进攻三区",
            "前场触球",
            "进攻区域",
            "attacking third",
        ),
        "finding:average_receipt_x": (
            "平均接球",
            "接球位置",
            "接球坐标",
            "接应位置",
            "receipt position",
            "average receipt",
        ),
        "finding:penalty_area_touch_ratio": (
            "禁区触球",
            "禁区内触球",
            "penalty area touch",
        ),
        "finding:forward_pass_count": (
            "向前传球",
            "纵向传球",
            "forward pass",
        ),
        "finding:completed_forward_pass_count": (
            "向前传球",
            "成功向前传球",
            "纵向传球",
            "completed forward pass",
        ),
        "finding:progressive_carry_count": (
            "推进带球",
            "持球推进",
            "带球推进",
            "progressive carry",
        ),
        "finding:key_pass_count": (
            "关键传球",
            "创造机会",
            "key pass",
        ),
        "finding:shot_count": (
            "射门次数",
            "射门变化",
            "射门表现",
            "射门最多",
            "哪场射门",
            "哪一场射门",
            "shots",
        ),
        "finding:expected_goals": (
            "预期进球",
            "预期进球值",
            "xg",
            "x.g.",
            "expected goals",
        ),
        "finding:shot_involvement_count": (
            "射门参与",
            "参与射门",
            "进攻参与",
            "shot involvement",
        ),
    }
    _all_finding_ids = tuple(_finding_keywords)
    _broad_finding_ids = (
        "finding:average_touch_x",
        "finding:attacking_third_touch_ratio",
        "finding:average_receipt_x",
        "finding:completed_forward_pass_count",
        "finding:progressive_carry_count",
        "finding:shot_involvement_count",
    )
    _broad_keywords = (
        "角色变化",
        "综合分析",
        "整体变化",
        "持球变化",
        "表现变化",
        "发挥最好",
        "表现最好",
        "哪场",
        "哪一场",
        "最好的一场",
        "最高",
        "最多",
        "近期表现",
        "最近表现",
        "比赛表现",
        "场上作用",
        "踢法变化",
        "活动趋势",
        "位置趋势",
        "role change",
        "recent form",
    )
    _generic_analysis_keywords = (
        "分析",
        "表现",
        "趋势",
        "变化",
        "怎么样",
        "如何",
        "看看",
        "看一下",
        "近期",
        "最近",
    )
    _unsupported_metric_keywords = (
        "进球",
        "助攻",
        "射正",
        "过人",
        "抢断",
        "拦截",
        "犯规",
        "评分",
        "goal",
        "assist",
        "shot on target",
        "dribble",
        "tackle",
    )

    def select(
        self,
        question: str,
        player_query: str,
    ) -> PlayerRoleQuestionSelection:
        normalized = "".join(question.lower().split())
        if not player_query.strip():
            raise UnsupportedAnalysisQuestionError

        asks_unsupported_metric = any(
            keyword in normalized for keyword in self._unsupported_metric_keywords
        )
        if asks_unsupported_metric:
            raise UnsupportedAnalysisQuestionError

        selected = tuple(
            finding_id
            for finding_id, keywords in self._finding_keywords.items()
            if any(keyword in normalized for keyword in keywords)
        )
        if selected:
            return PlayerRoleQuestionSelection(finding_ids=selected)

        is_broad = any(keyword in normalized for keyword in self._broad_keywords)
        if is_broad:
            return PlayerRoleQuestionSelection(finding_ids=self._broad_finding_ids)

        is_generic_analysis = any(
            keyword in normalized for keyword in self._generic_analysis_keywords
        )
        if is_generic_analysis:
            return PlayerRoleQuestionSelection(finding_ids=self._broad_finding_ids)
        raise UnsupportedAnalysisQuestionError

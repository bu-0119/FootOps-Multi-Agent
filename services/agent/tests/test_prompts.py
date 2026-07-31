"""Regression tests for the active FootOps AI role prompt."""

from footops_agent.prompts import (
    FOOTOPS_ROLE_PROMPT,
    PLANNER_PROMPT_VERSION,
    PLANNER_SYSTEM_PROMPT,
)


def test_planner_prompt_builds_on_footops_role() -> None:
    assert PLANNER_SYSTEM_PROMPT.startswith(FOOTOPS_ROLE_PROMPT)
    assert PLANNER_PROMPT_VERSION == "footops-planner-zh-v1"
    assert "FootOpsPlanner" in PLANNER_SYSTEM_PROMPT
    assert "简体中文" in PLANNER_SYSTEM_PROMPT


def test_planner_prompt_preserves_current_product_boundaries() -> None:
    required_boundaries = (
        "不回答用户问题本身",
        "不声称已经读取比赛",
        "不能由你估算或生成数值",
        "未生成真实结论",
        "AnalysisPlan Schema",
        "证据审核步骤",
    )

    for boundary in required_boundaries:
        assert boundary in PLANNER_SYSTEM_PROMPT

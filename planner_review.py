"""总策划生成与审核流程。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from Agent_model import Planner_Agent
from prompt import build_planner_agent_prompt


@dataclass
class PlannerReviewState:
    """记录当前大纲的审核状态。"""

    planner_output: dict[str, Any] | None = None
    approved: bool = False
    review_history: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.review_history is None:
            self.review_history = []


def generate_planner_outline(
    planner_agent: Planner_Agent,
    runtime_config: dict[str, Any],
    feedback: str | None = None,
) -> dict[str, Any] | str:
    """调用 planner 生成或修订分集大纲。"""
    planner_prompt = build_planner_agent_prompt(runtime_config, user_feedback=feedback)
    return planner_agent.generate_outline(planner_prompt)


def revise_planner_outline(
    review_state: PlannerReviewState,
    planner_agent: Planner_Agent,
    runtime_config: dict[str, Any],
    feedback: str,
) -> dict[str, Any] | str:
    """根据导演反馈重新生成大纲，并记录 review 历史。"""
    planner_output = generate_planner_outline(planner_agent, runtime_config, feedback=feedback)
    review_state.review_history.append(
        {
            "action": "revise_outline",
            "feedback": feedback,
            "result": planner_output if isinstance(planner_output, str) else "ok",
        }
    )
    if isinstance(planner_output, dict):
        review_state.planner_output = planner_output
        review_state.approved = False
    return planner_output


def approve_planner_outline(review_state: PlannerReviewState) -> dict[str, Any]:
    """冻结当前审核通过的大纲。"""
    if review_state.planner_output is None:
        raise ValueError("当前没有可审批的大纲")
    review_state.approved = True
    review_state.review_history.append({"action": "approve_outline"})
    return review_state.planner_output

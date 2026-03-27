from __future__ import annotations

import copy
from typing import Any

from event_committer import commit_system_event
from log_writer import truncate_episode_log
from planner_review import PlannerReviewState, approve_planner_outline, revise_planner_outline


def apply_director_command(session: Any, command: str, step: int | None = None, instruction: str | None = None, target_role: str | None = None, planner_agent: Any = None, runtime_config: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_command = command.strip().lower()
    valid_commands = {"approve_outline", "revise_outline", "rollback", "inject_instruction", "pause", "resume", "cut"}
    if normalized_command not in valid_commands:
        raise ValueError(f"不支持的导演指令: {command}")

    if normalized_command == "pause":
        session.status = "paused"
        return {"status": "paused"}

    if normalized_command == "resume":
        session.status = "running"
        return {"status": "running"}

    if normalized_command == "cut":
        commit_system_event(
            session.runtime_state,
            kind="director",
            speaker="DIRECTOR",
            content="导演主动切断当前集。",
            visible_to=[],
        )
        return session.finalize("director_cut", session.current_speaker)

    if normalized_command == "inject_instruction":
        if not instruction:
            raise ValueError("inject_instruction 需要 instruction")
        if target_role:
            session.pending_role_instructions[target_role] = instruction
        else:
            session.pending_scene_instruction = instruction
        return {
            "status": "instruction_injected",
            "target_role": target_role,
            "instruction": instruction,
        }

    if normalized_command == "rollback":
        if step is None or step not in session.snapshots:
            raise ValueError(f"step={step} 不存在，无法回档")
        snapshot = session.snapshots[step]
        session.runtime_state = copy.deepcopy(snapshot.runtime_state)
        session.current_speaker = snapshot.current_speaker
        session.turn_trace = copy.deepcopy(snapshot.turn_trace)
        session.pending_scene_instruction = snapshot.pending_scene_instruction
        session.pending_monitor_instruction = snapshot.pending_monitor_instruction
        session.pending_role_instructions = dict(snapshot.pending_role_instructions)
        session.status = snapshot.status
        session.result = None
        truncate_episode_log(session.log_path, keep_turns=step)
        for stale_step in list(session.snapshots.keys()):
            if stale_step > step:
                del session.snapshots[stale_step]
        return {
            "status": "rolled_back",
            "current_turn": session.runtime_state.story.current_turn,
            "current_speaker": session.current_speaker,
        }

    if normalized_command == "revise_outline":
        if planner_agent is None or runtime_config is None or not instruction:
            raise ValueError("revise_outline 需要 planner_agent、runtime_config 和 instruction")
        if session.planner_review_state is None:
            session.planner_review_state = PlannerReviewState(planner_output={"episodes": [session.episode_plan]})
        revised = revise_planner_outline(session.planner_review_state, planner_agent, runtime_config, instruction)
        return {"status": "outline_revised", "planner_output": revised}

    if normalized_command == "approve_outline":
        if session.planner_review_state is None:
            raise ValueError("当前没有待审批的大纲")
        planner_output = approve_planner_outline(session.planner_review_state)
        session.episode_plan = planner_output["episodes"][session.runtime_state.story.current_episode - 1]
        session.approved_outline = True
        return {"status": "outline_approved", "planner_output": planner_output}

    raise ValueError(f"暂未实现的导演指令: {command}")


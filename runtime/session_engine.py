# 该文件实现单集/整季运行时主循环，以及可供导演干预的 session。
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from Agent_model import Planner_Agent, Role_Agent_Box, Summary_Agent, load_env
from context_builder import build_role_context
from episode_beats import (
    build_controller_instruction,
    can_end_current_episode,
    create_beat_state,
    maybe_advance_beat,
)
from event_committer import commit_system_event, commit_turn_result, finalize_role_memories_for_next_episode
from formatter_agent import export_artifacts
from input_adapter import build_free_mode_planner_output
from log_writer import (
    append_turn_log,
    finalize_episode_log,
    initialize_episode_log,
    initialize_season_log_directory,
    serialize_role_memories,
    serialize_season_context,
    truncate_episode_log,
    write_episode_checkpoint,
    write_season_context,
    write_season_summary,
)
from monitor_agent import MonitorDecision
from planner_review import PlannerReviewState, approve_planner_outline, revise_planner_outline
from prompt import build_planner_agent_prompt
from scheduler import END_SIGNAL, extract_next_speakers, resolve_next_speaker, resolve_next_speakers
from story_state import (
    INTERACTION_MODE_PENDING_REPLIES,
    InteractionState,
    RoleMemory,
    RunMode,
    RuntimeState,
    create_runtime_state,
    create_season_context,
    get_episode_plan,
    reset_interaction_state,
    update_season_context,
)
from runtime.director_commands import apply_director_command as apply_director_command_impl
from runtime.turn_executor import execute_next_turn

SEASON_CONTINUE_STATUSES = {"ended", "handoff", "max_turns_reached", "director_cut"}
VALID_DIRECTOR_COMMANDS = {
    "approve_outline",
    "revise_outline",
    "rollback",
    "inject_instruction",
    "pause",
    "resume",
    "cut",
}
DEBUG_ROLE_IO_ENABLED = os.getenv("DEBUG_ROLE_IO_ENABLED", "1").strip().lower() not in {"0", "false", "off"}
DEBUG_ROLE_IO_FULL = os.getenv("DEBUG_ROLE_IO_FULL", "0").strip().lower() in {"1", "true", "on"}
DEBUG_ROLE_IO_PREVIEW_CHARS = max(200, int(os.getenv("DEBUG_ROLE_IO_PREVIEW_CHARS", "1200")))


from runtime.engine_helpers import (
    choose_trigger_event_id,
    derive_turn_limits,
    generate_role_turn_with_route_retry,
    log_role_io,
    normalize_invalid_route_for_prompt,
    resolve_episode_start_speaker,
    should_use_fallback_history,
)

from runtime.runners import (
    SEASON_CONTINUE_STATUSES,
    build_episode_checkpoint_payload,
    build_season_summary,
    is_episode_success_status,
)

@dataclass
class EpisodeSnapshot:
    """单集运行快照，用于回档。"""

    runtime_state: RuntimeState
    current_speaker: str
    turn_trace: list[dict[str, Any]]
    pending_scene_instruction: str | None
    pending_monitor_instruction: str | None
    pending_role_instructions: dict[str, str]
    status: str


@dataclass
class EpisodeSession:
    """支持导演命令的单集运行 session。"""

    runtime_state: RuntimeState
    episode_plan: dict[str, Any]
    role_agent_box: Role_Agent_Box
    summary_agent: Summary_Agent | None = None
    monitor_agent: Any = None
    current_speaker: str = ""
    tail_window: int = 4
    fallback_history_window: int = 6
    max_turns: int = 8
    soft_turn_limit: int = 0
    hard_turn_limit: int | None = None
    log_dir: str = "log"
    run_mode: RunMode = "planned"
    valid_roles: list[str] = field(default_factory=list)
    turn_trace: list[dict[str, Any]] = field(default_factory=list)
    log_path: Path | None = None
    status: str = "ready"
    result: dict[str, Any] | None = None
    pending_scene_instruction: str | None = None
    pending_monitor_instruction: str | None = None
    pending_role_instructions: dict[str, str] = field(default_factory=dict)
    snapshots: dict[int, EpisodeSnapshot] = field(default_factory=dict)
    planner_review_state: PlannerReviewState | None = None
    approved_outline: bool = True
    monitor_interval: int = 4

    def __post_init__(self) -> None:
        if not self.valid_roles:
            self.valid_roles = list(self.runtime_state.role_memories.keys())
        if self.soft_turn_limit <= 0:
            self.soft_turn_limit, self.hard_turn_limit = derive_turn_limits(self.max_turns)
        elif self.hard_turn_limit is not None and self.hard_turn_limit <= 0:
            _, self.hard_turn_limit = derive_turn_limits(self.soft_turn_limit)
        if not self.current_speaker:
            self.current_speaker = resolve_episode_start_speaker(self.episode_plan, self.valid_roles)
        if not self.runtime_state.beat_state.beats:
            self.runtime_state.beat_state = create_beat_state(self.episode_plan)
        if self.log_path is None:
            self.log_path = initialize_episode_log(self.runtime_state, self.episode_plan, log_dir=self.log_dir)
        self._save_snapshot()

    def _save_snapshot(self) -> None:
        """保存当前 turn 对应的回档快照。"""
        step = self.runtime_state.story.current_turn
        self.snapshots[step] = EpisodeSnapshot(
            runtime_state=copy.deepcopy(self.runtime_state),
            current_speaker=self.current_speaker,
            turn_trace=copy.deepcopy(self.turn_trace),
            pending_scene_instruction=self.pending_scene_instruction,
            pending_monitor_instruction=self.pending_monitor_instruction,
            pending_role_instructions=dict(self.pending_role_instructions),
            status=self.status,
        )

    def _clear_one_shot_instructions(self, speaker: str) -> tuple[str | None, str | None, str | None]:
        """消费当前 speaker 本轮需要使用的一次性指令。"""
        scene_instruction = self.pending_scene_instruction
        role_instruction = self.pending_role_instructions.pop(speaker, None)
        monitor_instruction = self.pending_monitor_instruction
        self.pending_scene_instruction = None
        self.pending_monitor_instruction = None
        return scene_instruction, role_instruction, monitor_instruction

    def _build_result(self, result_status: str, last_speaker: str, summary_status: dict[str, str]) -> dict[str, Any]:
        """统一整理单集运行结果。"""
        return {
            "status": result_status,
            "runtime_state": self.runtime_state,
            "last_speaker": last_speaker,
            "turn_trace": self.turn_trace,
            "summary_status": summary_status,
            "soft_turn_limit": self.soft_turn_limit,
            "hard_turn_limit": self.hard_turn_limit,
            "exports": export_artifacts(self.runtime_state, self.episode_plan),
        }

    def _append_beat_progress_event(self, extra_events: list[Any]) -> None:
        """Advance runtime beats using the soft turn budget and log controller progress."""
        advanced_beat = maybe_advance_beat(self.runtime_state, self.soft_turn_limit)
        if advanced_beat is None:
            return
        extra_events.append(
            commit_system_event(
                self.runtime_state,
                kind="system",
                speaker="BEAT_CONTROLLER",
                content=f"Beat advanced to {advanced_beat.label}: {advanced_beat.must_land}",
                visible_to=[],
            )
        )

    def finalize(self, result_status: str, last_speaker: str) -> dict[str, Any]:
        """统一处理 episode 收尾日志与跨集记忆回写。"""
        
        if self.result is not None:
            return self.result
        summary_status = finalize_role_memories_for_next_episode(
            self.runtime_state,
            self.summary_agent,
            fallback_history_window=self.fallback_history_window,
        )
        finalize_episode_log(
            self.log_path,
            runtime_state=self.runtime_state,
            result_status=result_status,
            last_speaker=last_speaker,
            total_turns=self.runtime_state.story.current_turn,
            summary_status=summary_status,
        )
        self.status = result_status
        self.result = self._build_result(result_status, last_speaker, summary_status)
        return self.result

    def _advance_pending_queue(self, speaker: str) -> str:
        """推进多人回应队列。"""
        interaction = self.runtime_state.interaction
        if interaction.pending_queue and interaction.pending_queue[0] == speaker:
            interaction.pending_queue.pop(0)
        if interaction.pending_queue:
            return interaction.pending_queue[0]

        initiator = interaction.initiator or self.current_speaker
        reset_interaction_state(self.runtime_state)
        return initiator

    def _maybe_review_monitor(self) -> list[Any]:
        """按固定间隔触发监制检查。"""
        if self.monitor_agent is None:
            return []
        if self.runtime_state.story.current_turn <= 0:
            return []
        if self.runtime_state.story.current_turn % self.monitor_interval != 0:
            return []

        decision: MonitorDecision = self.monitor_agent.review(self.runtime_state, self.episode_plan)
        monitor_events: list[Any] = []
        if decision.decision == "suggestion" and decision.suggestion:
            self.pending_monitor_instruction = decision.suggestion
            monitor_events.append(
                commit_system_event(
                    self.runtime_state,
                    kind="monitor",
                    speaker="MONITOR",
                    content=decision.suggestion,
                    visible_to=[],
                )
            )
        elif decision.decision == "cut":
            monitor_events.append(
                commit_system_event(
                    self.runtime_state,
                    kind="monitor",
                    speaker="MONITOR",
                    content=decision.reason or "监制判断当前集应立即结束。",
                    visible_to=[],
                )
            )
            self.finalize("director_cut", self.current_speaker)
        return monitor_events

    def apply_director_command(
        self,
        command: str,
        step: int | None = None,
        instruction: str | None = None,
        target_role: str | None = None,
        planner_agent: Planner_Agent | None = None,
        runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return apply_director_command_impl(
            self,
            command=command,
            step=step,
            instruction=instruction,
            target_role=target_role,
            planner_agent=planner_agent,
            runtime_config=runtime_config,
        )

    def run_next_turn(self) -> dict[str, Any]:
        return execute_next_turn(self)

    def run_until_stop(self) -> dict[str, Any]:
        """持续推进直到结束、暂停或达到轮数上限。"""
        while self.result is None and self.status != "paused":
            step_result = self.run_next_turn()
            if step_result.get("status") == "paused":
                return step_result
            if self.result is not None:
                return self.result
        if self.result is not None:
            return self.result
        return {"status": self.status, "current_turn": self.runtime_state.story.current_turn}


def create_episode_session(
    planner_output: dict[str, Any],
    role_agent_box: Role_Agent_Box,
    episode: int,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    previous_role_memories: dict[str, RoleMemory] | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> EpisodeSession:
    """创建支持导演干预的单集运行 session。"""
    runtime_state = create_runtime_state(
        runtime_config,
        planner_output,
        episode,
        previous_role_memories=previous_role_memories,
    )
    episode_plan = get_episode_plan(planner_output, episode)
    valid_roles = list(runtime_config["character_roster"].keys())
    soft_turn_limit, hard_turn_limit = derive_turn_limits(max_turns)
    return EpisodeSession(
        runtime_state=runtime_state,
        episode_plan=episode_plan,
        role_agent_box=role_agent_box,
        summary_agent=summary_agent,
        monitor_agent=monitor_agent,
        current_speaker=resolve_episode_start_speaker(episode_plan, valid_roles),
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        soft_turn_limit=soft_turn_limit,
        hard_turn_limit=hard_turn_limit,
        log_dir=log_dir,
        run_mode=run_mode,
        valid_roles=valid_roles,
    )


def run_episode(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    episode: int,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    previous_role_memories: dict[str, RoleMemory] | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> dict:
    from runtime.runners import run_episode as _impl

    return _impl(
        planner_output,
        role_agent_box,
        episode,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
        previous_role_memories=previous_role_memories,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
        run_mode=run_mode,
    )


def run_free_episode(
    role_agent_box: Role_Agent_Box,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    opening_scene: str | None = None,
    scene_roles: list[str] | None = None,
    story_hook: str | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
) -> dict:
    from runtime.runners import run_free_episode as _impl

    return _impl(
        role_agent_box,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
        opening_scene=opening_scene,
        scene_roles=scene_roles,
        story_hook=story_hook,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
    )


def run_season(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    start_episode: int = 1,
    continuity_enabled: bool = True,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> dict:
    from runtime.runners import run_season as _impl

    return _impl(
        planner_output,
        role_agent_box,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
        start_episode=start_episode,
        continuity_enabled=continuity_enabled,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
        run_mode=run_mode,
    )


def run_demo_episode(runtime_config: dict[str, Any], episode: int = 1) -> dict:
    from runtime.runners import run_demo_episode as _impl

    return _impl(runtime_config, episode=episode)


if __name__ == "__main__":
    raise SystemExit("run_demo_episode now requires an explicit runtime_config argument.")

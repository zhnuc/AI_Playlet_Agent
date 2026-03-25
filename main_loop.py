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
from global_config import global_config
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
from prompt import planner_agent_prompt
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


def _preview_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)]}..."


def _trim_turn_output_for_debug(turn_output: dict[str, Any], limit: int) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    for key in ("Inner_Thought", "Action", "Dialogue"):
        value = turn_output.get(key, "")
        trimmed[key] = _preview_text(str(value), limit)
    trimmed["next_speaker"] = turn_output.get("next_speaker")
    trimmed["next_speakers"] = list(turn_output.get("next_speakers", []))
    if isinstance(turn_output.get("__meta"), dict):
        trimmed["__meta"] = dict(turn_output["__meta"])
    return trimmed


def log_role_io(
    speaker: str,
    status: str,
    prompt: str,
    turn_output: dict[str, Any] | None,
    perf_payload: dict[str, Any],
) -> None:
    if not DEBUG_ROLE_IO_ENABLED:
        return

    print(
        f"[DEBUG][ROLE_IO][speaker={speaker}] status={status} "
        f"prompt_chars={len(prompt)} attempts={perf_payload.get('attempt_count', 0)}"
    )
    prompt_body = prompt if DEBUG_ROLE_IO_FULL else _preview_text(prompt, DEBUG_ROLE_IO_PREVIEW_CHARS)
    print(f"[DEBUG][ROLE_IO][speaker={speaker}][prompt]\n{prompt_body}")
    if isinstance(turn_output, dict):
        output_payload = turn_output if DEBUG_ROLE_IO_FULL else _trim_turn_output_for_debug(
            turn_output,
            DEBUG_ROLE_IO_PREVIEW_CHARS // 3,
        )
        print(
            f"[DEBUG][ROLE_IO][speaker={speaker}][output]\n"
            f"{json.dumps(output_payload, ensure_ascii=False, indent=2)}"
        )
    else:
        print(f"[DEBUG][ROLE_IO][speaker={speaker}][output] null")


def derive_turn_limits(max_turns: int) -> tuple[int, int | None]:
    """Treat max_turns as soft pacing budget only; hard cap is disabled by default."""
    resolved_soft_limit = max(1, int(max_turns))
    return resolved_soft_limit, None


def should_use_fallback_history(role_memory: RoleMemory) -> bool:
    """判断当前角色是否应自动进入跨集 fallback prompt。"""
    return (
        not role_memory.carryover_summary.strip()
        and bool(role_memory.carryover_event_tail)
        and not role_memory.private_history
    )


def is_episode_success_status(status: str) -> bool:
    """判断单集状态是否允许 season 继续执行下一集。"""
    return status in SEASON_CONTINUE_STATUSES


def build_episode_checkpoint_payload(
    run_id: str,
    episode: int,
    total_episode_count: int,
    final_role_memories: dict[str, RoleMemory],
    season_context_payload: dict,
) -> dict:
    """构造单集结束后的 checkpoint 内容。"""
    remaining_episode_numbers = list(range(episode + 1, total_episode_count + 1))
    serialized_role_memories = serialize_role_memories(final_role_memories)
    return {
        "run_id": run_id,
        "completed_episode": episode,
        "planner_baseline_ref": "planner_output.json",
        "role_memories": serialized_role_memories,
        "completed_episode_numbers": list(season_context_payload["completed_episode_numbers"]),
        "season_stats": dict(season_context_payload["season_stats"]),
        "remaining_episode_numbers": remaining_episode_numbers,
        "replan_context_stub": {
            "completed_episode": episode,
            "remaining_episode_count": len(remaining_episode_numbers),
            "carryover_role_memories": serialized_role_memories,
        },
    }


def build_season_summary(
    run_id: str,
    total_episode_count: int,
    stop_reason: str | None,
    season_context_payload: dict,
) -> dict:
    """基于 SeasonContext 汇总当前整季运行结果。"""
    season_stats = dict(season_context_payload["season_stats"])
    return {
        "run_id": run_id,
        "planner_baseline_ref": "planner_output.json",
        "planned_episode_count": total_episode_count,
        "completed_episode_numbers": list(season_context_payload["completed_episode_numbers"]),
        "completed_episode_count": season_stats["completed_episode_count"],
        "successful_episode_count": season_stats["successful_episode_count"],
        "failed_episode_count": season_stats["failed_episode_count"],
        "episode_status_map": dict(season_stats["episode_status_map"]),
        "episode_status_counts": dict(season_stats["episode_status_counts"]),
        "total_turns": season_stats["total_turns"],
        "average_turns_per_episode": season_stats["average_turns_per_episode"],
        "summary_status_counts": dict(season_stats["summary_status_counts"]),
        "completed_all_planned_episodes": season_stats["completed_all_planned_episodes"],
        "stop_reason": stop_reason,
    }


def resolve_episode_start_speaker(episode_plan: dict, valid_roles: list[str]) -> str:
    """将 planner 给出的首发角色收敛到当前场景的合法发言者。"""
    first_speaker = (episode_plan.get("first_speaker") or "").strip()
    scene_roles = [role for role in episode_plan.get("scene_roles", []) if role in valid_roles]

    if first_speaker and first_speaker in scene_roles:
        return first_speaker
    if scene_roles:
        return scene_roles[0]
    if valid_roles:
        return valid_roles[0]
    raise ValueError("当前没有可用的合法首发角色")


def choose_trigger_event_id(runtime_state: RuntimeState, committed_events: list[Any]) -> str | None:
    """为多人回应队列选择触发事件。"""
    preferred_kinds = ("dialogue", "action")
    for preferred_kind in preferred_kinds:
        for event in reversed(committed_events):
            if event.kind == preferred_kind:
                return event.event_id
    if committed_events:
        return committed_events[-1].event_id
    if runtime_state.story.event_log:
        return runtime_state.story.event_log[-1].event_id
    return None


def normalize_invalid_route_for_prompt(turn_output: dict[str, Any]) -> str:
    """将非法路由提议整理为 prompt 中可阅读的重试提示。"""
    next_speakers = extract_next_speakers(turn_output)
    if not next_speakers:
        return "空列表"
    return ",".join(next_speakers)


def generate_role_turn_with_route_retry(
    current_speaker: str,
    runtime_state: RuntimeState,
    episode_plan: dict,
    role_agent_box: Role_Agent_Box,
    valid_roles: list[str],
    tail_window: int,
    fallback_history_window: int,
    scene_instruction: str | None = None,
    role_instruction: str | None = None,
    monitor_instruction: str | None = None,
    controller_instruction: str | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
    ignore_route: bool = False,
) -> dict[str, object]:
    """调用角色 agent，并在路由非法时最多重试一次。"""
    use_fallback_history = should_use_fallback_history(runtime_state.role_memories[current_speaker])
    invalid_next_speaker: str | None = None
    retry_count = 0
    prompt = ""
    final_turn_output: dict | None = None
    model_elapsed_ms_list: list[float] = []

    for attempt in range(2):
        prompt = build_role_context(
            current_speaker,
            runtime_state,
            episode_plan,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
            use_fallback_history=use_fallback_history,
            retry_invalid_next_speaker=invalid_next_speaker,
            scene_instruction=scene_instruction,
            role_instruction=role_instruction,
            monitor_instruction=monitor_instruction,
            controller_instruction=controller_instruction,
            soft_turn_limit=soft_turn_limit,
            hard_turn_limit=hard_turn_limit,
        )
        turn_output = role_agent_box.generate_role_response(current_speaker, prompt)
        if isinstance(turn_output, str):
            return {
                "status": turn_output,
                "turn_output": None,
                "prompt": prompt,
                "use_fallback_history": use_fallback_history,
                "retry_count": retry_count,
                "invalid_next_speaker": invalid_next_speaker,
                "model_elapsed_ms_list": model_elapsed_ms_list,
            }

        if isinstance(turn_output.get("__meta"), dict):
            model_elapsed = turn_output["__meta"].get("model_elapsed_ms")
            if isinstance(model_elapsed, (int, float)):
                model_elapsed_ms_list.append(float(model_elapsed))
        next_speakers = extract_next_speakers(turn_output)
        turn_output["next_speakers"] = next_speakers
        turn_output["next_speaker"] = next_speakers[0] if len(next_speakers) == 1 else None
        final_turn_output = turn_output

        if ignore_route:
            return {
                "status": "ok",
                "turn_output": turn_output,
                "prompt": prompt,
                "use_fallback_history": use_fallback_history,
                "retry_count": retry_count,
                "invalid_next_speaker": None,
                "model_elapsed_ms_list": model_elapsed_ms_list,
            }

        if resolve_next_speakers(
            current_speaker,
            next_speakers,
            runtime_state.story.scene_roles,
            valid_roles,
        ) is not None:
            return {
                "status": "ok",
                "turn_output": turn_output,
                "prompt": prompt,
                "use_fallback_history": use_fallback_history,
                "retry_count": retry_count,
                "invalid_next_speaker": None,
                "model_elapsed_ms_list": model_elapsed_ms_list,
            }

        invalid_next_speaker = normalize_invalid_route_for_prompt(turn_output)
        if attempt == 0:
            retry_count = 1

    return {
        "status": "handoff",
        "turn_output": final_turn_output,
        "prompt": prompt,
        "use_fallback_history": use_fallback_history,
        "retry_count": retry_count,
        "invalid_next_speaker": invalid_next_speaker,
        "model_elapsed_ms_list": model_elapsed_ms_list,
    }


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
            self.valid_roles = list(global_config["character_roster"].keys())
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
        """执行导演指令。"""
        normalized_command = command.strip().lower()
        if normalized_command not in VALID_DIRECTOR_COMMANDS:
            raise ValueError(f"不支持的导演指令: {command}")

        if normalized_command == "pause":
            self.status = "paused"
            return {"status": "paused"}

        if normalized_command == "resume":
            self.status = "running"
            return {"status": "running"}

        if normalized_command == "cut":
            commit_system_event(
                self.runtime_state,
                kind="director",
                speaker="DIRECTOR",
                content="导演主动切断当前集。",
                visible_to=[],
            )
            return self.finalize("director_cut", self.current_speaker)

        if normalized_command == "inject_instruction":
            if not instruction:
                raise ValueError("inject_instruction 需要 instruction")
            if target_role:
                self.pending_role_instructions[target_role] = instruction
            else:
                self.pending_scene_instruction = instruction
            return {
                "status": "instruction_injected",
                "target_role": target_role,
                "instruction": instruction,
            }

        if normalized_command == "rollback":
            if step is None or step not in self.snapshots:
                raise ValueError(f"step={step} 不存在，无法回档")
            snapshot = self.snapshots[step]
            self.runtime_state = copy.deepcopy(snapshot.runtime_state)
            self.current_speaker = snapshot.current_speaker
            self.turn_trace = copy.deepcopy(snapshot.turn_trace)
            self.pending_scene_instruction = snapshot.pending_scene_instruction
            self.pending_monitor_instruction = snapshot.pending_monitor_instruction
            self.pending_role_instructions = dict(snapshot.pending_role_instructions)
            self.status = snapshot.status
            self.result = None
            truncate_episode_log(self.log_path, keep_turns=step)
            for stale_step in list(self.snapshots.keys()):
                if stale_step > step:
                    del self.snapshots[stale_step]
            return {
                "status": "rolled_back",
                "current_turn": self.runtime_state.story.current_turn,
                "current_speaker": self.current_speaker,
            }

        if normalized_command == "revise_outline":
            if planner_agent is None or runtime_config is None or not instruction:
                raise ValueError("revise_outline 需要 planner_agent、runtime_config 和 instruction")
            if self.planner_review_state is None:
                self.planner_review_state = PlannerReviewState(planner_output={"episodes": [self.episode_plan]})
            revised = revise_planner_outline(self.planner_review_state, planner_agent, runtime_config, instruction)
            return {"status": "outline_revised", "planner_output": revised}

        if normalized_command == "approve_outline":
            if self.planner_review_state is None:
                raise ValueError("当前没有待审批的大纲")
            planner_output = approve_planner_outline(self.planner_review_state)
            self.episode_plan = planner_output["episodes"][self.runtime_state.story.current_episode - 1]
            self.approved_outline = True
            return {"status": "outline_approved", "planner_output": planner_output}

        raise ValueError(f"暂未实现的导演指令: {command}")

    def run_next_turn(self) -> dict[str, Any]:
        """推进单个角色的一轮输出。"""
        if self.result is not None:
            return self.result
        turn_started_at = perf_counter()
        if self.status == "paused":
            return {"status": "paused", "current_turn": self.runtime_state.story.current_turn}
        ignore_route = (
            self.runtime_state.interaction.mode == INTERACTION_MODE_PENDING_REPLIES
            and self.current_speaker != self.runtime_state.interaction.initiator
        )
        scene_instruction, role_instruction, monitor_instruction = self._clear_one_shot_instructions(self.current_speaker)
        controller_instruction = build_controller_instruction(
            self.runtime_state,
            soft_turn_limit=self.soft_turn_limit,
            hard_turn_limit=self.hard_turn_limit,
        )
        turn_result = generate_role_turn_with_route_retry(
            self.current_speaker,
            self.runtime_state,
            self.episode_plan,
            self.role_agent_box,
            self.valid_roles,
            self.tail_window,
            self.fallback_history_window,
            scene_instruction=scene_instruction,
            role_instruction=role_instruction,
            monitor_instruction=monitor_instruction,
            controller_instruction=controller_instruction,
            soft_turn_limit=self.soft_turn_limit,
            hard_turn_limit=self.hard_turn_limit,
            ignore_route=ignore_route,
        )

        prompt = str(turn_result["prompt"])
        use_fallback_history = bool(turn_result["use_fallback_history"])
        status = str(turn_result["status"])
        model_elapsed_ms_list = [
            float(item)
            for item in turn_result.get("model_elapsed_ms_list", [])
            if isinstance(item, (int, float))
        ]
        perf_payload = {
            "attempt_count": len(model_elapsed_ms_list),
            "route_retry_count": int(turn_result.get("retry_count", 0)),
            "prompt_chars": len(prompt),
            "model_elapsed_ms_list": model_elapsed_ms_list,
            "model_elapsed_ms_total": round(sum(model_elapsed_ms_list), 1),
        }
        if status in {"api_error", "format_error", "key_error"}:
            perf_payload["step_elapsed_ms"] = round((perf_counter() - turn_started_at) * 1000, 1)
            log_role_io(
                self.current_speaker,
                status=status,
                prompt=prompt,
                turn_output=turn_result.get("turn_output") if isinstance(turn_result.get("turn_output"), dict) else None,
                perf_payload=perf_payload,
            )
            print(
                f"[PERF][STEP][speaker={self.current_speaker}] status={status} "
                f"step_ms={perf_payload['step_elapsed_ms']} model_ms={perf_payload['model_elapsed_ms_total']} "
                f"attempts={perf_payload['attempt_count']} prompt_chars={perf_payload['prompt_chars']}"
            )
            return self.finalize(status, self.current_speaker)

        turn_output = turn_result["turn_output"]
        if not isinstance(turn_output, dict):
            return self.finalize("api_error", self.current_speaker)
        log_role_io(
            self.current_speaker,
            status=status,
            prompt=prompt,
            turn_output=turn_output,
            perf_payload=perf_payload,
        )

        proposed_next_speakers = list(turn_output.get("next_speakers", []))

        if status == "handoff" and not ignore_route:
            return self.finalize("handoff", self.current_speaker)

        committed_events = commit_turn_result(self.runtime_state, self.current_speaker, turn_output)
        extra_events: list[Any] = []
        maybe_advance_beat(self.runtime_state, self.soft_turn_limit)

        if proposed_next_speakers == [END_SIGNAL] and can_end_current_episode(self.runtime_state):
            append_turn_log(
                self.log_path,
                runtime_state=self.runtime_state,
                step=self.runtime_state.story.current_turn,
                speaker=self.current_speaker,
                prompt=prompt,
                use_fallback_history=use_fallback_history,
                turn_output=turn_output,
                committed_events=committed_events,
                proposed_next_speaker=proposed_next_speakers,
                resolved_next_speaker=END_SIGNAL,
                status="ended",
                extra_events=extra_events,
                perf={
                    **perf_payload,
                    "step_elapsed_ms": round((perf_counter() - turn_started_at) * 1000, 1),
                },
            )
            self.turn_trace.append(
                {
                    "step": self.runtime_state.story.current_turn,
                    "speaker": self.current_speaker,
                    "proposed_next_speakers": proposed_next_speakers,
                    "resolved_next_speaker": END_SIGNAL,
                    "route_retry_count": turn_result["retry_count"],
                    "status": "ended",
                }
            )
            self._save_snapshot()
            return self.finalize("ended", self.current_speaker)
        if proposed_next_speakers == [END_SIGNAL]:
            proposed_next_speakers = []
            turn_output["next_speakers"] = []
            turn_output["next_speaker"] = None
        resolved_next_speaker: str | list[str] | None = None

        if ignore_route:
            resolved_next_speaker = self._advance_pending_queue(self.current_speaker)
            routing_status = "queue_continue"
        else:
            resolved_next_speakers = resolve_next_speakers(
                current_speaker=self.current_speaker,
                proposed_next_speakers=proposed_next_speakers,
                scene_roles=self.runtime_state.story.scene_roles,
                valid_roles=self.valid_roles,
            )
            if resolved_next_speakers is None:
                append_turn_log(
                    self.log_path,
                    runtime_state=self.runtime_state,
                    step=self.runtime_state.story.current_turn,
                    speaker=self.current_speaker,
                    prompt=prompt,
                    use_fallback_history=use_fallback_history,
                    turn_output=turn_output,
                    committed_events=committed_events,
                    proposed_next_speaker=proposed_next_speakers,
                    resolved_next_speaker=None,
                    status="handoff",
                    extra_events=extra_events,
                    perf={
                        **perf_payload,
                        "step_elapsed_ms": round((perf_counter() - turn_started_at) * 1000, 1),
                    },
                )
                self.turn_trace.append(
                    {
                        "step": self.runtime_state.story.current_turn,
                        "speaker": self.current_speaker,
                        "proposed_next_speakers": proposed_next_speakers,
                        "resolved_next_speaker": None,
                        "route_retry_count": turn_result["retry_count"],
                        "status": "handoff",
                    }
                )
                self._save_snapshot()
                return self.finalize("handoff", self.current_speaker)

            if len(resolved_next_speakers) > 1:
                self.runtime_state.interaction = InteractionState(
                    mode=INTERACTION_MODE_PENDING_REPLIES,
                    initiator=self.current_speaker,
                    pending_queue=list(resolved_next_speakers),
                    trigger_event_id=choose_trigger_event_id(self.runtime_state, committed_events),
                )
                resolved_next_speaker = resolved_next_speakers[0]
                routing_status = "queue_open"
            else:
                resolved_next_speaker = resolve_next_speaker(
                    current_speaker=self.current_speaker,
                    proposed_next_speaker=resolved_next_speakers,
                    scene_roles=self.runtime_state.story.scene_roles,
                    valid_roles=self.valid_roles,
                )
                routing_status = "continue" if resolved_next_speaker else "handoff"

        monitor_events = self._maybe_review_monitor()
        extra_events.extend(monitor_events)

        append_turn_log(
            self.log_path,
            runtime_state=self.runtime_state,
            step=self.runtime_state.story.current_turn,
            speaker=self.current_speaker,
            prompt=prompt,
            use_fallback_history=use_fallback_history,
            turn_output=turn_output,
            committed_events=committed_events,
            proposed_next_speaker=proposed_next_speakers,
            resolved_next_speaker=resolved_next_speaker,
            status=routing_status,
            extra_events=extra_events,
            perf={
                **perf_payload,
                "step_elapsed_ms": round((perf_counter() - turn_started_at) * 1000, 1),
            },
        )
        self.turn_trace.append(
            {
                "step": self.runtime_state.story.current_turn,
                "speaker": self.current_speaker,
                "proposed_next_speakers": proposed_next_speakers,
                "resolved_next_speaker": resolved_next_speaker,
                "route_retry_count": turn_result["retry_count"],
                "status": routing_status,
            }
        )
        step_elapsed_ms = round((perf_counter() - turn_started_at) * 1000, 1)
        print(
            f"[PERF][STEP][speaker={self.current_speaker}] status={routing_status} "
            f"step_ms={step_elapsed_ms} model_ms={perf_payload['model_elapsed_ms_total']} "
            f"attempts={perf_payload['attempt_count']} prompt_chars={perf_payload['prompt_chars']}"
        )

        if self.result is not None:
            return self.result
        if resolved_next_speaker is None:
            self._save_snapshot()
            return self.finalize("handoff", self.current_speaker)

        self.current_speaker = resolved_next_speaker if isinstance(resolved_next_speaker, str) else resolved_next_speaker[0]
        self.status = "running"
        self._save_snapshot()
        return {
            "status": "running",
            "current_turn": self.runtime_state.story.current_turn,
            "current_speaker": self.current_speaker,
        }

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
    runtime_config: dict[str, Any] | None = None,
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
    effective_runtime_config = runtime_config or global_config
    runtime_state = create_runtime_state(
        effective_runtime_config,
        planner_output,
        episode,
        previous_role_memories=previous_role_memories,
    )
    episode_plan = get_episode_plan(planner_output, episode)
    valid_roles = list(effective_runtime_config["character_roster"].keys())
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
    runtime_config: dict[str, Any] | None = None,
    summary_agent: Summary_Agent | None = None,
    previous_role_memories: dict[str, RoleMemory] | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> dict:
    """运行单集单场景的主循环。"""
    session = create_episode_session(
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
    return session.run_until_stop()


def run_free_episode(
    role_agent_box: Role_Agent_Box,
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
    """用 free mode 最小单集 planner 直接起跑。"""
    planner_output = build_free_mode_planner_output(
        global_config,
        opening_scene=opening_scene,
        scene_roles=scene_roles,
        story_hook=story_hook,
    )
    return run_episode(
        planner_output,
        role_agent_box,
        1,
        summary_agent=summary_agent,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
        run_mode="free",
    )


def run_season(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    runtime_config: dict[str, Any] | None = None,
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
    """按 planner 顺序连续运行多集，并默认承接上一集角色记忆。"""
    episodes = planner_output.get("episodes", [])
    total_episode_count = len(episodes)

    if start_episode <= 0 or start_episode > total_episode_count:
        raise ValueError(f"start_episode={start_episode} 不在 planner 输出范围内")

    episode_results: list[dict] = []
    previous_role_memories: dict[str, RoleMemory] | None = None
    final_role_memories: dict[str, RoleMemory] | None = None
    run_id, season_log_dir = initialize_season_log_directory(planner_output, log_dir=log_dir)
    season_context = create_season_context(planner_output, run_id)
    write_season_context(season_log_dir, season_context)

    for episode in range(start_episode, total_episode_count + 1):
        episode_result = run_episode(
            planner_output,
            role_agent_box,
            episode,
            runtime_config=runtime_config,
            summary_agent=summary_agent,
            previous_role_memories=previous_role_memories if continuity_enabled else None,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
            max_turns=max_turns,
            log_dir=str(season_log_dir),
            monitor_agent=monitor_agent,
            run_mode=run_mode,
        )
        season_episode_result = {"episode": episode, **episode_result}
        episode_results.append(season_episode_result)
        final_role_memories = episode_result["runtime_state"].role_memories
        episode_succeeded = is_episode_success_status(episode_result["status"])
        update_season_context(
            season_context,
            episode,
            episode_result["status"],
            total_turns=episode_result["runtime_state"].story.current_turn,
            summary_status=episode_result["summary_status"],
            episode_succeeded=episode_succeeded,
        )
        season_context_payload = serialize_season_context(season_context)
        checkpoint_payload = build_episode_checkpoint_payload(
            run_id,
            episode,
            total_episode_count,
            final_role_memories,
            season_context_payload,
        )
        checkpoint_path = write_episode_checkpoint(season_log_dir, episode, checkpoint_payload)
        season_context.checkpoint_index[str(episode)] = str(checkpoint_path.relative_to(season_log_dir))
        write_season_context(season_log_dir, season_context)

        if not episode_succeeded:
            season_context_payload = serialize_season_context(season_context)
            season_summary = build_season_summary(
                run_id,
                total_episode_count,
                stop_reason=episode_result["status"],
                season_context_payload=season_context_payload,
            )
            write_season_summary(season_log_dir, season_summary)
            return {
                "status": "stopped",
                "stop_reason": episode_result["status"],
                "run_id": run_id,
                "season_log_dir": str(season_log_dir),
                "season_context": season_context_payload,
                "season_summary": season_summary,
                "start_episode": start_episode,
                "planned_episode_count": total_episode_count,
                "completed_episode_count": len(episode_results),
                "completed_episode_numbers": [result["episode"] for result in episode_results],
                "episode_results": episode_results,
                "final_role_memories": final_role_memories,
            }

        previous_role_memories = final_role_memories

    season_context_payload = serialize_season_context(season_context)
    season_summary = build_season_summary(
        run_id,
        total_episode_count,
        stop_reason=None,
        season_context_payload=season_context_payload,
    )
    write_season_summary(season_log_dir, season_summary)
    return {
        "status": "completed",
        "stop_reason": None,
        "run_id": run_id,
        "season_log_dir": str(season_log_dir),
        "season_context": season_context_payload,
        "season_summary": season_summary,
        "start_episode": start_episode,
        "planned_episode_count": total_episode_count,
        "completed_episode_count": len(episode_results),
        "completed_episode_numbers": [result["episode"] for result in episode_results],
        "episode_results": episode_results,
        "final_role_memories": final_role_memories or {},
    }


def run_demo_episode(episode: int = 1) -> dict:
    """用真实模型调用跑通单集 demo。"""
    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    planner_output = planner_agent.generate_outline(planner_agent_prompt)
    if isinstance(planner_output, str):
        return {"status": planner_output}

    role_agent_box = Role_Agent_Box(base_url, api_key, model)
    summary_agent = Summary_Agent(base_url, api_key, model)
    return run_episode(planner_output, role_agent_box, episode, summary_agent=summary_agent)


if __name__ == "__main__":
    print(run_demo_episode())

from __future__ import annotations

import json
import os
from typing import Any

from Agent_model import Role_Agent_Box
from context_builder import build_role_context
from scheduler import extract_next_speakers
from story_state import RoleMemory, RunMode, RuntimeState

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
    resolved_soft_limit = max(1, int(max_turns))
    return resolved_soft_limit, None


def should_use_fallback_history(role_memory: RoleMemory) -> bool:
    return (
        not role_memory.carryover_summary.strip()
        and bool(role_memory.carryover_event_tail)
        and not role_memory.private_history
    )


def resolve_episode_start_speaker(episode_plan: dict, valid_roles: list[str]) -> str:
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
    run_mode: RunMode = "planned",
    ignore_route: bool = False,
) -> dict[str, object]:
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
            run_mode=run_mode,
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

        from scheduler import resolve_next_speakers

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


from __future__ import annotations

from time import perf_counter
from typing import Any

from episode_beats import build_controller_instruction, can_end_current_episode, maybe_advance_beat
from event_committer import commit_turn_result
from log_writer import append_turn_log
from scheduler import END_SIGNAL, resolve_next_speaker, resolve_next_speakers
from story_state import INTERACTION_MODE_PENDING_REPLIES, InteractionState
from runtime.engine_helpers import (
    choose_trigger_event_id,
    generate_role_turn_with_route_retry,
    log_role_io,
)


def execute_next_turn(session: Any) -> dict[str, Any]:
    if session.result is not None:
        return session.result
    turn_started_at = perf_counter()
    if session.status == "paused":
        return {"status": "paused", "current_turn": session.runtime_state.story.current_turn}
    ignore_route = (
        session.runtime_state.interaction.mode == INTERACTION_MODE_PENDING_REPLIES
        and session.current_speaker != session.runtime_state.interaction.initiator
    )
    scene_instruction, role_instruction, monitor_instruction = session._clear_one_shot_instructions(session.current_speaker)
    controller_instruction = build_controller_instruction(
        session.runtime_state,
        soft_turn_limit=session.soft_turn_limit,
        hard_turn_limit=session.hard_turn_limit,
    )
    turn_result = generate_role_turn_with_route_retry(
        session.current_speaker,
        session.runtime_state,
        session.episode_plan,
        session.role_agent_box,
        session.valid_roles,
        session.tail_window,
        session.fallback_history_window,
        scene_instruction=scene_instruction,
        role_instruction=role_instruction,
        monitor_instruction=monitor_instruction,
        controller_instruction=controller_instruction,
        soft_turn_limit=session.soft_turn_limit,
        hard_turn_limit=session.hard_turn_limit,
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
            session.current_speaker,
            status=status,
            prompt=prompt,
            turn_output=turn_result.get("turn_output") if isinstance(turn_result.get("turn_output"), dict) else None,
            perf_payload=perf_payload,
        )
        print(
            f"[PERF][STEP][speaker={session.current_speaker}] status={status} "
            f"step_ms={perf_payload['step_elapsed_ms']} model_ms={perf_payload['model_elapsed_ms_total']} "
            f"attempts={perf_payload['attempt_count']} prompt_chars={perf_payload['prompt_chars']}"
        )
        return session.finalize(status, session.current_speaker)

    turn_output = turn_result["turn_output"]
    if not isinstance(turn_output, dict):
        return session.finalize("api_error", session.current_speaker)
    log_role_io(
        session.current_speaker,
        status=status,
        prompt=prompt,
        turn_output=turn_output,
        perf_payload=perf_payload,
    )

    proposed_next_speakers = list(turn_output.get("next_speakers", []))

    if status == "handoff" and not ignore_route:
        return session.finalize("handoff", session.current_speaker)

    committed_events = commit_turn_result(session.runtime_state, session.current_speaker, turn_output)
    extra_events: list[Any] = []
    maybe_advance_beat(session.runtime_state, session.soft_turn_limit)

    if proposed_next_speakers == [END_SIGNAL] and can_end_current_episode(session.runtime_state):
        append_turn_log(
            session.log_path,
            runtime_state=session.runtime_state,
            step=session.runtime_state.story.current_turn,
            speaker=session.current_speaker,
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
        session.turn_trace.append(
            {
                "step": session.runtime_state.story.current_turn,
                "speaker": session.current_speaker,
                "proposed_next_speakers": proposed_next_speakers,
                "resolved_next_speaker": END_SIGNAL,
                "route_retry_count": turn_result["retry_count"],
                "status": "ended",
            }
        )
        session._save_snapshot()
        return session.finalize("ended", session.current_speaker)
    if proposed_next_speakers == [END_SIGNAL]:
        proposed_next_speakers = []
        turn_output["next_speakers"] = []
        turn_output["next_speaker"] = None
    resolved_next_speaker: str | list[str] | None = None

    if ignore_route:
        resolved_next_speaker = session._advance_pending_queue(session.current_speaker)
        routing_status = "queue_continue"
    else:
        resolved_next_speakers = resolve_next_speakers(
            current_speaker=session.current_speaker,
            proposed_next_speakers=proposed_next_speakers,
            scene_roles=session.runtime_state.story.scene_roles,
            valid_roles=session.valid_roles,
        )
        if resolved_next_speakers is None:
            append_turn_log(
                session.log_path,
                runtime_state=session.runtime_state,
                step=session.runtime_state.story.current_turn,
                speaker=session.current_speaker,
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
            session.turn_trace.append(
                {
                    "step": session.runtime_state.story.current_turn,
                    "speaker": session.current_speaker,
                    "proposed_next_speakers": proposed_next_speakers,
                    "resolved_next_speaker": None,
                    "route_retry_count": turn_result["retry_count"],
                    "status": "handoff",
                }
            )
            session._save_snapshot()
            return session.finalize("handoff", session.current_speaker)

        if len(resolved_next_speakers) > 1:
            session.runtime_state.interaction = InteractionState(
                mode=INTERACTION_MODE_PENDING_REPLIES,
                initiator=session.current_speaker,
                pending_queue=list(resolved_next_speakers),
                trigger_event_id=choose_trigger_event_id(session.runtime_state, committed_events),
            )
            resolved_next_speaker = resolved_next_speakers[0]
            routing_status = "queue_open"
        else:
            resolved_next_speaker = resolve_next_speaker(
                current_speaker=session.current_speaker,
                proposed_next_speaker=resolved_next_speakers,
                scene_roles=session.runtime_state.story.scene_roles,
                valid_roles=session.valid_roles,
            )
            routing_status = "continue" if resolved_next_speaker else "handoff"

    monitor_events = session._maybe_review_monitor()
    extra_events.extend(monitor_events)

    append_turn_log(
        session.log_path,
        runtime_state=session.runtime_state,
        step=session.runtime_state.story.current_turn,
        speaker=session.current_speaker,
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
    session.turn_trace.append(
        {
            "step": session.runtime_state.story.current_turn,
            "speaker": session.current_speaker,
            "proposed_next_speakers": proposed_next_speakers,
            "resolved_next_speaker": resolved_next_speaker,
            "route_retry_count": turn_result["retry_count"],
            "status": routing_status,
        }
    )
    step_elapsed_ms = round((perf_counter() - turn_started_at) * 1000, 1)
    print(
        f"[PERF][STEP][speaker={session.current_speaker}] status={routing_status} "
        f"step_ms={step_elapsed_ms} model_ms={perf_payload['model_elapsed_ms_total']} "
        f"attempts={perf_payload['attempt_count']} prompt_chars={perf_payload['prompt_chars']}"
    )

    if session.result is not None:
        return session.result
    if resolved_next_speaker is None:
        session._save_snapshot()
        return session.finalize("handoff", session.current_speaker)

    session.current_speaker = resolved_next_speaker if isinstance(resolved_next_speaker, str) else resolved_next_speaker[0]
    session.status = "running"
    session._save_snapshot()
    return {
        "status": "running",
        "current_turn": session.runtime_state.story.current_turn,
        "current_speaker": session.current_speaker,
    }

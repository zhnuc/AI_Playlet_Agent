"""Commit turn outputs into runtime events and maintain role memories."""
from typing import Any

from Agent_model import Summary_Agent, is_valid_summary_response
from story_state import Event, RuntimeState, get_event_by_id

SUMMARY_VISIBLE_EVENT_WINDOW = 24
DIGEST_PUBLIC_EVENT_WINDOW = 6
DIGEST_PRIVATE_EVENT_WINDOW = 3
DIGEST_PUBLIC_MAX_CHARS = 560
DIGEST_PRIVATE_MAX_CHARS = 240


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)]}..."


def _is_public_event(event: Event) -> bool:
    return event.kind in {"action", "dialogue", "system", "director", "monitor"}


def _event_to_digest_line(event: Event, limit: int = 72) -> str:
    content = _truncate(event.content.replace("\n", " ").strip(), limit)
    return f"{event.speaker}({event.kind}): {content}"


def build_event_id(runtime_state: RuntimeState) -> str:
    """Generate monotonic event id."""
    return f"e{len(runtime_state.story.event_log) + 1}"


def append_event(runtime_state: RuntimeState, event: Event) -> None:
    """Append event into global log and visible role histories."""
    runtime_state.story.event_log.append(event)
    for role_name in event.visible_to:
        runtime_state.role_memories[role_name].private_history.append(event.event_id)


def build_event(
    runtime_state: RuntimeState,
    step: int,
    kind: str,
    speaker: str,
    content: str,
    visible_to: list[str],
) -> Event:
    """Build a normalized runtime event."""
    return Event(
        event_id=build_event_id(runtime_state),
        step=step,
        episode=runtime_state.story.current_episode,
        scene=runtime_state.story.current_scene,
        kind=kind,
        speaker=speaker,
        content=content,
        visible_to=visible_to,
    )


def commit_system_event(
    runtime_state: RuntimeState,
    kind: str,
    speaker: str,
    content: str,
    visible_to: list[str] | None = None,
) -> Event:
    """Commit system/director/monitor event."""
    resolved_visible = visible_to if visible_to is not None else list(runtime_state.story.scene_roles)
    event = build_event(
        runtime_state,
        step=runtime_state.story.current_turn,
        kind=kind,
        speaker=speaker,
        content=content,
        visible_to=resolved_visible,
    )
    append_event(runtime_state, event)
    if resolved_visible:
        refresh_episode_digests(runtime_state, roles=resolved_visible)
    return event


def commit_turn_result(runtime_state: RuntimeState, speaker: str, turn_output: dict) -> list[Event]:
    """Commit thought/action/dialogue outputs from one role turn."""
    runtime_state.story.current_turn += 1
    step = runtime_state.story.current_turn
    committed_events: list[Event] = []

    thought = turn_output.get("Inner_Thought", "").strip()
    action = turn_output.get("Action", "").strip()
    dialogue = turn_output.get("Dialogue", "").strip()

    if thought:
        event = build_event(runtime_state, step, "thought", speaker, thought, [speaker])
        append_event(runtime_state, event)
        committed_events.append(event)

    if action:
        event = build_event(
            runtime_state,
            step,
            "action",
            speaker,
            action,
            list(runtime_state.story.scene_roles),
        )
        append_event(runtime_state, event)
        committed_events.append(event)

    if dialogue:
        event = build_event(
            runtime_state,
            step,
            "dialogue",
            speaker,
            dialogue,
            list(runtime_state.story.scene_roles),
        )
        append_event(runtime_state, event)
        committed_events.append(event)

    refresh_episode_digests(runtime_state)
    return committed_events


def get_role_visible_events(role_name: str, runtime_state: RuntimeState) -> list[Event]:
    """Resolve role-visible event list from private_history ids."""
    events: list[Event] = []
    for event_id in runtime_state.role_memories[role_name].private_history:
        event = get_event_by_id(runtime_state, event_id)
        if event is not None:
            events.append(event)
    return events


def serialize_events_for_summary(events: list[Event]) -> list[dict[str, Any]]:
    """Serialize events for summary prompt input."""
    return [
        {
            "event_id": event.event_id,
            "step": event.step,
            "kind": event.kind,
            "speaker": event.speaker,
            "content": event.content,
        }
        for event in events
    ]


def serialize_events_for_carryover_tail(events: list[Event], fallback_history_window: int = 6) -> list[dict[str, Any]]:
    """Serialize recent tail events as fallback cross-episode memory."""
    tail_events = events[-fallback_history_window:] if fallback_history_window > 0 else []
    return [
        {
            "event_id": event.event_id,
            "step": event.step,
            "kind": event.kind,
            "speaker": event.speaker,
            "content": event.content,
        }
        for event in tail_events
    ]


def update_role_episode_digest(
    role_name: str,
    runtime_state: RuntimeState,
    public_window: int = DIGEST_PUBLIC_EVENT_WINDOW,
    private_window: int = DIGEST_PRIVATE_EVENT_WINDOW,
) -> None:
    """Refresh lightweight per-role rolling episode digest."""
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    if not visible_events:
        role_memory.episode_digest_public = ""
        role_memory.episode_digest_private = ""
        role_memory.episode_digest_until_event_id = None
        return

    public_events = [event for event in visible_events if _is_public_event(event)]
    public_tail = public_events[-public_window:] if public_window > 0 else []
    if public_tail:
        public_lines = [_event_to_digest_line(event) for event in public_tail]
        role_memory.episode_digest_public = _truncate(" | ".join(public_lines), DIGEST_PUBLIC_MAX_CHARS)
    elif not role_memory.episode_digest_public:
        role_memory.episode_digest_public = ""

    private_thoughts = [
        event
        for event in visible_events
        if event.kind == "thought" and event.speaker == role_name
    ]
    private_tail = private_thoughts[-private_window:] if private_window > 0 else []
    if private_tail:
        private_lines = [_event_to_digest_line(event, limit=88) for event in private_tail]
        role_memory.episode_digest_private = _truncate(" | ".join(private_lines), DIGEST_PRIVATE_MAX_CHARS)

    role_memory.episode_digest_until_event_id = visible_events[-1].event_id


def refresh_episode_digests(runtime_state: RuntimeState, roles: list[str] | None = None) -> None:
    """Refresh rolling digests for all or selected roles."""
    target_roles = roles if roles is not None else list(runtime_state.role_memories.keys())
    for role_name in target_roles:
        if role_name in runtime_state.role_memories:
            update_role_episode_digest(role_name, runtime_state)


def build_role_summary_input(role_name: str, runtime_state: RuntimeState) -> dict[str, Any]:
    """Prepare bounded payload for summary agent."""
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    recent_events = visible_events[-SUMMARY_VISIBLE_EVENT_WINDOW:] if SUMMARY_VISIBLE_EVENT_WINDOW > 0 else []
    return {
        "role_name": role_name,
        "episode": runtime_state.story.current_episode,
        "scene": runtime_state.story.current_scene,
        "current_goal": role_memory.current_goal,
        "carryover_summary": role_memory.carryover_summary,
        "beliefs_about_others": dict(role_memory.beliefs_about_others),
        "unresolved_hook": role_memory.unresolved_hook,
        "episode_digest_public": role_memory.episode_digest_public,
        "episode_digest_private": role_memory.episode_digest_private,
        "visible_event_total_count": len(visible_events),
        "visible_events": serialize_events_for_summary(recent_events),
    }


def apply_summary_to_role_memory(role_name: str, runtime_state: RuntimeState, summary_payload: dict[str, Any]) -> None:
    """Apply validated summary payload to role memory."""
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    summary_text = summary_payload.get("carryover_summary", "").strip()
    current_goal = summary_payload.get("current_goal", "").strip()

    role_memory.private_summary = summary_text
    role_memory.summary_until_event_id = visible_events[-1].event_id if visible_events else None
    role_memory.carryover_summary = summary_text
    if current_goal:
        role_memory.current_goal = current_goal
    role_memory.beliefs_about_others = dict(summary_payload.get("beliefs_about_others", {}))
    role_memory.unresolved_hook = summary_payload.get("unresolved_hook", "").strip()


def save_role_carryover_event_tail(
    role_name: str,
    runtime_state: RuntimeState,
    fallback_history_window: int = 6,
) -> None:
    """Store raw tail events for fallback cross-episode continuation."""
    visible_events = get_role_visible_events(role_name, runtime_state)
    runtime_state.role_memories[role_name].carryover_event_tail = serialize_events_for_carryover_tail(
        visible_events,
        fallback_history_window=fallback_history_window,
    )


def finalize_role_memories_for_next_episode(
    runtime_state: RuntimeState,
    summary_agent: Summary_Agent | None,
    fallback_history_window: int = 6,
) -> dict[str, str]:
    """Finalize role memories at episode end for cross-episode continuity."""
    roles_to_summarize = [
        role_name
        for role_name, role_memory in runtime_state.role_memories.items()
        if role_memory.private_history
    ]
    if not roles_to_summarize:
        return {}

    refresh_episode_digests(runtime_state, roles=roles_to_summarize)
    for role_name in roles_to_summarize:
        save_role_carryover_event_tail(
            role_name,
            runtime_state,
            fallback_history_window=fallback_history_window,
        )

    if summary_agent is None:
        return {role_name: "summary_agent_missing" for role_name in roles_to_summarize}

    summary_inputs = {
        role_name: build_role_summary_input(role_name, runtime_state)
        for role_name in roles_to_summarize
    }
    summary_result = summary_agent.generate_role_summaries(summary_inputs)
    if isinstance(summary_result, str):
        return {role_name: summary_result for role_name in roles_to_summarize}

    summary_status: dict[str, str] = {}
    for role_name in roles_to_summarize:
        summary_payload = summary_result.get(role_name)
        if not isinstance(summary_payload, dict) or not is_valid_summary_response(summary_payload):
            summary_status[role_name] = "schema_error"
            continue
        apply_summary_to_role_memory(role_name, runtime_state, summary_payload)
        summary_status[role_name] = "updated"

    return summary_status

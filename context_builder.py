"""Runtime Context V2 prompt builder."""
from __future__ import annotations

from typing import Any

from episode_beats import can_end_current_episode, get_active_beat
from event_committer import get_role_visible_events
from story_state import Event, INTERACTION_MODE_PENDING_REPLIES, RuntimeState

SCENE_WINDOW_MIN = 3
SCENE_WINDOW_MAX = 5
DEFAULT_SCENE_WINDOW = 4
EVENT_PREVIEW_CHARS = 140


def _truncate(text: str, limit: int = EVENT_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 3, 0)]}..."


def _field(episode_plan: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = episode_plan.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _json_like_lines(items: list[str], empty_text: str) -> str:
    if not items:
        return f'["{empty_text}"]'
    escaped = [item.replace("\\", "\\\\").replace('"', '\\"') for item in items]
    return "[\n  " + ",\n  ".join(f'"{item}"' for item in escaped) + "\n]"


def _resolve_scene_window(tail_window: int) -> int:
    if tail_window <= 0:
        return DEFAULT_SCENE_WINDOW
    return min(max(tail_window, SCENE_WINDOW_MIN), SCENE_WINDOW_MAX)


def format_event(event: Event | dict[str, Any]) -> str:
    """Render event as one compact line."""
    if isinstance(event, Event):
        step = event.step
        kind = event.kind
        speaker = event.speaker
        content = event.content
    else:
        step = event.get("step", "?")
        kind = event.get("kind", "event")
        speaker = event.get("speaker", "UNKNOWN")
        content = event.get("content", "")
    return f"[step {step}] {kind} | {speaker}: {_truncate(str(content))}"


def format_event_block(events: list[Event | dict[str, Any]], empty_text: str) -> str:
    if not events:
        return empty_text
    return "\n".join(format_event(event) for event in events)


def format_beliefs(beliefs: dict[str, str]) -> str:
    if not beliefs:
        return "none"
    lines = [f"- {name}: {_truncate(judgement, 120)}" for name, judgement in beliefs.items()]
    return "\n".join(lines)


def _is_public_event(event: Event) -> bool:
    return event.kind in {"action", "dialogue", "system", "director", "monitor"}


def _get_recent_public_events(role_name: str, runtime_state: RuntimeState, scene_window: int) -> list[Event]:
    visible_events = get_role_visible_events(role_name, runtime_state)
    public_events = [event for event in visible_events if _is_public_event(event)]
    return public_events[-scene_window:]


def _get_latest_trigger_event(role_name: str, runtime_state: RuntimeState) -> Event | None:
    trigger_id = runtime_state.interaction.trigger_event_id
    if trigger_id:
        visible_events = get_role_visible_events(role_name, runtime_state)
        for event in reversed(visible_events):
            if event.event_id == trigger_id:
                return event
    recent_public = _get_recent_public_events(role_name, runtime_state, scene_window=1)
    if recent_public:
        return recent_public[-1]
    return None


def _build_tension_state(runtime_state: RuntimeState) -> str:
    if runtime_state.interaction.mode == INTERACTION_MODE_PENDING_REPLIES:
        return "Queue mode active: direct responses are required and topic switching is disallowed."
    turn = runtime_state.story.current_turn
    if turn <= 2:
        return "Opening phase: conflict is being established."
    if turn <= 6:
        return "Escalation phase: pressure should increase, avoid repetitive argument."
    return "High tension phase: push toward decisive conflict or hook."


def build_allowed_next_speakers(role_name: str, runtime_state: RuntimeState) -> list[str]:
    allowed = [role for role in runtime_state.story.scene_roles if role != role_name]
    allowed.append("end_request")
    return allowed


def build_role_header(role_name: str, runtime_state: RuntimeState) -> str:
    role_card = runtime_state.story.character_roster[role_name]
    role_type = role_card.get("role_type", "character")
    identity = role_card.get("identity", "unknown")
    personality = ", ".join(role_card.get("personality_tags", [])) or "n/a"
    catchphrase = role_card.get("catchphrase", "n/a")

    return f"""
# Runtime Context V2
You are role-playing strictly as "{role_name}" and must stay in-character.

## Identity Layer
- role_name: {role_name}
- role_type: {role_type}
- identity: {identity}
- personality_signature: {personality}
- speaking_style_hint: keep voice consistent with catchphrase "{_truncate(str(catchphrase), 100)}"
""".strip()


def build_season_layer(role_name: str, runtime_state: RuntimeState) -> str:
    role_memory = runtime_state.role_memories[role_name]
    carryover_summary = role_memory.carryover_summary.strip() or "none"
    unresolved_hook = role_memory.unresolved_hook.strip() or "none"

    return f"""
## Season Layer
- carryover_summary: {_truncate(carryover_summary, 320)}
- beliefs_about_others:
{format_beliefs(role_memory.beliefs_about_others)}
- unresolved_hook: {_truncate(unresolved_hook, 160)}
""".strip()


def build_episode_layer(role_name: str, runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> str:
    role_memory = runtime_state.role_memories[role_name]
    role_directive = episode_plan.get("character_directives", {}).get(
        role_name,
        "Advance the scene naturally from your role perspective.",
    )
    role_goal = role_memory.current_goal.strip() or str(role_directive)
    active_beat = get_active_beat(runtime_state)

    beat_block = "- current_beat: none"
    if active_beat is not None:
        beat_block = (
            "- current_beat:\n"
            f"  - label: {active_beat.label}\n"
            f"  - objective: {active_beat.objective}\n"
            f"  - must_land: {active_beat.must_land}\n"
            f"  - exit_condition: {active_beat.exit_condition}"
        )

    return f"""
## Episode Layer
- episode_number: {runtime_state.story.current_episode}
- scene: {runtime_state.story.current_scene}
- episode_objective: {_field(episode_plan, "global_plot", default="Drive this episode mainline.")}
- core_conflict: {_field(episode_plan, "core_conflict", default="Escalate the central conflict.")}
- role_episode_goal: {_truncate(role_goal, 220)}
{beat_block}
""".strip()


def build_scene_state_layer(role_name: str, runtime_state: RuntimeState, tail_window: int) -> str:
    role_memory = runtime_state.role_memories[role_name]
    scene_window = _resolve_scene_window(tail_window)
    recent_public_events = _get_recent_public_events(role_name, runtime_state, scene_window)
    recent_public_lines = [format_event(event) for event in recent_public_events]
    latest_trigger_event = _get_latest_trigger_event(role_name, runtime_state)
    latest_trigger = format_event(latest_trigger_event) if latest_trigger_event else "none"

    queue_block = ""
    interaction = runtime_state.interaction
    if interaction.mode == INTERACTION_MODE_PENDING_REPLIES:
        initiator = interaction.initiator or "unknown"
        if role_name == initiator:
            queue_action = "You are queue initiator; your next_speakers controls routing."
        else:
            queue_action = "You are a queued responder; must directly reply to initiator and output next_speakers as []."
        queue_block = (
            "- queue_state:\n"
            f"  - mode: {interaction.mode}\n"
            f"  - initiator: {initiator}\n"
            f"  - action_rule: {queue_action}"
        )
    else:
        queue_block = "- queue_state: normal"

    digest_public = role_memory.episode_digest_public.strip() or "none"
    digest_private = role_memory.episode_digest_private.strip() or "none"

    return f"""
## Scene State Layer
- rolling_episode_digest_public: {_truncate(digest_public, 420)}
- rolling_episode_digest_private: {_truncate(digest_private, 220)}
- recent_public_exchanges: {_json_like_lines(recent_public_lines, "none")}
- latest_trigger: {_truncate(latest_trigger, 220)}
- tension_state: {_build_tension_state(runtime_state)}
{queue_block}
""".strip()


def build_controller_block(
    runtime_state: RuntimeState,
    scene_instruction: str | None,
    role_instruction: str | None,
    monitor_instruction: str | None,
    controller_instruction: str | None,
) -> str:
    end_allowed = can_end_current_episode(runtime_state)
    director_instruction = role_instruction or scene_instruction or "none"
    repair_hint = controller_instruction or "none"
    monitor_note = monitor_instruction or "none"
    end_pressure = (
        "Ending can be requested with end_request if hook is already landed."
        if end_allowed
        else "Do not request ending yet; continue pushing current beat."
    )
    return f"""
## Control Layer
- director_instruction: {_truncate(director_instruction, 220)}
- repair_hint: {_truncate(repair_hint, 220)}
- end_pressure: {end_pressure}
- monitor_note: {_truncate(monitor_note, 220)}
""".strip()


def build_fallback_memory_block(role_name: str, runtime_state: RuntimeState, fallback_history_window: int) -> str:
    role_memory = runtime_state.role_memories[role_name]
    fallback_events = role_memory.carryover_event_tail[-fallback_history_window:] if fallback_history_window > 0 else []
    return f"""
## Fallback Memory
Use this only when carryover summary is empty.
{format_event_block(fallback_events, "none")}
""".strip()


def build_routing_rules(
    role_name: str,
    runtime_state: RuntimeState,
    retry_invalid_next_speaker: str | None,
) -> str:
    interaction = runtime_state.interaction
    if interaction.mode == INTERACTION_MODE_PENDING_REPLIES and role_name != interaction.initiator:
        rules = [
            "## Routing Rules",
            "- Queue responder mode: next_speakers must be [] in this turn.",
            "- Focus on direct response to initiator; do not switch topic.",
        ]
    else:
        allowed_values = ", ".join(build_allowed_next_speakers(role_name, runtime_state))
        rules = [
            "## Routing Rules",
            f"- next_speakers can only choose from: {allowed_values}",
            f"- Never output the current speaker itself: {role_name}",
            "- Do not output out-of-scene roles or generic placeholders.",
            "- Use end_request only as a request; final ending decision belongs to controller.",
        ]

    if retry_invalid_next_speaker:
        rules.extend(
            [
                "## Retry Note",
                f"- Previous routing was invalid: {retry_invalid_next_speaker}",
                "- Fix routing first, then continue dramatic progression.",
            ]
        )
    return "\n".join(rules)


def build_output_contract(role_name: str, runtime_state: RuntimeState) -> str:
    end_allowed = can_end_current_episode(runtime_state)
    allowed_next = ", ".join(build_allowed_next_speakers(role_name, runtime_state))
    return f"""
## Output Contract
- allowed_next_speakers: {allowed_next}
- end_allowed: {str(end_allowed).lower()}
- Return strict JSON only (no markdown, no explanation).
- Top-level key must be "{role_name}".
- Required schema:
{{
  "{role_name}": {{
    "Inner_Thought": "string",
    "Action": "string",
    "Dialogue": "string",
    "next_speakers": ["string"]
  }}
}}
""".strip()


def build_role_context(
    role_name: str,
    runtime_state: RuntimeState,
    episode_plan: dict[str, Any],
    tail_window: int = 4,
    fallback_history_window: int = 6,
    use_fallback_history: bool = False,
    retry_invalid_next_speaker: str | None = None,
    scene_instruction: str | None = None,
    role_instruction: str | None = None,
    monitor_instruction: str | None = None,
    controller_instruction: str | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
) -> str:
    """Build runtime prompt with a fixed six-layer structure."""
    del soft_turn_limit  # retained for call compatibility
    del hard_turn_limit  # retained for call compatibility

    sections = [
        build_role_header(role_name, runtime_state),
        build_season_layer(role_name, runtime_state),
        build_episode_layer(role_name, runtime_state, episode_plan),
        build_scene_state_layer(role_name, runtime_state, tail_window),
    ]

    if use_fallback_history:
        sections.append(build_fallback_memory_block(role_name, runtime_state, fallback_history_window))

    sections.append(
        build_controller_block(
            runtime_state,
            scene_instruction=scene_instruction,
            role_instruction=role_instruction,
            monitor_instruction=monitor_instruction,
            controller_instruction=controller_instruction,
        )
    )
    sections.append(build_routing_rules(role_name, runtime_state, retry_invalid_next_speaker))
    sections.append(build_output_contract(role_name, runtime_state))

    return "\n\n".join(section for section in sections if section).strip() + "\n"

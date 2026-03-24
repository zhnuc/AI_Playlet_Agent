"""Runtime beat planning and controller helpers."""
from __future__ import annotations

from typing import Any

from story_state import (
    BEAT_STATUS_ACTIVE,
    BEAT_STATUS_COMPLETED,
    BEAT_STATUS_PENDING,
    BeatState,
    EpisodeBeat,
    RuntimeState,
)


def _dedupe_role_names(candidates: list[str]) -> list[str]:
    resolved: list[str] = []
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in resolved:
            resolved.append(normalized)
    return resolved


def build_episode_beats(episode_plan: dict[str, Any]) -> list[EpisodeBeat]:
    """Build a compact runtime beat sheet from a user-facing outline."""
    roles = _dedupe_role_names(list(episode_plan.get("scene_roles", [])))
    first_speaker = (episode_plan.get("first_speaker") or "").strip()
    remaining_roles = [role for role in roles if role != first_speaker]

    opening_speakers = _dedupe_role_names([first_speaker] + remaining_roles[:1]) or roles[:1]
    pressure_speakers = remaining_roles[:2] or roles[:2]
    reversal_speakers = roles[:2]
    hook_speakers = roles[-2:] if len(roles) >= 2 else roles[:1]

    beats = [
        EpisodeBeat(
            beat_id="opening",
            label="Opening Beat",
            objective="Open the scene quickly and lock the premise into public view.",
            must_land=episode_plan.get("global_plot", "").strip() or "Open the main premise.",
            exit_condition="The room clearly understands what the confrontation is about.",
            suggested_speakers=opening_speakers,
        ),
        EpisodeBeat(
            beat_id="pressure",
            label="Pressure Beat",
            objective="Escalate the main conflict instead of repeating surface emotion.",
            must_land=episode_plan.get("core_conflict", "").strip() or "Escalate the central conflict.",
            exit_condition="At least one side loses room to keep stalling.",
            suggested_speakers=pressure_speakers,
        ),
        EpisodeBeat(
            beat_id="reversal",
            label="Reversal Beat",
            objective="Force a shift in power, information, or emotional control.",
            must_land="A new piece of leverage, confession, or reversal must enter the scene.",
            exit_condition="The scene no longer feels balanced.",
            suggested_speakers=reversal_speakers,
        ),
        EpisodeBeat(
            beat_id="hook",
            label="Hook Beat",
            objective="Land the episode hook and steer toward a clean cut point.",
            must_land=episode_plan.get("plot_twist_or_hook", "").strip() or "Land the episode hook.",
            exit_condition="The hook is explicit enough that the next episode has momentum.",
            suggested_speakers=hook_speakers,
        ),
    ]
    return beats


def create_beat_state(episode_plan: dict[str, Any]) -> BeatState:
    beats = build_episode_beats(episode_plan)
    return BeatState(
        beats=beats,
        active_index=0,
        last_advanced_turn=0,
        status=BEAT_STATUS_ACTIVE if beats else BEAT_STATUS_COMPLETED,
    )


def get_active_beat(runtime_state: RuntimeState) -> EpisodeBeat | None:
    beat_state = runtime_state.beat_state
    if not beat_state.beats:
        return None
    active_index = min(max(beat_state.active_index, 0), len(beat_state.beats) - 1)
    return beat_state.beats[active_index]


def is_last_beat(runtime_state: RuntimeState) -> bool:
    beat_state = runtime_state.beat_state
    return bool(beat_state.beats) and beat_state.active_index >= len(beat_state.beats) - 1


def advance_beat(runtime_state: RuntimeState, note: str) -> EpisodeBeat | None:
    beat_state = runtime_state.beat_state
    if not beat_state.beats:
        beat_state.status = BEAT_STATUS_COMPLETED
        return None

    beat_state.completion_notes.append(note)
    beat_state.last_advanced_turn = runtime_state.story.current_turn
    if beat_state.active_index < len(beat_state.beats) - 1:
        beat_state.active_index += 1
        beat_state.status = BEAT_STATUS_ACTIVE
        return beat_state.beats[beat_state.active_index]

    beat_state.status = BEAT_STATUS_COMPLETED
    return beat_state.beats[-1]


def infer_target_turn(soft_turn_limit: int, beat_count: int, beat_index: int) -> int:
    if soft_turn_limit <= 0 or beat_count <= 0:
        return 0
    return max(1, round(((beat_index + 1) / beat_count) * soft_turn_limit))


def maybe_advance_beat(runtime_state: RuntimeState, soft_turn_limit: int) -> EpisodeBeat | None:
    """Advance beats using a lightweight controller heuristic."""
    beat_state = runtime_state.beat_state
    if not beat_state.beats or beat_state.status == BEAT_STATUS_COMPLETED:
        return None
    if is_last_beat(runtime_state):
        return None

    target_turn = infer_target_turn(soft_turn_limit, len(beat_state.beats), beat_state.active_index)
    if runtime_state.story.current_turn < target_turn:
        return None

    active_beat = get_active_beat(runtime_state)
    beat_label = active_beat.label if active_beat else "beat"
    return advance_beat(
        runtime_state,
        note=f"Advanced after turn {runtime_state.story.current_turn}: {beat_label}",
    )


def build_controller_instruction(
    runtime_state: RuntimeState,
    soft_turn_limit: int,
    hard_turn_limit: int | None,
) -> str | None:
    """Return a temporary controller hint for the next speaker."""
    active_beat = get_active_beat(runtime_state)
    if active_beat is None:
        return None

    turn = runtime_state.story.current_turn
    turns_since_advance = turn - runtime_state.beat_state.last_advanced_turn

    if turn >= soft_turn_limit and not is_last_beat(runtime_state):
        return (
            f"You are past the soft turn budget. Immediately pivot into the active beat and land: "
            f"{active_beat.must_land}"
        )

    if turn >= max(soft_turn_limit - 1, 1):
        return (
            f"Enter closing mode. Stay inside {active_beat.label} and make the hook explicit: "
            f"{active_beat.must_land}"
        )

    if turns_since_advance >= 2:
        return (
            f"The scene is stalling in {active_beat.label}. Stop repeating the same argument and push toward: "
            f"{active_beat.must_land}"
        )

    return None


def can_end_current_episode(runtime_state: RuntimeState, min_turns: int = 4) -> bool:
    """Only allow natural ending after the runtime has reached the closing beat."""
    if runtime_state.story.current_turn < min_turns:
        return False
    if not runtime_state.story.event_log:
        return False
    return is_last_beat(runtime_state)

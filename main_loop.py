"""Compatibility layer.

The runtime engine implementation has been moved to `runtime.session_engine`.
Keep this module as a stable import path for existing callers.
"""

from runtime.session_engine import (
    SEASON_CONTINUE_STATUSES,
    VALID_DIRECTOR_COMMANDS,
    EpisodeSession,
    build_episode_checkpoint_payload,
    build_season_summary,
    choose_trigger_event_id,
    create_episode_session,
    derive_turn_limits,
    generate_role_turn_with_route_retry,
    is_episode_success_status,
    log_role_io,
    normalize_invalid_route_for_prompt,
    resolve_episode_start_speaker,
    run_demo_episode,
    run_episode,
    run_free_episode,
    run_season,
    should_use_fallback_history,
)

__all__ = [
    "SEASON_CONTINUE_STATUSES",
    "VALID_DIRECTOR_COMMANDS",
    "EpisodeSession",
    "build_episode_checkpoint_payload",
    "build_season_summary",
    "choose_trigger_event_id",
    "create_episode_session",
    "derive_turn_limits",
    "generate_role_turn_with_route_retry",
    "is_episode_success_status",
    "log_role_io",
    "normalize_invalid_route_for_prompt",
    "resolve_episode_start_speaker",
    "run_demo_episode",
    "run_episode",
    "run_free_episode",
    "run_season",
    "should_use_fallback_history",
]


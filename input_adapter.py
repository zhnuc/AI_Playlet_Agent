"""Input adapter for runtime config and free-mode planner bootstrap."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

REQUIRED_RUNTIME_KEYS = ("drama_settings", "logline", "character_roster")


def deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _validate_runtime_config_shape(runtime_config: dict[str, Any]) -> None:
    if not isinstance(runtime_config, dict):
        raise ValueError("config_override must be a JSON object")

    missing = [key for key in REQUIRED_RUNTIME_KEYS if key not in runtime_config]
    if missing:
        raise ValueError(f"config_override missing required fields: {', '.join(missing)}")

    drama_settings = runtime_config.get("drama_settings")
    if not isinstance(drama_settings, dict):
        raise ValueError("drama_settings must be an object")

    if not isinstance(runtime_config.get("logline"), str) or not runtime_config["logline"].strip():
        raise ValueError("logline must be a non-empty string")

    roster = runtime_config.get("character_roster")
    if not isinstance(roster, dict) or not roster:
        raise ValueError("character_roster must be a non-empty object")


def build_runtime_config(config_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build runtime config from external input only (no hard-coded fallback)."""
    if not config_override:
        raise ValueError(
            "config_override is required. "
            "This service no longer falls back to global_config.py."
        )

    runtime_config = deepcopy(config_override)
    _validate_runtime_config_shape(runtime_config)
    return runtime_config


def build_free_mode_planner_output(
    runtime_config: dict[str, Any],
    opening_scene: str | None = None,
    scene_roles: list[str] | None = None,
    story_hook: str | None = None,
) -> dict[str, Any]:
    available_roles = list(runtime_config["character_roster"].keys())
    resolved_scene_roles = [
        role_name for role_name in (scene_roles or available_roles[:2]) if role_name in available_roles
    ]
    if not resolved_scene_roles:
        resolved_scene_roles = available_roles[:1]
    first_speaker = resolved_scene_roles[0] if resolved_scene_roles else ""
    place = (opening_scene or "High-pressure confrontation scene").strip() or "High-pressure confrontation scene"
    hook = (story_hook or runtime_config["logline"]).strip() or runtime_config["logline"]

    character_directives = {
        role_name: "Stay in-character, escalate conflict, and end with a clear hook."
        for role_name in resolved_scene_roles
    }

    return {
        "episodes": [
            {
                "episode_number": 1,
                "global_plot": f"Single-scene escalation around: {hook}",
                "place": place,
                "scene_roles": resolved_scene_roles,
                "core_conflict": "Roles collide around a concrete conflict or secret in the same scene.",
                "plot_twist_or_hook": f"End this scene with a strong hook: {hook}",
                "first_speaker": first_speaker,
                "character_directives": character_directives,
            }
        ]
    }


"""输入适配层。

负责把固定 global_config、外部请求参数和 free mode 场景设定
整理成统一的运行时输入结构。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from global_config import global_config


def deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """深合并配置字典。"""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def build_runtime_config(config_override: dict[str, Any] | None = None) -> dict[str, Any]:
    """基于默认 global_config 构造一次运行所需配置。"""
    if not config_override:
        return deepcopy(global_config)
    return deep_merge_dict(global_config, config_override)


def build_free_mode_planner_output(
    runtime_config: dict[str, Any],
    opening_scene: str | None = None,
    scene_roles: list[str] | None = None,
    story_hook: str | None = None,
) -> dict[str, Any]:
    """为 free mode 生成最小可运行的单集 planner 输出。"""
    available_roles = list(runtime_config["character_roster"].keys())
    resolved_scene_roles = [
        role_name for role_name in (scene_roles or available_roles[:2]) if role_name in available_roles
    ]
    if not resolved_scene_roles:
        resolved_scene_roles = available_roles[:1]
    first_speaker = resolved_scene_roles[0] if resolved_scene_roles else ""
    place = (opening_scene or "高压对峙现场").strip() or "高压对峙现场"
    hook = (story_hook or runtime_config["logline"]).strip() or runtime_config["logline"]

    character_directives = {
        role_name: "根据人物设定主动制造冲突，并尽快抛出新的爽点或悬念。"
        for role_name in resolved_scene_roles
    }

    return {
        "episodes": [
            {
                "episode_number": 1,
                "global_plot": f"围绕“{hook}”展开一场高密度的即时冲突。",
                "place": place,
                "scene_roles": resolved_scene_roles,
                "core_conflict": "角色在同一场景下围绕核心利益或秘密正面碰撞。",
                "plot_twist_or_hook": f"在本场冲突尾声抛出足以推动下一场戏的钩子：{hook}",
                "first_speaker": first_speaker,
                "character_directives": character_directives,
            }
        ]
    }

"""导出层：将事件日志整理为短剧台本和 shotlist。"""
from __future__ import annotations

from typing import Any

from story_state import RuntimeState


def _collect_scene_lines(runtime_state: RuntimeState) -> list[str]:
    """将事件日志转换为可阅读的短剧台本行。"""
    lines: list[str] = []
    for event in runtime_state.story.event_log:
        if event.kind == "action":
            lines.append(f"动作：{event.speaker}{event.content}")
        elif event.kind == "dialogue":
            lines.append(f"{event.speaker}：{event.content}")
        elif event.kind == "thought":
            lines.append(f"内心：{event.speaker}（{event.content}）")
    return lines


def export_episode_script(runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> str:
    """导出标准短剧台本文本。"""
    header = [
        f"【第{runtime_state.story.current_episode}集】",
        f"场景：{runtime_state.story.current_scene}",
        f"主线：{episode_plan['global_plot']}",
        "",
    ]
    return "\n".join(header + _collect_scene_lines(runtime_state))


def export_episode_shotlist(runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> dict[str, Any]:
    """导出简化版 shotlist JSON。"""
    shots: list[dict[str, Any]] = []
    shot_number = 1
    for event in runtime_state.story.event_log:
        if event.kind not in {"action", "dialogue"}:
            continue
        shots.append(
            {
                "shot_number": shot_number,
                "episode": runtime_state.story.current_episode,
                "scene": runtime_state.story.current_scene,
                "speaker": event.speaker,
                "event_kind": event.kind,
                "content": event.content,
                "suggested_camera": "medium close-up" if event.kind == "dialogue" else "medium shot",
            }
        )
        shot_number += 1

    return {
        "episode": runtime_state.story.current_episode,
        "scene": runtime_state.story.current_scene,
        "scene_goal": episode_plan["global_plot"],
        "hook": episode_plan["plot_twist_or_hook"],
        "shots": shots,
    }


def export_artifacts(
    runtime_state: RuntimeState,
    episode_plan: dict[str, Any],
    season_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """统一导出剧本、shotlist 和整季摘要。"""
    return {
        "script": export_episode_script(runtime_state, episode_plan),
        "shotlist": export_episode_shotlist(runtime_state, episode_plan),
        "season_summary": season_summary or {},
    }

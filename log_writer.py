# 该文件负责将单集运行过程写入结构化日志。
# 它独立于主流程维护 episode 级 JSON 文件，
# 用于保存场景信息、逐轮角色输出和最终运行结果。
#* 工具函数，记录：初始化场景信息、每轮角色输出、最终结果
import json
from pathlib import Path
from typing import Any

from story_state import Event, RoleMemory, RuntimeState


def build_episode_log_path(episode: int, log_dir: str = "log") -> Path:
    """构造单集 JSON 日志路径，并确保日志目录存在。"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path / f"episode_{episode:02d}_trace.json"


def write_episode_log(log_path: Path, payload: dict[str, Any]) -> None:
    """将日志对象写入 JSON 文件。"""
    log_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_episode_log(log_path: Path) -> dict[str, Any]:
    """读取当前单集 JSON 日志。"""
    return json.loads(log_path.read_text(encoding="utf-8"))


def serialize_event(event: Event) -> dict[str, Any]:
    """将事件对象整理为便于审阅的 JSON 结构。"""
    return {
        "event_id": event.event_id,
        "step": event.step,
        "episode": event.episode,
        "scene": event.scene,
        "kind": event.kind,
        "speaker": event.speaker,
        "content": event.content,
        "visible_to": list(event.visible_to),
    }


def serialize_role_memory(role_memory: RoleMemory) -> dict[str, Any]:
    """将角色记忆整理为可直接写入日志的结构。"""
    return {
        "private_history": list(role_memory.private_history),
        "private_summary": role_memory.private_summary,
        "summary_until_event_id": role_memory.summary_until_event_id,
        "carryover_summary": role_memory.carryover_summary,
        "carryover_event_tail": [dict(event) for event in role_memory.carryover_event_tail],
        "current_goal": role_memory.current_goal,
        "beliefs_about_others": dict(role_memory.beliefs_about_others),
        "unresolved_hook": role_memory.unresolved_hook,
    }


def serialize_role_memories(role_memories: dict[str, RoleMemory]) -> dict[str, dict[str, Any]]:
    """批量整理角色记忆快照。"""
    return {
        role_name: serialize_role_memory(role_memory)
        for role_name, role_memory in role_memories.items()
    }


def initialize_episode_log(
    runtime_state: RuntimeState,
    episode_plan: dict,
    log_dir: str = "log",
) -> Path:
    """初始化单集日志文件，写入场景信息、角色指令和空回合列表。"""
    log_path = build_episode_log_path(runtime_state.story.current_episode, log_dir)
    scene_roles = runtime_state.story.scene_roles
    directives = {
        role_name: episode_plan["character_directives"].get(role_name, "根据现场局势自然推进剧情")
        for role_name in scene_roles
    }

    payload = {
        "episode": runtime_state.story.current_episode,
        "scene_info": {
            "scene": runtime_state.story.current_scene,
            "scene_roles": scene_roles,
            "global_plot": episode_plan["global_plot"],
            "core_conflict": episode_plan["core_conflict"],
            "plot_twist_or_hook": episode_plan["plot_twist_or_hook"],
            "first_speaker": episode_plan["first_speaker"],
        },
        "character_directives": directives,
        "initial_role_memories": serialize_role_memories(runtime_state.role_memories),
        "turns": [],
        "result": None,
    }
    write_episode_log(log_path, payload)
    return log_path


def append_turn_log(
    log_path: Path,
    step: int,
    speaker: str,
    prompt: str,
    use_fallback_history: bool,
    turn_output: dict,
    committed_events: list[Event],
    proposed_next_speaker: str | None,
    resolved_next_speaker: str | None,
    status: str,
) -> None:
    """将当前回合的角色原始输出追加到 JSON 日志。"""
    payload = read_episode_log(log_path)
    payload["turns"].append(
        {
            "step": step,
            "speaker": speaker,
            "use_fallback_history": use_fallback_history,
            "prompt": prompt,
            "output": {
                "Inner_Thought": turn_output.get("Inner_Thought", "").strip(),
                "Action": turn_output.get("Action", "").strip(),
                "Dialogue": turn_output.get("Dialogue", "").strip(),
                "next_speaker": turn_output.get("next_speaker"),
            },
            "committed_events": [serialize_event(event) for event in committed_events],
            "routing": {
                "proposed_next_speaker": proposed_next_speaker,
                "resolved_next_speaker": resolved_next_speaker,
                "status": status,
            },
        }
    )
    write_episode_log(log_path, payload)


def finalize_episode_log(
    log_path: Path,
    runtime_state: RuntimeState,
    result_status: str,
    last_speaker: str,
    total_turns: int,
    summary_status: dict[str, str],
) -> None:
    """在 JSON 日志中写入单集最终结果。"""
    payload = read_episode_log(log_path)
    payload["result"] = {
        "status": result_status,
        "last_speaker": last_speaker,
        "total_turns": total_turns,
        "summary_status": summary_status,
        "final_role_memories": serialize_role_memories(runtime_state.role_memories),
    }
    write_episode_log(log_path, payload)

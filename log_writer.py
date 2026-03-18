# 该文件负责将单集运行过程写入结构化日志。
# 它独立于主流程维护 episode 级 JSON 文件，
# 用于保存场景信息、逐轮角色输出和最终运行结果。
#* 工具函数，记录：初始化场景信息、每轮角色输出、最终结果
import json
from pathlib import Path
from typing import Any

from story_state import RuntimeState


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
        "turns": [],
        "result": None,
    }
    write_episode_log(log_path, payload)
    return log_path


def append_turn_log(
    log_path: Path,
    step: int,
    speaker: str,
    turn_output: dict,
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
            "output": {
                "Inner_Thought": turn_output.get("Inner_Thought", "").strip(),
                "Action": turn_output.get("Action", "").strip(),
                "Dialogue": turn_output.get("Dialogue", "").strip(),
                "next_speaker": turn_output.get("next_speaker"),
            },
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
    result_status: str,
    last_speaker: str,
    total_turns: int,
) -> None:
    """在 JSON 日志中写入单集最终结果。"""
    payload = read_episode_log(log_path)
    payload["result"] = {
        "status": result_status,
        "last_speaker": last_speaker,
        "total_turns": total_turns,
    }
    write_episode_log(log_path, payload)

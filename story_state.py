# 该文件定义剧情运行期的核心状态结构。
# 包括事件、角色记忆、全局故事上下文和运行时状态，
# 供主循环、日志和上下文管理模块共享使用。
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """定义单条剧情事件。"""

    event_id: str
    step: int
    episode: int
    scene: str
    kind: str
    speaker: str
    content: str
    visible_to: list[str]


@dataclass
class RoleMemory:
    """定义角色私有记忆。"""

    private_history: list[str] = field(default_factory=list)
    private_summary: str = ""
    current_goal: str = ""
    beliefs_about_others: dict[str, str] = field(default_factory=dict)


@dataclass
class StoryContext:
    """定义当前剧情的全局状态。"""

    drama_settings: dict[str, Any]
    logline: str
    character_roster: dict[str, dict[str, Any]]
    current_episode: int
    current_scene: str
    scene_roles: list[str]
    event_log: list[Event] = field(default_factory=list)
    current_turn: int = 0


@dataclass
class RuntimeState:
    """定义运行时的完整状态。"""

    story: StoryContext
    role_memories: dict[str, RoleMemory]


def get_episode_plan(planner_output: dict[str, Any], episode: int) -> dict[str, Any]:
    """读取指定集数的分集计划。"""
    episodes = planner_output.get("episodes", [])
    if episode <= 0 or episode > len(episodes):
        raise ValueError(f"episode={episode} 不在 planner 输出范围内")
    return episodes[episode - 1]


def build_role_memories(global_config: dict[str, Any], episode_plan: dict[str, Any]) -> dict[str, RoleMemory]:
    """根据角色表和单集指令初始化角色记忆。"""
    directives = episode_plan.get("character_directives", {})
    role_memories: dict[str, RoleMemory] = {}

    for role_name in global_config["character_roster"]:
        role_memories[role_name] = RoleMemory(
            current_goal=directives.get(role_name, "根据当前场景自然推进剧情"),
        )

    return role_memories


def create_runtime_state(global_config: dict[str, Any], planner_output: dict[str, Any], episode: int) -> RuntimeState:
    """创建单集运行所需的初始状态。"""
    episode_plan = get_episode_plan(planner_output, episode)
    story = StoryContext(
        drama_settings=global_config["drama_settings"],
        logline=global_config["logline"],
        character_roster=global_config["character_roster"],
        current_episode=episode,
        current_scene=episode_plan["place"],
        scene_roles=episode_plan["scene_roles"],
    )
    role_memories = build_role_memories(global_config, episode_plan)
    return RuntimeState(story=story, role_memories=role_memories)


def get_event_by_id(runtime_state: RuntimeState, event_id: str) -> Event | None:
    """按事件编号从全局日志中回查事件。"""
    for event in runtime_state.story.event_log:
        if event.event_id == event_id:
            return event
    return None

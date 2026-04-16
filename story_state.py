# 该文件定义剧情运行期的核心状态结构。
# 包括事件、角色记忆、全局故事上下文和运行时状态，
# 供主循环、日志和上下文管理模块共享使用。
from dataclasses import dataclass, field
from typing import Any, Literal

DEFAULT_ROLE_GOAL = "根据当前场景自然推进剧情"
INTERACTION_MODE_NORMAL = "normal"
INTERACTION_MODE_PENDING_REPLIES = "pending_replies"
RunMode = Literal["planned", "free"]
BEAT_STATUS_PENDING = "pending"
BEAT_STATUS_ACTIVE = "active"
BEAT_STATUS_COMPLETED = "completed"


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
    summary_until_event_id: str | None = None
    episode_digest_public: str = ""
    episode_digest_private: str = ""
    episode_digest_until_event_id: str | None = None
    carryover_summary: str = ""
    carryover_event_tail: list[dict[str, Any]] = field(default_factory=list)
    current_goal: str = ""
    beliefs_about_others: dict[str, str] = field(default_factory=dict)
    unresolved_hook: str = ""


@dataclass
class InteractionState:
    """定义当前场景的互动控制状态。"""

    mode: str = INTERACTION_MODE_NORMAL
    initiator: str | None = None
    pending_queue: list[str] = field(default_factory=list)
    trigger_event_id: str | None = None


@dataclass
class EpisodeBeat:
    """Definition for a single runtime beat."""

    beat_id: str
    label: str
    objective: str
    must_land: str
    exit_condition: str
    suggested_speakers: list[str] = field(default_factory=list)


@dataclass
class BeatState:
    """Runtime beat progress tracker."""

    beats: list[EpisodeBeat] = field(default_factory=list)
    active_index: int = 0
    last_advanced_turn: int = 0
    status: str = BEAT_STATUS_PENDING
    completion_notes: list[str] = field(default_factory=list)


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
    interaction: InteractionState = field(default_factory=InteractionState)
    beat_state: BeatState = field(default_factory=BeatState)


@dataclass
class SeasonContext:
    """定义整季运行期间的共享上下文。"""

    planner_baseline: dict[str, Any]
    run_id: str
    completed_episode_numbers: list[int] = field(default_factory=list)
    season_stats: dict[str, Any] = field(
        default_factory=lambda: {
            "planned_episode_count": 0,
            "completed_episode_count": 0,
            "successful_episode_count": 0,
            "failed_episode_count": 0,
            "episode_status_map": {},
            "episode_status_counts": {},
            "total_turns": 0,
            "average_turns_per_episode": 0.0,
            "summary_status_counts": {},
            "completed_all_planned_episodes": False,
        }
    )
    checkpoint_index: dict[str, str] = field(default_factory=dict)


def get_episode_plan(planner_output: dict[str, Any], episode: int) -> dict[str, Any]:
    """读取指定集数的分集计划。"""
    episodes = planner_output.get("episodes", [])
    if episode <= 0 or episode > len(episodes):
        raise ValueError(f"episode={episode} 不在 planner 输出范围内")
    return episodes[episode - 1]


def merge_current_goal(previous_goal: str, episode_directive: str) -> str:
    """合并上一集遗留目标与本集角色指令。"""
    cleaned_previous_goal = previous_goal.strip()
    cleaned_episode_directive = episode_directive.strip() or DEFAULT_ROLE_GOAL

    if cleaned_previous_goal and cleaned_episode_directive and cleaned_episode_directive != DEFAULT_ROLE_GOAL:
        if cleaned_previous_goal == cleaned_episode_directive:
            return cleaned_previous_goal
        return f"延续目标：{cleaned_previous_goal}；本集要求：{cleaned_episode_directive}"

    if cleaned_previous_goal:
        return cleaned_previous_goal

    return cleaned_episode_directive


def inherit_role_memory(previous_memory: RoleMemory, episode_directive: str) -> RoleMemory:
    """基于上一集记忆构造下一集初始角色状态。"""
    return RoleMemory(
        carryover_summary=previous_memory.carryover_summary,
        carryover_event_tail=[dict(event) for event in previous_memory.carryover_event_tail],
        current_goal=merge_current_goal(previous_memory.current_goal, episode_directive),
        beliefs_about_others=dict(previous_memory.beliefs_about_others),
        unresolved_hook=previous_memory.unresolved_hook,
    )


def build_role_memories(
    global_config: dict[str, Any],
    episode_plan: dict[str, Any],
    previous_role_memories: dict[str, RoleMemory] | None = None,
) -> dict[str, RoleMemory]:
    """根据角色表和单集指令初始化角色记忆。"""
    directives = episode_plan.get("character_directives", {})
    role_memories: dict[str, RoleMemory] = {}

    for role_name in global_config["character_roster"]:
        role_directive = directives.get(role_name, DEFAULT_ROLE_GOAL)
        if previous_role_memories and role_name in previous_role_memories:
            role_memories[role_name] = inherit_role_memory(previous_role_memories[role_name], role_directive)
            continue

        role_memories[role_name] = RoleMemory(current_goal=role_directive)

    return role_memories


def create_runtime_state(
    global_config: dict[str, Any],
    planner_output: dict[str, Any],
    episode: int,
    previous_role_memories: dict[str, RoleMemory] | None = None,
) -> RuntimeState:
    """创建单集运行所需的初始状态 runtime-state。"""
    episode_plan = get_episode_plan(planner_output, episode)
    known_roles = set(global_config["character_roster"].keys())
    scene_roles = [r for r in episode_plan.get("scene_roles", []) if r in known_roles]
    story = StoryContext(
        drama_settings=global_config["drama_settings"],
        logline=global_config["logline"],
        character_roster=global_config["character_roster"],
        current_episode=episode,
        current_scene=episode_plan["place"],
        scene_roles=scene_roles,
    )
    role_memories = build_role_memories(global_config, episode_plan, previous_role_memories=previous_role_memories)
    return RuntimeState(
        story=story,
        role_memories=role_memories,
        interaction=InteractionState(),
    )


def create_season_context(planner_output: dict[str, Any], run_id: str) -> SeasonContext:
    """创建整季运行使用的最薄 SeasonContext。"""
    season_context = SeasonContext(
        planner_baseline=planner_output,
        run_id=run_id,
    )
    season_context.season_stats["planned_episode_count"] = len(planner_output.get("episodes", []))
    return season_context


def update_season_context(
    season_context: SeasonContext,
    episode: int,
    episode_status: str,
    total_turns: int,
    summary_status: dict[str, str],
    episode_succeeded: bool,
) -> None:
    """在单集结束后更新 season 级共享状态。"""
    if episode not in season_context.completed_episode_numbers:
        season_context.completed_episode_numbers.append(episode)
    stats = season_context.season_stats
    stats["completed_episode_count"] = len(season_context.completed_episode_numbers)
    stats["episode_status_map"][str(episode)] = episode_status
    stats["episode_status_counts"][episode_status] = stats["episode_status_counts"].get(episode_status, 0) + 1
    stats["total_turns"] += total_turns
    stats["average_turns_per_episode"] = (
        stats["total_turns"] / stats["completed_episode_count"]
        if stats["completed_episode_count"]
        else 0.0
    )
    if episode_succeeded:
        stats["successful_episode_count"] += 1
    else:
        stats["failed_episode_count"] += 1

    for role_status in summary_status.values():
        stats["summary_status_counts"][role_status] = stats["summary_status_counts"].get(role_status, 0) + 1

    stats["completed_all_planned_episodes"] = (
        stats["completed_episode_count"] == stats["planned_episode_count"]
    )


def get_event_by_id(runtime_state: RuntimeState, event_id: str) -> Event | None:
    """按事件编号从全局日志中回查事件。"""
    for event in runtime_state.story.event_log:
        if event.event_id == event_id:
            return event
    return None


def reset_interaction_state(runtime_state: RuntimeState) -> None:
    """将运行时的多人互动控制状态重置为普通模式。"""
    runtime_state.interaction.mode = INTERACTION_MODE_NORMAL
    runtime_state.interaction.initiator = None
    runtime_state.interaction.pending_queue = []
    runtime_state.interaction.trigger_event_id = None

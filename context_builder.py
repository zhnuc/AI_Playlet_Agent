# 该文件负责为当前发言角色构造工作上下文。
# 它会根据角色可见历史、角色卡和本集指令拼接 prompt，
# 保证角色只基于自己应知的信息继续推进剧情。
from story_state import Event, RuntimeState, get_event_by_id


def format_role_profile(runtime_state: RuntimeState, role_name: str) -> str:
    """格式化当前角色的人设信息。"""
    role_info = runtime_state.story.character_roster[role_name]
    appearance = "、".join(role_info["appearance_tags"])
    personality = "、".join(role_info["personality_tags"])

    return (
        f"{role_name}（{role_info['role_type']}）：\n"
        f"-【基础信息】：{role_info['gender']}，{role_info['age']}岁，{role_info['identity']}\n"
        f"-【外貌】：{appearance}\n"
        f"-【性格】：{personality}\n"
        f"-【口头禅】：{role_info['catchphrase']}\n"
    )


def get_recent_visible_events(role_name: str, runtime_state: RuntimeState, history_window: int = 6) -> list[Event]:
    """获取当前角色最近可见的若干条事件。"""
    event_ids = runtime_state.role_memories[role_name].private_history[-history_window:]
    events: list[Event] = []

    for event_id in event_ids:
        event = get_event_by_id(runtime_state, event_id)
        if event is not None:
            events.append(event)

    return events


def get_uncompressed_visible_events(role_name: str, runtime_state: RuntimeState) -> list[Event]:
    """获取当前角色尚未被 private_summary 覆盖的可见事件。"""
    role_memory = runtime_state.role_memories[role_name]
    event_ids = list(role_memory.private_history)

    if role_memory.summary_until_event_id in event_ids:
        summary_index = event_ids.index(role_memory.summary_until_event_id)
        event_ids = event_ids[summary_index + 1 :]

    events: list[Event] = []
    for event_id in event_ids:
        event = get_event_by_id(runtime_state, event_id)
        if event is not None:
            events.append(event)
    return events


def format_visible_events(events: list[Event]) -> str:
    """将最近可见事件格式化为 prompt 文本。"""
    if not events:
        return "暂无历史互动。"

    formatted_lines = []
    for event in events:
        formatted_lines.append(
            f"[step {event.step}] {event.kind} | {event.speaker}：{event.content}"
        )
    return "\n".join(formatted_lines)


def split_tail_events(events: list[Event], tail_window: int) -> tuple[list[Event], list[Event]]:
    """将未摘要事件拆成旧事件层与尾部细节层。"""
    if tail_window <= 0:
        return events, []
    if len(events) <= tail_window:
        return [], events
    return events[:-tail_window], events[-tail_window:]


def format_beliefs_about_others(beliefs: dict[str, str]) -> str:
    """格式化角色对其他人的当前判断。"""
    if not beliefs:
        return "暂无明确判断。"
    return "\n".join([f"- {role_name}：{belief}" for role_name, belief in beliefs.items()])


def build_role_context(
    role_name: str,
    runtime_state: RuntimeState,
    episode_plan: dict,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    use_fallback_history: bool = False,
) -> str:
    """构造当前角色的一轮混合记忆工作上下文。"""
    role_memory = runtime_state.role_memories[role_name]
    role_profile = format_role_profile(runtime_state, role_name)
    scene_roles = "、".join(runtime_state.story.scene_roles)
    next_candidates = [speaker for speaker in runtime_state.story.scene_roles if speaker != role_name]
    next_speaker_text = "、".join(next_candidates) if next_candidates else "end"
    carryover_summary_text = role_memory.carryover_summary or "暂无上一集延续记忆。"
    private_summary_text = role_memory.private_summary or "当前集暂无已压缩摘要。"
    unresolved_hook_text = role_memory.unresolved_hook or "暂无需要延续的悬念。"
    beliefs_text = format_beliefs_about_others(role_memory.beliefs_about_others)

    if use_fallback_history:
        fallback_events = get_recent_visible_events(role_name, runtime_state, fallback_history_window)
        fallback_history_text = format_visible_events(fallback_events)
        return f"""
# Role:
你是一个演技精湛的专业短剧演员，需要严格站在“{role_name}”的视角继续当前场景互动。

# Global Context:
-【整剧故事核】：{runtime_state.story.logline}
-【当前集数】：第 {runtime_state.story.current_episode} 集
-【当前场景】：{runtime_state.story.current_scene}
-【在场角色】：{scene_roles}
-【本集主线】：{episode_plan["global_plot"]}
-【核心冲突】：{episode_plan["core_conflict"]}
-【本集悬念】：{episode_plan["plot_twist_or_hook"]}

# Character:
{role_profile}
-【本集角色指令】：{episode_plan["character_directives"].get(role_name, "根据现场局势自然推进剧情")}
-【当前角色目标】：{role_memory.current_goal or "根据当前场景自然推进剧情"}

# Fallback Memory:
当前处于降级路径，仅提供最近 {fallback_history_window} 条可见历史：
{fallback_history_text}

# Task:
请只基于以上可见信息继续推进场景。你可以输出：
1. 当前角色的内心想法
2. 当前角色的动作
3. 当前角色的对白
4. 你提议的下一位说话者，或输出 "end" 申请结束当前对话

# next_speaker 约束:
- `next_speaker` 只能从这些值中选择：{next_speaker_text}、end
- 不能输出当前角色自己：{role_name}
- 不要输出场外人物、泛称、长辈、宾客、导演等非角色名
- 如果你认为本集核心冲突已经打透，且当前一句话足以形成悬念或收尾，可以输出 `end`

# Output Format (Strict JSON):
你必须且只能输出严格 JSON，格式如下：
{{
  "{role_name}": {{
    "Inner_Thought": "...",
    "Action": "...",
    "Dialogue": "...",
    "next_speaker": "角色名或end"
  }}
}}
"""

    uncompressed_events = get_uncompressed_visible_events(role_name, runtime_state)
    older_uncompressed_events, tail_events = split_tail_events(uncompressed_events, tail_window)
    older_uncompressed_text = (
        format_visible_events(older_uncompressed_events)
        if older_uncompressed_events else "暂无需要额外压缩的旧事件。"
    )
    tail_history_text = format_visible_events(tail_events) if tail_events else "暂无最近尾部事件。"

    return f"""
# Role:
你是一个演技精湛的专业短剧演员，需要严格站在“{role_name}”的视角继续当前场景互动。

# Global Context:
-【整剧故事核】：{runtime_state.story.logline}
-【当前集数】：第 {runtime_state.story.current_episode} 集
-【当前场景】：{runtime_state.story.current_scene}
-【在场角色】：{scene_roles}
-【本集主线】：{episode_plan["global_plot"]}
-【核心冲突】：{episode_plan["core_conflict"]}
-【本集悬念】：{episode_plan["plot_twist_or_hook"]}

# Character:
{role_profile}
-【本集角色指令】：{episode_plan["character_directives"].get(role_name, "根据现场局势自然推进剧情")}
-【当前角色目标】：{role_memory.current_goal or "根据当前场景自然推进剧情"}
-【跨集记忆摘要】：{carryover_summary_text}
-【对他人的判断】：
{beliefs_text}
-【跨集悬念】：{unresolved_hook_text}

# Episode Memory:
-【当前集已压缩摘要】：{private_summary_text}
-【当前集未压缩旧事件】：
{older_uncompressed_text}

# Tail Events:
以下仅为你当前角色可见的最近 {tail_window} 条原始事件尾巴：
{tail_history_text}

# Task:
请只基于以上可见信息继续推进场景。你可以输出：
1. 当前角色的内心想法
2. 当前角色的动作
3. 当前角色的对白
4. 你提议的下一位说话者，或输出 "end" 申请结束当前对话

# next_speaker 约束:
- `next_speaker` 只能从这些值中选择：{next_speaker_text}、end
- 不能输出当前角色自己：{role_name}
- 不要输出场外人物、泛称、长辈、宾客、导演等非角色名
- 如果你认为本集核心冲突已经打透，且当前一句话足以形成悬念或收尾，可以输出 `end`

# Output Format (Strict JSON):
你必须且只能输出严格 JSON，格式如下：
{{
  "{role_name}": {{
    "Inner_Thought": "...",
    "Action": "...",
    "Dialogue": "...",
    "next_speaker": "角色名或end"
  }}
}}
"""

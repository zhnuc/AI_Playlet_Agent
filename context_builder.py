"""Prompt builder for role-level runtime turns."""
from __future__ import annotations

from typing import Any

from episode_beats import get_active_beat
from event_committer import get_role_visible_events
from story_state import Event, RuntimeState


def format_event(event: Event | dict[str, Any]) -> str:
    """Render an event into the compact prompt-facing line format."""
    if isinstance(event, Event):
        step = event.step
        kind = event.kind
        speaker = event.speaker
        content = event.content
    else:
        step = event.get("step", "?")
        kind = event.get("kind", "event")
        speaker = event.get("speaker", "UNKNOWN")
        content = event.get("content", "")
    return f"[step {step}] {kind} | {speaker}：{content}"


def format_event_block(events: list[Event | dict[str, Any]], empty_text: str) -> str:
    if not events:
        return empty_text
    return "\n".join(format_event(event) for event in events)


def format_beliefs(beliefs: dict[str, str]) -> str:
    if not beliefs:
        return "暂无明确判断。"
    return "\n".join(f"- {role_name}：{judgement}" for role_name, judgement in beliefs.items())


def find_summary_cutoff_index(visible_events: list[Event], summary_until_event_id: str | None) -> int:
    if not summary_until_event_id:
        return 0
    for index, event in enumerate(visible_events):
        if event.event_id == summary_until_event_id:
            return index + 1
    return 0


def split_episode_memory(
    visible_events: list[Event],
    summary_until_event_id: str | None,
    tail_window: int,
) -> tuple[list[Event], list[Event]]:
    summary_cutoff = find_summary_cutoff_index(visible_events, summary_until_event_id)
    tail_count = min(max(tail_window, 0), len(visible_events))
    tail_start = len(visible_events) - tail_count
    tail_start = max(tail_start, summary_cutoff)
    old_events = visible_events[summary_cutoff:tail_start]
    tail_events = visible_events[tail_start:]
    return old_events, tail_events


def build_allowed_next_speakers(role_name: str, runtime_state: RuntimeState) -> list[str]:
    allowed = [
        scene_role
        for scene_role in runtime_state.story.scene_roles
        if scene_role != role_name
    ]
    allowed.append("end")
    return allowed


def build_role_header(role_name: str, runtime_state: RuntimeState) -> str:
    role_card = runtime_state.story.character_roster[role_name]
    appearance = "、".join(role_card.get("appearance_tags", [])) or "暂无外貌标签"
    personality = "、".join(role_card.get("personality_tags", [])) or "暂无性格标签"
    catchphrase = role_card.get("catchphrase", "暂无口头禅")
    role_type = role_card.get("role_type", "角色")

    return f"""
# Role:
你是一个演技精湛的专业短剧演员，需要严格站在“{role_name}”的视角继续当前场景互动。

# Character:
{role_name}（{role_type}）：
-【基础信息】：{role_card.get("gender", "未知")}，{role_card.get("age", "未知")}岁，{role_card.get("identity", "未知身份")}
-【外貌】：{appearance}
-【性格】：{personality}
-【口头禅】：{catchphrase}
""".strip()


def build_global_context(
    role_name: str,
    runtime_state: RuntimeState,
    episode_plan: dict[str, Any],
    include_cross_episode_memory: bool = True,
) -> str:
    role_memory = runtime_state.role_memories[role_name]
    carryover_summary = role_memory.carryover_summary.strip() or "暂无上一集延续记忆。"
    unresolved_hook = role_memory.unresolved_hook.strip() or "暂无需要延续的悬念。"
    directive = episode_plan.get("character_directives", {}).get(role_name, "根据现场局势自然推进剧情。")
    scene_roles = "、".join(runtime_state.story.scene_roles)

    cross_episode_lines: list[str] = []
    if include_cross_episode_memory:
        cross_episode_lines.extend(
            [
                f"-【跨集记忆摘要】：{carryover_summary}",
                "-【对他人的判断】：",
                format_beliefs(role_memory.beliefs_about_others),
                f"-【跨集悬念】：{unresolved_hook}",
            ]
        )

    body = f"""
# Global Context:
-【整剧故事核】：{runtime_state.story.logline}
-【当前集数】：第 {runtime_state.story.current_episode} 集
-【当前场景】：{runtime_state.story.current_scene}
-【在场角色】：{scene_roles}
-【本集主线】：{episode_plan.get("global_plot", "")}
-【核心冲突】：{episode_plan.get("core_conflict", "")}
-【本集悬念】：{episode_plan.get("plot_twist_or_hook", "")}

-【本集角色指令】：{directive}
-【当前角色目标】：{role_memory.current_goal.strip() or directive}
""".strip()
    if cross_episode_lines:
        body = body + "\n" + "\n".join(cross_episode_lines)
    return body


def build_fallback_memory_block(role_name: str, runtime_state: RuntimeState, fallback_history_window: int) -> str:
    role_memory = runtime_state.role_memories[role_name]
    fallback_events = role_memory.carryover_event_tail[-fallback_history_window:] if fallback_history_window > 0 else []
    return f"""
# Fallback Memory:
上一集没有可用的跨集摘要，请仅基于以下跨集尾部原始事件承接剧情：
{format_event_block(fallback_events, "暂无可用的跨集尾部事件。")}
""".strip()


def build_episode_memory_block(role_name: str, runtime_state: RuntimeState, tail_window: int) -> tuple[str, str]:
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    old_events, tail_events = split_episode_memory(
        visible_events,
        role_memory.summary_until_event_id,
        tail_window,
    )

    episode_memory = f"""
# Episode Memory:
-【当前集已压缩摘要】：{role_memory.private_summary.strip() or "当前集暂无已压缩摘要。"}
-【当前集未压缩旧事件】：
{format_event_block(old_events, "暂无需要额外压缩的旧事件。")}
""".strip()

    tail_block = f"""
# Tail Events:
以下仅为你当前角色可见的最近 {tail_window} 条原始事件尾巴：
{format_event_block(tail_events, "暂无最近尾部事件。")}
""".strip()

    return episode_memory, tail_block


def build_queue_block(role_name: str, runtime_state: RuntimeState) -> str:
    interaction = runtime_state.interaction
    if interaction.mode != "pending_replies" or role_name == interaction.initiator:
        return ""

    trigger_line = "暂无可追溯的触发事件。"
    if interaction.trigger_event_id:
        trigger_event = next(
            (event for event in runtime_state.story.event_log if event.event_id == interaction.trigger_event_id),
            None,
        )
        if trigger_event is not None:
            trigger_line = format_event(trigger_event)

    initiator = interaction.initiator or "未知发起者"
    return f"""
# Queue Mode:
- 当前处于多人点名后的队列化回应阶段。
- 发起者是：{initiator}
- 触发你回应的事件是：
{trigger_line}
- 你本轮必须优先回应 {initiator} 刚刚发起的冲突，不得转移话题。
- 你仍需输出标准 JSON，但你本轮的 `next_speakers` 不会接管主路由，请输出空列表 `[]`。
""".strip()


def build_controller_block(
    runtime_state: RuntimeState,
    controller_instruction: str | None,
    soft_turn_limit: int | None,
    hard_turn_limit: int | None,
) -> str:
    active_beat = get_active_beat(runtime_state)
    if active_beat is None and not controller_instruction:
        return ""

    beat_lines = []
    if active_beat is not None:
        beat_lines.extend(
            [
                f"-【当前 Beat】：{active_beat.label}",
                f"-【Beat 目标】：{active_beat.objective}",
                f"-【本 Beat 必须落点】：{active_beat.must_land}",
                f"-【Beat 退出条件】：{active_beat.exit_condition}",
            ]
        )
        if active_beat.suggested_speakers:
            beat_lines.append(f"-【建议推动角色】：{'、'.join(active_beat.suggested_speakers)}")
    if soft_turn_limit is not None:
        beat_lines.append(f"-【软轮数指标】：建议在 {soft_turn_limit} 轮附近完成本集收束。")
    if hard_turn_limit is not None:
        beat_lines.append(f"-【硬轮数上限】：最晚不要拖过第 {hard_turn_limit} 轮。")
    if controller_instruction:
        beat_lines.append(f"-【Controller 临时提示】：{controller_instruction}")

    return "# Runtime Controller:\n" + "\n".join(beat_lines)


def build_director_block(
    scene_instruction: str | None,
    role_instruction: str | None,
    monitor_instruction: str | None,
) -> str:
    notes: list[str] = []
    if scene_instruction:
        notes.append(f"-【导演场景指令】：{scene_instruction}")
    if role_instruction:
        notes.append(f"-【角色定向指令】：{role_instruction}")
    if monitor_instruction:
        notes.append(f"-【监制提示】：{monitor_instruction}")
    if not notes:
        notes.append("暂无额外场外指令。")
    return "# Director & Monitor:\n" + "\n".join(notes)


def build_routing_rules(
    role_name: str,
    runtime_state: RuntimeState,
    retry_invalid_next_speaker: str | None,
) -> str:
    interaction = runtime_state.interaction
    if interaction.mode == "pending_replies" and role_name != interaction.initiator:
        base_rules = [
            "# Routing Rules:",
            "- 当前是队列化回应阶段，本轮 `next_speakers` 只允许输出空列表 `[]`",
            "- 你的任务是回应发起者，不是接管路由",
        ]
    else:
        allowed_values = "、".join(build_allowed_next_speakers(role_name, runtime_state))
        base_rules = [
            "# Routing Rules:",
            f"- `next_speakers` 只能从这些值中选择：{allowed_values}",
            f"- 不能输出当前角色自己：{role_name}",
            "- 不要输出场外人物、泛称、长辈、宾客、导演等非角色名",
            "- 只有当本集冲突已经打透并且悬念已落地时，才允许输出 `end`",
        ]

    if retry_invalid_next_speaker:
        if interaction.mode == "pending_replies" and role_name != interaction.initiator:
            retry_rule = "- 你上一轮的 `next_speaker` 不符合队列规则。本轮必须改为输出空列表 `[]`。"
        else:
            allowed_values = "、".join(build_allowed_next_speakers(role_name, runtime_state))
            retry_rule = (
                f"- 你上一轮的 `next_speaker` 为 `{retry_invalid_next_speaker}`，不在合法路由里。"
                f"你本轮只能从以下值中选择：{allowed_values}。"
                "先保证路由合理，再继续推进本集核心冲突。"
            )
        base_rules.extend(
            [
                "",
                "# Retry Note:",
                retry_rule,
            ]
        )

    return "\n".join(base_rules)


def build_output_contract(role_name: str) -> str:
    return f"""
# Task:
请只基于以上可见信息继续推进场景。你可以输出：
1. 当前角色的内心想法
2. 当前角色的动作
3. 当前角色的对白
4. 你提议的下一位说话者列表，或输出 `["end"]` 申请结束当前对话

# Output Format (Strict JSON):
你必须且只能输出严格 JSON，格式如下：
{{
  "{role_name}": {{
    "Inner_Thought": "...",
    "Action": "...",
    "Dialogue": "...",
    "next_speakers": ["角色名A", "角色名B"]
  }}
}}
""".strip()


def build_role_context(
    role_name: str,
    runtime_state: RuntimeState,
    episode_plan: dict[str, Any],
    tail_window: int = 4,
    fallback_history_window: int = 6,
    use_fallback_history: bool = False,
    retry_invalid_next_speaker: str | None = None,
    scene_instruction: str | None = None,
    role_instruction: str | None = None,
    monitor_instruction: str | None = None,
    controller_instruction: str | None = None,
    soft_turn_limit: int | None = None,
    hard_turn_limit: int | None = None,
) -> str:
    """Build the runtime prompt for a single role turn."""
    sections = [
        build_role_header(role_name, runtime_state),
        build_global_context(
            role_name,
            runtime_state,
            episode_plan,
            include_cross_episode_memory=not use_fallback_history,
        ),
    ]

    controller_block = build_controller_block(
        runtime_state,
        controller_instruction=controller_instruction,
        soft_turn_limit=soft_turn_limit,
        hard_turn_limit=hard_turn_limit,
    )
    if controller_block:
        sections.append(controller_block)

    queue_block = build_queue_block(role_name, runtime_state)
    if queue_block:
        sections.append(queue_block)

    if use_fallback_history:
        sections.append(build_fallback_memory_block(role_name, runtime_state, fallback_history_window))
    else:
        episode_memory_block, tail_block = build_episode_memory_block(role_name, runtime_state, tail_window)
        sections.extend([episode_memory_block, tail_block])

    sections.append(build_director_block(scene_instruction, role_instruction, monitor_instruction))
    sections.append(build_routing_rules(role_name, runtime_state, retry_invalid_next_speaker))
    sections.append(build_output_contract(role_name))
    return "\n\n".join(section for section in sections if section).strip() + "\n"

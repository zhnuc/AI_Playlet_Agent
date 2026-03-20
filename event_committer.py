# 该文件负责把角色单轮输出提交为剧情事件。
# 它会拆分 thought、action、dialogue 三类内容，
#* 规定：thought -> 只自己可见； action/dialogue -> 场上所有 scene_roles 可见。
# 并同步更新全局事件日志和各角色的私有可见历史。
from typing import Any

from Agent_model import Summary_Agent, is_valid_summary_response
from story_state import Event, RuntimeState, get_event_by_id


def build_event_id(runtime_state: RuntimeState) -> str:
    """为新事件生成递增编号。"""
    return f"e{len(runtime_state.story.event_log) + 1}"


def append_event(runtime_state: RuntimeState, event: Event) -> None:
    """将事件写入全局日志并分发到可见角色记忆中。"""
    runtime_state.story.event_log.append(event)
    for role_name in event.visible_to:
        runtime_state.role_memories[role_name].private_history.append(event.event_id)


def build_event(
    runtime_state: RuntimeState,
    step: int,
    kind: str,
    speaker: str,
    content: str,
    visible_to: list[str],
) -> Event:
    """构造单条事件对象。"""
    return Event(
        event_id=build_event_id(runtime_state),
        step=step,
        episode=runtime_state.story.current_episode,
        scene=runtime_state.story.current_scene,
        kind=kind,
        speaker=speaker,
        content=content,
        visible_to=visible_to,
    )


def commit_turn_result(runtime_state: RuntimeState, speaker: str, turn_output: dict) -> list[Event]:
    """提交当前角色的一轮输出并写入事件日志。"""
    runtime_state.story.current_turn += 1
    step = runtime_state.story.current_turn
    committed_events: list[Event] = []

    thought = turn_output.get("Inner_Thought", "").strip()
    action = turn_output.get("Action", "").strip()
    dialogue = turn_output.get("Dialogue", "").strip()

    if thought:
        event = build_event(runtime_state, step, "thought", speaker, thought, [speaker])
        append_event(runtime_state, event)
        committed_events.append(event)

    if action:
        event = build_event(
            runtime_state,
            step,
            "action",
            speaker,
            action,
            list(runtime_state.story.scene_roles),
        )
        append_event(runtime_state, event)
        committed_events.append(event)

    if dialogue:
        event = build_event(
            runtime_state,
            step,
            "dialogue",
            speaker,
            dialogue,
            list(runtime_state.story.scene_roles),
        )
        append_event(runtime_state, event)
        committed_events.append(event)

    return committed_events


def get_role_visible_events(role_name: str, runtime_state: RuntimeState) -> list[Event]:
    """按角色 private_history 回查其当前集可见事件。"""
    events: list[Event] = []
    for event_id in runtime_state.role_memories[role_name].private_history:
        event = get_event_by_id(runtime_state, event_id)
        if event is not None:
            events.append(event)
    return events


def serialize_events_for_summary(events: list[Event]) -> list[dict[str, Any]]:
    """将事件对象整理为摘要 agent 可消费的结构化输入。"""
    return [
        {
            "event_id": event.event_id,
            "step": event.step,
            "kind": event.kind,
            "speaker": event.speaker,
            "content": event.content,
        }
        for event in events
    ]


def serialize_events_for_carryover_tail(events: list[Event], fallback_history_window: int = 6) -> list[dict[str, Any]]:
    """截取并序列化跨集 fallback 需要保留的尾部事件。"""
    tail_events = events[-fallback_history_window:] if fallback_history_window > 0 else []
    return [
        {
            "event_id": event.event_id,
            "step": event.step,
            "kind": event.kind,
            "speaker": event.speaker,
            "content": event.content,
        }
        for event in tail_events
    ]


def build_role_summary_input(role_name: str, runtime_state: RuntimeState) -> dict[str, Any]:
    """整理单角色的摘要输入载荷。"""
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    return {
        "role_name": role_name,
        "episode": runtime_state.story.current_episode,
        "scene": runtime_state.story.current_scene,
        "current_goal": role_memory.current_goal,
        "carryover_summary": role_memory.carryover_summary,
        "beliefs_about_others": dict(role_memory.beliefs_about_others),
        "unresolved_hook": role_memory.unresolved_hook,
        "visible_events": serialize_events_for_summary(visible_events),
    }


def apply_summary_to_role_memory(role_name: str, runtime_state: RuntimeState, summary_payload: dict[str, Any]) -> None:
    """将合法摘要结果回写到对应角色记忆中。"""
    role_memory = runtime_state.role_memories[role_name]
    visible_events = get_role_visible_events(role_name, runtime_state)
    summary_text = summary_payload.get("carryover_summary", "").strip()
    current_goal = summary_payload.get("current_goal", "").strip()

    role_memory.private_summary = summary_text
    role_memory.summary_until_event_id = visible_events[-1].event_id if visible_events else None
    role_memory.carryover_summary = summary_text
    if current_goal:
        role_memory.current_goal = current_goal
    role_memory.beliefs_about_others = dict(summary_payload.get("beliefs_about_others", {}))
    role_memory.unresolved_hook = summary_payload.get("unresolved_hook", "").strip()


def save_role_carryover_event_tail(
    role_name: str,
    runtime_state: RuntimeState,
    fallback_history_window: int = 6,
) -> None:
    """为角色保存跨集 fallback 使用的原始事件尾巴。"""
    visible_events = get_role_visible_events(role_name, runtime_state)
    runtime_state.role_memories[role_name].carryover_event_tail = serialize_events_for_carryover_tail(
        visible_events,
        fallback_history_window=fallback_history_window,
    )


def finalize_role_memories_for_next_episode(
    runtime_state: RuntimeState,
    summary_agent: Summary_Agent | None,
    fallback_history_window: int = 6,
) -> dict[str, str]:
    """在 episode 收尾阶段统一生成并回写角色跨集记忆。"""
    roles_to_summarize = [
        role_name
        for role_name, role_memory in runtime_state.role_memories.items()
        if role_memory.private_history
    ]
    if not roles_to_summarize:
        return {}

    for role_name in roles_to_summarize:
        save_role_carryover_event_tail(
            role_name,
            runtime_state,
            fallback_history_window=fallback_history_window,
        )

    if summary_agent is None:
        return {role_name: "summary_agent_missing" for role_name in roles_to_summarize}

    summary_inputs = {
        role_name: build_role_summary_input(role_name, runtime_state)
        for role_name in roles_to_summarize
    }
    summary_result = summary_agent.generate_role_summaries(summary_inputs)
    if isinstance(summary_result, str):
        return {role_name: summary_result for role_name in roles_to_summarize}

    summary_status: dict[str, str] = {}
    for role_name in roles_to_summarize:
        summary_payload = summary_result.get(role_name)
        if not isinstance(summary_payload, dict) or not is_valid_summary_response(summary_payload):
            summary_status[role_name] = "schema_error"
            continue
        apply_summary_to_role_memory(role_name, runtime_state, summary_payload)
        summary_status[role_name] = "updated"

    return summary_status

# 该文件负责把角色单轮输出提交为剧情事件。
# 它会拆分 thought、action、dialogue 三类内容，
#* 规定：thought -> 只自己可见； action/dialogue -> 场上所有 scene_roles 可见。
# 并同步更新全局事件日志和各角色的私有可见历史。
from story_state import Event, RuntimeState


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

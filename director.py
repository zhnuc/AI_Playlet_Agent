# 该文件实现轻量级导演规则。
# 主要用于在角色提出 `end` 时判断本集是否允许结束，
# 避免对话在冲突尚未展开时过早收束。
from story_state import RuntimeState


def should_end_episode(runtime_state: RuntimeState, min_turns: int = 4) -> bool:
    """用轻量规则判断本集是否允许结束。"""
    if runtime_state.story.current_turn < min_turns:
        return False

    dialogue_events = [event for event in runtime_state.story.event_log if event.kind == "dialogue"]
    action_events = [event for event in runtime_state.story.event_log if event.kind == "action"]
    active_speakers = {event.speaker for event in dialogue_events}

    if len(dialogue_events) < 2:
        return False
    if len(action_events) < 1:
        return False
    if len(active_speakers) < 2:
        return False

    return True

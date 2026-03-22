# 该文件实现最小化的说话人调度规则。
#* 判断 next_speaker 是否合法并给出下一位角色或结束信号
#* 待扩展：处理 冲突/并发 情况
# 它负责识别 `end` 信号、校验下一位发言角色是否合法，
# 并在必要时提供简单的 fallback 路由结果。
def is_end_signal(next_speaker: str | None) -> bool:
    """判断角色是否申请结束当前对话。"""
    return (next_speaker or "").strip().lower() == "end"


def get_allowed_next_speakers(
    current_speaker: str,
    scene_roles: list[str],
    valid_roles: list[str],
) -> list[str]:
    """获取当前角色本轮允许的下一位说话者列表。"""
    return [
        role
        for role in scene_roles
        if role in valid_roles and role != current_speaker
    ]


def is_valid_next_speaker(
    current_speaker: str,
    proposed_next_speaker: str | None,
    scene_roles: list[str],
    valid_roles: list[str],
) -> bool:
    """判断 next_speaker 是否属于当前场景的合法范围。"""
    proposed = (proposed_next_speaker or "").strip()
    if is_end_signal(proposed):
        return True
    return proposed in get_allowed_next_speakers(current_speaker, scene_roles, valid_roles)


def resolve_next_speaker(
    current_speaker: str,
    proposed_next_speaker: str | None,
    scene_roles: list[str],
    valid_roles: list[str],
) -> str | None:
    """校验下一位说话者是否合法，并返回可继续推进的结果。"""
    proposed = (proposed_next_speaker or "").strip()

    if is_end_signal(proposed):
        return "end"

    if proposed and proposed in get_allowed_next_speakers(current_speaker, scene_roles, valid_roles):
        return proposed
    return None

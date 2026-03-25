"""该文件实现短剧多角色调度规则。"""

END_SIGNAL = "end"
END_REQUEST_SIGNAL = "end_request"


def normalize_candidate_name(candidate: str | None) -> str:
    """标准化单个候选说话人。"""
    normalized = (candidate or "").strip()
    if normalized.lower() in {END_SIGNAL, END_REQUEST_SIGNAL}:
        return END_SIGNAL
    return normalized


def extract_next_speakers(turn_output: dict) -> list[str]:
    """从角色输出中提取并归一化下一位说话者列表。"""
    raw_next_speakers = turn_output.get("next_speakers")
    if isinstance(raw_next_speakers, list):
        candidates = raw_next_speakers
    else:
        raw_next_speaker = turn_output.get("next_speaker")
        if isinstance(raw_next_speaker, list):
            candidates = raw_next_speaker
        elif isinstance(raw_next_speaker, str):
            candidates = [raw_next_speaker]
        else:
            candidates = []

    normalized_candidates: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        normalized = normalize_candidate_name(candidate)
        if normalized and normalized not in normalized_candidates:
            normalized_candidates.append(normalized)
    return normalized_candidates


def is_end_signal(next_speaker: str | None) -> bool:
    """判断角色是否申请结束当前对话。"""
    return normalize_candidate_name(next_speaker) == END_SIGNAL


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


def are_valid_next_speakers(
    current_speaker: str,
    proposed_next_speakers: list[str],
    scene_roles: list[str],
    valid_roles: list[str],
) -> bool:
    """判断归一化后的下一位说话者列表是否合法。"""
    if not proposed_next_speakers:
        return False

    if END_SIGNAL in proposed_next_speakers:
        return proposed_next_speakers == [END_SIGNAL]

    allowed_next_speakers = get_allowed_next_speakers(current_speaker, scene_roles, valid_roles)
    return all(candidate in allowed_next_speakers for candidate in proposed_next_speakers)


def is_valid_next_speaker(
    current_speaker: str,
    proposed_next_speaker: str | list[str] | None,
    scene_roles: list[str],
    valid_roles: list[str],
) -> bool:
    """兼容旧接口，判断下一位说话者是否属于当前场景的合法范围。"""
    if isinstance(proposed_next_speaker, list):
        candidates = [
            normalize_candidate_name(candidate)
            for candidate in proposed_next_speaker
            if isinstance(candidate, str)
        ]
    else:
        candidate = normalize_candidate_name(proposed_next_speaker)
        candidates = [candidate] if candidate else []
    return are_valid_next_speakers(current_speaker, candidates, scene_roles, valid_roles)


def resolve_next_speakers(
    current_speaker: str,
    proposed_next_speakers: list[str],
    scene_roles: list[str],
    valid_roles: list[str],
) -> list[str] | None:
    """校验下一位说话者列表是否合法。"""
    if not are_valid_next_speakers(current_speaker, proposed_next_speakers, scene_roles, valid_roles):
        return None
    return proposed_next_speakers


def resolve_next_speaker(
    current_speaker: str,
    proposed_next_speaker: str | list[str] | None,
    scene_roles: list[str],
    valid_roles: list[str],
) -> str | None:
    """兼容旧接口，返回单一下一位说话者或结束信号。"""
    if isinstance(proposed_next_speaker, list):
        candidates = [
            normalize_candidate_name(candidate)
            for candidate in proposed_next_speaker
            if isinstance(candidate, str)
        ]
    else:
        candidate = normalize_candidate_name(proposed_next_speaker)
        candidates = [candidate] if candidate else []
    resolved = resolve_next_speakers(current_speaker, candidates, scene_roles, valid_roles)
    if not resolved or len(resolved) != 1:
        return None
    return resolved[0]

# 该文件实现单集单场景的主运行循环。
# 它负责串联 planner、上下文构造、角色调用、事件提交、
# 路由决策、日志写入和 episode 收束判断。
from Agent_model import Planner_Agent, Role_Agent_Box, Summary_Agent, load_env
from context_builder import build_role_context
from director import should_end_episode
from event_committer import commit_turn_result, finalize_role_memories_for_next_episode
from global_config import global_config
from log_writer import (
    append_turn_log,
    finalize_episode_log,
    initialize_episode_log,
    initialize_season_log_directory,
    serialize_role_memories,
    serialize_season_context,
    write_episode_checkpoint,
    write_season_context,
    write_season_summary,
)
from prompt import planner_agent_prompt
from scheduler import is_end_signal, is_valid_next_speaker, resolve_next_speaker
from story_state import (
    RoleMemory,
    RuntimeState,
    create_runtime_state,
    create_season_context,
    get_episode_plan,
    update_season_context,
)

SEASON_CONTINUE_STATUSES = {"ended", "handoff", "max_turns_reached"}


def should_use_fallback_history(role_memory: RoleMemory) -> bool:
    """判断当前角色是否应自动进入跨集 fallback prompt。"""
    return (
        not role_memory.carryover_summary.strip()
        and bool(role_memory.carryover_event_tail)
        and not role_memory.private_history
    )


def complete_episode_run(
    runtime_state: RuntimeState,
    summary_agent: Summary_Agent | None,
    log_path,
    result_status: str,
    last_speaker: str,
    turn_trace: list[dict],
    fallback_history_window: int,
) -> dict:
    """统一处理 episode 收尾日志与跨集记忆回写。"""
    summary_status = finalize_role_memories_for_next_episode(
        runtime_state,
        summary_agent,
        fallback_history_window=fallback_history_window,
    )
    finalize_episode_log(
        log_path,
        runtime_state=runtime_state,
        result_status=result_status,
        last_speaker=last_speaker,
        total_turns=runtime_state.story.current_turn,
        summary_status=summary_status,
    )
    return {
        "status": result_status,
        "runtime_state": runtime_state,
        "last_speaker": last_speaker,
        "turn_trace": turn_trace,
        "summary_status": summary_status,
    }


def is_episode_success_status(status: str) -> bool:
    """判断单集状态是否允许 season 继续执行下一集。"""
    return status in SEASON_CONTINUE_STATUSES


def build_episode_checkpoint_payload(
    run_id: str,
    episode: int,
    total_episode_count: int,
    final_role_memories: dict[str, RoleMemory],
    season_context_payload: dict,
) -> dict:
    """构造单集结束后的 checkpoint 内容。"""
    remaining_episode_numbers = list(range(episode + 1, total_episode_count + 1))
    serialized_role_memories = serialize_role_memories(final_role_memories)
    return {
        "run_id": run_id,
        "completed_episode": episode,
        "planner_baseline_ref": "planner_output.json",
        "role_memories": serialized_role_memories,
        "completed_episode_numbers": list(season_context_payload["completed_episode_numbers"]),
        "season_stats": dict(season_context_payload["season_stats"]),
        "remaining_episode_numbers": remaining_episode_numbers,
        "replan_context_stub": {
            "completed_episode": episode,
            "remaining_episode_count": len(remaining_episode_numbers),
            "carryover_role_memories": serialized_role_memories,
        },
    }


def build_season_summary(
    run_id: str,
    total_episode_count: int,
    stop_reason: str | None,
    season_context_payload: dict,
) -> dict:
    """基于 SeasonContext 汇总当前整季运行结果。"""
    season_stats = dict(season_context_payload["season_stats"])
    return {
        "run_id": run_id,
        "planner_baseline_ref": "planner_output.json",
        "planned_episode_count": total_episode_count,
        "completed_episode_numbers": list(season_context_payload["completed_episode_numbers"]),
        "completed_episode_count": season_stats["completed_episode_count"],
        "successful_episode_count": season_stats["successful_episode_count"],
        "failed_episode_count": season_stats["failed_episode_count"],
        "episode_status_map": dict(season_stats["episode_status_map"]),
        "episode_status_counts": dict(season_stats["episode_status_counts"]),
        "total_turns": season_stats["total_turns"],
        "average_turns_per_episode": season_stats["average_turns_per_episode"],
        "summary_status_counts": dict(season_stats["summary_status_counts"]),
        "completed_all_planned_episodes": season_stats["completed_all_planned_episodes"],
        "stop_reason": stop_reason,
    }


def resolve_episode_start_speaker(episode_plan: dict, valid_roles: list[str]) -> str:
    """将 planner 给出的首发角色收敛到当前场景的合法发言者。"""
    first_speaker = (episode_plan.get("first_speaker") or "").strip()
    scene_roles = [role for role in episode_plan.get("scene_roles", []) if role in valid_roles]

    if first_speaker and first_speaker in scene_roles:
        return first_speaker

    if scene_roles:
        return scene_roles[0]

    if valid_roles:
        return valid_roles[0]

    raise ValueError("当前没有可用的合法首发角色")


def generate_role_turn_with_route_retry(
    current_speaker: str,
    runtime_state: RuntimeState,
    episode_plan: dict,
    role_agent_box: Role_Agent_Box,
    valid_roles: list[str],
    tail_window: int,
    fallback_history_window: int,
) -> dict[str, object]:
    """调用角色 agent，并在 next_speaker 非法时最多重试一次。"""
    use_fallback_history = should_use_fallback_history(runtime_state.role_memories[current_speaker])
    invalid_next_speaker: str | None = None
    retry_count = 0
    prompt = ""
    final_turn_output: dict | None = None

    for attempt in range(2):
        prompt = build_role_context(
            current_speaker,
            runtime_state,
            episode_plan,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
            use_fallback_history=use_fallback_history,
            retry_invalid_next_speaker=invalid_next_speaker,
        )
        turn_output = role_agent_box.generate_role_response(current_speaker, prompt)
        if isinstance(turn_output, str):
            return {
                "status": turn_output,
                "turn_output": None,
                "prompt": prompt,
                "use_fallback_history": use_fallback_history,
                "retry_count": retry_count,
                "invalid_next_speaker": invalid_next_speaker,
            }

        final_turn_output = turn_output
        proposed_next_speaker = turn_output.get("next_speaker")
        if is_valid_next_speaker(
            current_speaker,
            proposed_next_speaker,
            runtime_state.story.scene_roles,
            valid_roles,
        ):
            return {
                "status": "ok",
                "turn_output": turn_output,
                "prompt": prompt,
                "use_fallback_history": use_fallback_history,
                "retry_count": retry_count,
                "invalid_next_speaker": None,
            }

        invalid_next_speaker = proposed_next_speaker
        if attempt == 0:
            retry_count = 1

    return {
        "status": "handoff",
        "turn_output": final_turn_output,
        "prompt": prompt,
        "use_fallback_history": use_fallback_history,
        "retry_count": retry_count,
        "invalid_next_speaker": invalid_next_speaker,
    }


def run_episode(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    episode: int,
    summary_agent: Summary_Agent | None = None,
    previous_role_memories: dict[str, RoleMemory] | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
) -> dict:
    """运行单集单场景的最小主循环。"""
    runtime_state: RuntimeState = create_runtime_state(
        global_config,
        planner_output,
        episode,
        previous_role_memories=previous_role_memories,
    )
    episode_plan = get_episode_plan(planner_output, episode)
    valid_roles = list(global_config["character_roster"].keys())
    current_speaker = resolve_episode_start_speaker(episode_plan, valid_roles)
    turn_trace: list[dict] = []
    log_path = initialize_episode_log(runtime_state, episode_plan, log_dir=log_dir)

    #* 每一轮循环就是一个 agent 的 turn
    for _ in range(max_turns):
        turn_result = generate_role_turn_with_route_retry(
            current_speaker,
            runtime_state,
            episode_plan,
            role_agent_box,
            valid_roles,
            tail_window,
            fallback_history_window=fallback_history_window,
        )

        prompt = turn_result["prompt"]
        use_fallback_history = bool(turn_result["use_fallback_history"])
        if turn_result["status"] in {"api_error", "format_error", "key_error"}:
            return complete_episode_run(
                runtime_state=runtime_state,
                summary_agent=summary_agent,
                log_path=log_path,
                result_status=str(turn_result["status"]),
                last_speaker=current_speaker,
                turn_trace=turn_trace,
                fallback_history_window=fallback_history_window,
            )

        turn_output = turn_result["turn_output"]
        if not isinstance(turn_output, dict):
            return complete_episode_run(
                runtime_state=runtime_state,
                summary_agent=summary_agent,
                log_path=log_path,
                result_status="api_error",
                last_speaker=current_speaker,
                turn_trace=turn_trace,
                fallback_history_window=fallback_history_window,
            )

        proposed_next_speaker = turn_output.get("next_speaker")
        turn_record = {
            "step": runtime_state.story.current_turn,
            "speaker": current_speaker,
            "proposed_next_speaker": proposed_next_speaker,
            "route_retry_count": turn_result["retry_count"],
        }

        if is_end_signal(proposed_next_speaker): # 角色申请结束本集剧情
            if should_end_episode(runtime_state): # 交由 director 判断
                committed_events = commit_turn_result(runtime_state, current_speaker, turn_output)
                turn_record["resolved_next_speaker"] = "end"
                turn_record["status"] = "ended"
                turn_trace.append(turn_record)
                append_turn_log(
                    log_path,
                    step=runtime_state.story.current_turn,
                    speaker=current_speaker,
                    prompt=prompt,
                    use_fallback_history=use_fallback_history,
                    turn_output=turn_output,
                    committed_events=committed_events,
                    proposed_next_speaker=turn_output.get("next_speaker"),
                    resolved_next_speaker="end",
                    status="ended",
                )
                return complete_episode_run(
                    runtime_state=runtime_state,
                    summary_agent=summary_agent,
                    log_path=log_path,
                    result_status="ended",
                    last_speaker=current_speaker,
                    turn_trace=turn_trace,
                    fallback_history_window=fallback_history_window,
                )
            proposed_next_speaker = None

        if turn_result["status"] == "handoff":
            return complete_episode_run(
                runtime_state=runtime_state,
                summary_agent=summary_agent,
                log_path=log_path,
                result_status="handoff",
                last_speaker=current_speaker,
                turn_trace=turn_trace,
                fallback_history_window=fallback_history_window,
            )

        # 将这一轮输出提交到状态，更新 runtime_state
        committed_events = commit_turn_result(runtime_state, current_speaker, turn_output)
        # 解析下一位 speaker
        next_speaker = resolve_next_speaker(
            current_speaker=current_speaker,
            proposed_next_speaker=proposed_next_speaker,
            scene_roles=runtime_state.story.scene_roles,
            valid_roles=valid_roles,
        )
        turn_record["resolved_next_speaker"] = next_speaker
        turn_record["status"] = "continue" if next_speaker else "handoff"
        turn_trace.append(turn_record)
        append_turn_log(
            log_path,
            step=runtime_state.story.current_turn,
            speaker=current_speaker,
            prompt=prompt,
            use_fallback_history=use_fallback_history,
            turn_output=turn_output,
            committed_events=committed_events,
            proposed_next_speaker=turn_output.get("next_speaker"),
            resolved_next_speaker=next_speaker,
            status=turn_record["status"],
        )

        if next_speaker is None:
            return complete_episode_run(
                runtime_state=runtime_state,
                summary_agent=summary_agent,
                log_path=log_path,
                result_status="handoff",
                last_speaker=current_speaker,
                turn_trace=turn_trace,
                fallback_history_window=fallback_history_window,
            )

        current_speaker = next_speaker

    return complete_episode_run(
        runtime_state=runtime_state,
        summary_agent=summary_agent,
        log_path=log_path,
        result_status="max_turns_reached",
        last_speaker=current_speaker,
        turn_trace=turn_trace,
        fallback_history_window=fallback_history_window,
    )


def run_season(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    summary_agent: Summary_Agent | None = None,
    start_episode: int = 1,
    continuity_enabled: bool = True,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
) -> dict:
    """按 planner 顺序连续运行多集，并默认承接上一集角色记忆。"""
    episodes = planner_output.get("episodes", [])
    total_episode_count = len(episodes)

    if start_episode <= 0 or start_episode > total_episode_count:
        raise ValueError(f"start_episode={start_episode} 不在 planner 输出范围内")

    episode_results: list[dict] = []
    previous_role_memories: dict[str, RoleMemory] | None = None
    final_role_memories: dict[str, RoleMemory] | None = None
    run_id, season_log_dir = initialize_season_log_directory(planner_output, log_dir=log_dir)
    season_context = create_season_context(planner_output, run_id)
    write_season_context(season_log_dir, season_context)

    for episode in range(start_episode, total_episode_count + 1):
        episode_result = run_episode(
            planner_output,
            role_agent_box,
            episode,
            summary_agent=summary_agent,
            previous_role_memories=previous_role_memories if continuity_enabled else None,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
            max_turns=max_turns,
            log_dir=str(season_log_dir),
        )
        season_episode_result = {"episode": episode, **episode_result}
        episode_results.append(season_episode_result)
        final_role_memories = episode_result["runtime_state"].role_memories
        episode_succeeded = is_episode_success_status(episode_result["status"])
        update_season_context(
            season_context,
            episode,
            episode_result["status"],
            total_turns=episode_result["runtime_state"].story.current_turn,
            summary_status=episode_result["summary_status"],
            episode_succeeded=episode_succeeded,
        )
        season_context_payload = serialize_season_context(season_context)
        checkpoint_payload = build_episode_checkpoint_payload(
            run_id,
            episode,
            total_episode_count,
            final_role_memories,
            season_context_payload,
        )
        checkpoint_path = write_episode_checkpoint(season_log_dir, episode, checkpoint_payload)
        season_context.checkpoint_index[str(episode)] = str(checkpoint_path.relative_to(season_log_dir))
        write_season_context(season_log_dir, season_context)

        if not episode_succeeded:
            season_context_payload = serialize_season_context(season_context)
            season_summary = build_season_summary(
                run_id,
                total_episode_count,
                stop_reason=episode_result["status"],
                season_context_payload=season_context_payload,
            )
            write_season_summary(season_log_dir, season_summary)
            return {
                "status": "stopped",
                "stop_reason": episode_result["status"],
                "run_id": run_id,
                "season_log_dir": str(season_log_dir),
                "season_context": season_context_payload,
                "season_summary": season_summary,
                "start_episode": start_episode,
                "planned_episode_count": total_episode_count,
                "completed_episode_count": len(episode_results),
                "completed_episode_numbers": [result["episode"] for result in episode_results],
                "episode_results": episode_results,
                "final_role_memories": final_role_memories,
            }

        previous_role_memories = final_role_memories

    season_context_payload = serialize_season_context(season_context)
    season_summary = build_season_summary(
        run_id,
        total_episode_count,
        stop_reason=None,
        season_context_payload=season_context_payload,
    )
    write_season_summary(season_log_dir, season_summary)
    return {
        "status": "completed",
        "stop_reason": None,
        "run_id": run_id,
        "season_log_dir": str(season_log_dir),
        "season_context": season_context_payload,
        "season_summary": season_summary,
        "start_episode": start_episode,
        "planned_episode_count": total_episode_count,
        "completed_episode_count": len(episode_results),
        "completed_episode_numbers": [result["episode"] for result in episode_results],
        "episode_results": episode_results,
        "final_role_memories": final_role_memories or {},
    }

# test
def run_demo_episode(episode: int = 1) -> dict:
    """用真实模型调用跑通单集 demo。"""
    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    planner_output = planner_agent.generate_outline(planner_agent_prompt)
    if isinstance(planner_output, str):
        return {"status": planner_output}

    role_agent_box = Role_Agent_Box(base_url, api_key, model)
    summary_agent = Summary_Agent(base_url, api_key, model)
    return run_episode(planner_output, role_agent_box, episode, summary_agent=summary_agent)


if __name__ == "__main__":
    print(run_demo_episode())

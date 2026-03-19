# 该文件实现单集单场景的主运行循环。
# 它负责串联 planner、上下文构造、角色调用、事件提交、
# 路由决策、日志写入和 episode 收束判断。
from Agent_model import Planner_Agent, Role_Agent_Box, Summary_Agent, load_env
from context_builder import build_role_context
from director import should_end_episode
from event_committer import commit_turn_result, finalize_role_memories_for_next_episode
from global_config import global_config
from log_writer import append_turn_log, finalize_episode_log, initialize_episode_log
from prompt import planner_agent_prompt
from scheduler import is_end_signal, resolve_next_speaker
from story_state import RoleMemory, RuntimeState, create_runtime_state, get_episode_plan


def complete_episode_run(
    runtime_state: RuntimeState,
    summary_agent: Summary_Agent | None,
    log_path,
    result_status: str,
    last_speaker: str,
    turn_trace: list[dict],
) -> dict:
    """统一处理 episode 收尾日志与跨集记忆回写。"""
    summary_status = finalize_role_memories_for_next_episode(runtime_state, summary_agent)
    finalize_episode_log(
        log_path,
        result_status=result_status,
        last_speaker=last_speaker,
        total_turns=runtime_state.story.current_turn,
    )
    return {
        "status": result_status,
        "runtime_state": runtime_state,
        "last_speaker": last_speaker,
        "turn_trace": turn_trace,
        "summary_status": summary_status,
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
    current_speaker = episode_plan["first_speaker"]
    valid_roles = list(global_config["character_roster"].keys())
    turn_trace: list[dict] = []
    log_path = initialize_episode_log(runtime_state, episode_plan, log_dir=log_dir)

    #* 每一轮循环就是一个 agent 的 turn
    for _ in range(max_turns):
        # 构造当前角色的输入
        prompt = build_role_context(
            current_speaker,
            runtime_state,
            episode_plan,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
        )
        # 调用 agent llm，生成这一轮输出
        # 返回 thought + action + dialogue + next_speaker 4 个字段内容
        turn_output = role_agent_box.generate_role_response(current_speaker, prompt)
        if isinstance(turn_output, str):
            return complete_episode_run(
                runtime_state=runtime_state,
                summary_agent=summary_agent,
                log_path=log_path,
                result_status=turn_output,
                last_speaker=current_speaker,
                turn_trace=turn_trace,
            )
        # 将这一轮输出提交到状态，更新 runtime_state
        commit_turn_result(runtime_state, current_speaker, turn_output)
        # 读取模型提议的下一位 speaker
        proposed_next_speaker = turn_output.get("next_speaker")
        turn_record = {
            "step": runtime_state.story.current_turn,
            "speaker": current_speaker,
            "proposed_next_speaker": proposed_next_speaker,
        }

        if is_end_signal(proposed_next_speaker): # 角色申请结束本集剧情
            if should_end_episode(runtime_state): # 交由 director 判断
                turn_record["resolved_next_speaker"] = "end"
                turn_record["status"] = "ended"
                turn_trace.append(turn_record)
                append_turn_log(
                    log_path,
                    step=runtime_state.story.current_turn,
                    speaker=current_speaker,
                    turn_output=turn_output,
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
                )
            proposed_next_speaker = None
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
            turn_output=turn_output,
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
            )

        current_speaker = next_speaker

    return complete_episode_run(
        runtime_state=runtime_state,
        summary_agent=summary_agent,
        log_path=log_path,
        result_status="max_turns_reached",
        last_speaker=current_speaker,
        turn_trace=turn_trace,
    )

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

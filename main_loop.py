# 该文件实现单集单场景的主运行循环。
# 它负责串联 planner、上下文构造、角色调用、事件提交、
# 路由决策、日志写入和 episode 收束判断。
from Agent_model import Planner_Agent, Role_Agent_Box, load_env
from context_builder import build_role_context
from director import should_end_episode
from event_committer import commit_turn_result
from global_config import global_config
from log_writer import append_turn_log, finalize_episode_log, initialize_episode_log
from prompt import planner_agent_prompt
from scheduler import is_end_signal, resolve_next_speaker
from story_state import RuntimeState, create_runtime_state, get_episode_plan


def run_episode(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    episode: int,
    history_window: int = 6,
    max_turns: int = 8,
) -> dict:
    """运行单集单场景的最小主循环。"""
    runtime_state: RuntimeState = create_runtime_state(global_config, planner_output, episode)
    episode_plan = get_episode_plan(planner_output, episode)
    current_speaker = episode_plan["first_speaker"]
    valid_roles = list(global_config["character_roster"].keys())
    turn_trace: list[dict] = []
    log_path = initialize_episode_log(runtime_state, episode_plan)

    for _ in range(max_turns):
        prompt = build_role_context(
            current_speaker,
            runtime_state,
            episode_plan,
            history_window=history_window,
        )
        turn_output = role_agent_box.generate_role_response(current_speaker, prompt)
        if isinstance(turn_output, str):
            finalize_episode_log(
                log_path,
                result_status=turn_output,
                last_speaker=current_speaker,
                total_turns=runtime_state.story.current_turn,
            )
            return {
                "status": turn_output,
                "runtime_state": runtime_state,
                "last_speaker": current_speaker,
                "turn_trace": turn_trace,
            }

        commit_turn_result(runtime_state, current_speaker, turn_output)
        proposed_next_speaker = turn_output.get("next_speaker")
        turn_record = {
            "step": runtime_state.story.current_turn,
            "speaker": current_speaker,
            "proposed_next_speaker": proposed_next_speaker,
        }

        if is_end_signal(proposed_next_speaker):
            if should_end_episode(runtime_state):
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
                finalize_episode_log(
                    log_path,
                    result_status="ended",
                    last_speaker=current_speaker,
                    total_turns=runtime_state.story.current_turn,
                )
                return {
                    "status": "ended",
                    "runtime_state": runtime_state,
                    "last_speaker": current_speaker,
                    "turn_trace": turn_trace,
                }
            proposed_next_speaker = None

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
            finalize_episode_log(
                log_path,
                result_status="handoff",
                last_speaker=current_speaker,
                total_turns=runtime_state.story.current_turn,
            )
            return {
                "status": "handoff",
                "runtime_state": runtime_state,
                "last_speaker": current_speaker,
                "turn_trace": turn_trace,
            }

        current_speaker = next_speaker

    finalize_episode_log(
        log_path,
        result_status="max_turns_reached",
        last_speaker=current_speaker,
        total_turns=runtime_state.story.current_turn,
    )
    return {
        "status": "max_turns_reached",
        "runtime_state": runtime_state,
        "last_speaker": current_speaker,
        "turn_trace": turn_trace,
    }


def run_demo_episode(episode: int = 1) -> dict:
    """用真实模型调用跑通单集 demo。"""
    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    planner_output = planner_agent.generate_outline(planner_agent_prompt)
    if isinstance(planner_output, str):
        return {"status": planner_output}

    role_agent_box = Role_Agent_Box(base_url, api_key, model)
    return run_episode(planner_output, role_agent_box, episode)


if __name__ == "__main__":
    print(run_demo_episode())

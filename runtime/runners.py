from __future__ import annotations

from typing import Any

from Agent_model import Planner_Agent, Role_Agent_Box, Summary_Agent, load_env
from input_adapter import build_free_mode_planner_output
from log_writer import (
    initialize_season_log_directory,
    serialize_role_memories,
    serialize_season_context,
    write_episode_checkpoint,
    write_season_context,
    write_season_summary,
)
from prompt import build_planner_agent_prompt
from story_state import RoleMemory, RunMode, create_season_context, update_season_context

SEASON_CONTINUE_STATUSES = {"ended", "handoff", "max_turns_reached", "director_cut"}


def is_episode_success_status(status: str) -> bool:
    return status in SEASON_CONTINUE_STATUSES


def build_episode_checkpoint_payload(
    run_id: str,
    episode: int,
    total_episode_count: int,
    final_role_memories: dict[str, RoleMemory],
    season_context_payload: dict,
) -> dict:
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


def run_episode(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    episode: int,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    previous_role_memories: dict[str, RoleMemory] | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> dict:
    from runtime.session_engine import create_episode_session

    session = create_episode_session(
        planner_output,
        role_agent_box,
        episode,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
        previous_role_memories=previous_role_memories,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
        run_mode=run_mode,
    )
    return session.run_until_stop()


def run_free_episode(
    role_agent_box: Role_Agent_Box,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    opening_scene: str | None = None,
    scene_roles: list[str] | None = None,
    story_hook: str | None = None,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
) -> dict:
    planner_output = build_free_mode_planner_output(
        runtime_config,
        opening_scene=opening_scene,
        scene_roles=scene_roles,
        story_hook=story_hook,
    )
    return run_episode(
        planner_output,
        role_agent_box,
        1,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
        tail_window=tail_window,
        fallback_history_window=fallback_history_window,
        max_turns=max_turns,
        log_dir=log_dir,
        monitor_agent=monitor_agent,
        run_mode="free",
    )


def run_season(
    planner_output: dict,
    role_agent_box: Role_Agent_Box,
    runtime_config: dict[str, Any],
    summary_agent: Summary_Agent | None = None,
    start_episode: int = 1,
    continuity_enabled: bool = True,
    tail_window: int = 4,
    fallback_history_window: int = 6,
    max_turns: int = 8,
    log_dir: str = "log",
    monitor_agent: Any = None,
    run_mode: RunMode = "planned",
) -> dict:
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
            runtime_config=runtime_config,
            summary_agent=summary_agent,
            previous_role_memories=previous_role_memories if continuity_enabled else None,
            tail_window=tail_window,
            fallback_history_window=fallback_history_window,
            max_turns=max_turns,
            log_dir=str(season_log_dir),
            monitor_agent=monitor_agent,
            run_mode=run_mode,
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


def run_demo_episode(runtime_config: dict[str, Any], episode: int = 1) -> dict:
    base_url, api_key, model = load_env()
    planner_agent = Planner_Agent(base_url, api_key, model)
    planner_prompt = build_planner_agent_prompt(runtime_config)
    planner_output = planner_agent.generate_outline(planner_prompt)
    if isinstance(planner_output, str):
        return {"status": planner_output}

    role_agent_box = Role_Agent_Box(base_url, api_key, model)
    summary_agent = Summary_Agent(base_url, api_key, model)
    return run_episode(
        planner_output,
        role_agent_box,
        episode,
        runtime_config=runtime_config,
        summary_agent=summary_agent,
    )


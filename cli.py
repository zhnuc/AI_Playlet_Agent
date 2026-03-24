"""最小 CLI demo。"""
from __future__ import annotations

import argparse
import json

from monitor_agent import RuleBasedMonitor
from playlet_service import PlayletService, build_default_agents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Playlet Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    planned = subparsers.add_parser("planned-demo", help="生成大纲并运行单集 demo")
    planned.add_argument("--feedback", default="", help="可选的大纲修订意见")
    planned.add_argument("--episode", type=int, default=1)
    planned.add_argument("--max-turns", type=int, default=8)

    free = subparsers.add_parser("free-demo", help="直接用 free mode 跑单集 demo")
    free.add_argument("--scene", default="总裁办公室")
    free.add_argument("--hook", default="")
    free.add_argument("--max-turns", type=int, default=8)
    return parser


def run() -> None:
    parser = build_parser()
    args = parser.parse_args()
    planner_agent, role_agent_box, summary_agent = build_default_agents()
    service = PlayletService()

    if args.command == "planned-demo":
        session = service.create_planned_session()
        planner_output = service.generate_outline(session.session_id, planner_agent)
        if isinstance(planner_output, str):
            print(planner_output)
            return
        if args.feedback:
            planner_output = service.revise_outline(session.session_id, args.feedback, planner_agent)
            if isinstance(planner_output, str):
                print(planner_output)
                return
        service.approve_outline(session.session_id)
        result = service.run_episode(
            session.session_id,
            role_agent_box,
            summary_agent=summary_agent,
            episode=args.episode,
            monitor_agent=RuleBasedMonitor(),
            max_turns=args.max_turns,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "free-demo":
        session = service.create_free_session(opening_scene=args.scene, story_hook=args.hook or None)
        result = service.run_episode(
            session.session_id,
            role_agent_box,
            summary_agent=summary_agent,
            monitor_agent=RuleBasedMonitor(),
            max_turns=args.max_turns,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    run()

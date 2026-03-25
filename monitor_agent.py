"""Monitor layer for runtime supervision."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from Agent_model import parse_json_response
from story_state import RuntimeState


@dataclass
class MonitorDecision:
    """Result returned by monitor review."""

    decision: str = "continue"
    suggestion: str = ""
    reason: str = ""


class RuleBasedMonitor:
    """Minimal rule monitor that does not rely on extra model calls."""

    def review(self, runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> MonitorDecision:
        return MonitorDecision(decision="continue", reason="Rule monitor disabled")


class Monitor_Agent:
    """Optional LLM monitor."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def build_prompt(self, runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> str:
        recent_events = [
            {
                "step": event.step,
                "kind": event.kind,
                "speaker": event.speaker,
                "content": event.content,
            }
            for event in runtime_state.story.event_log[-12:]
        ]
        return f"""
# Role:
You are the monitor agent in a short-drama runtime. Judge whether the scene should continue, cut, or receive a pacing suggestion.

# Scene Goal:
- Main plot: {episode_plan["global_plot"]}
- Core conflict: {episode_plan["core_conflict"]}
- Hook target: {episode_plan["plot_twist_or_hook"]}

# Recent Events:
{json.dumps(recent_events, ensure_ascii=False, indent=2)}

# Output:
Return strict JSON only:
{{
  "decision": "continue | cut | suggestion",
  "suggestion": "If decision is suggestion, provide one short actionable instruction",
  "reason": "Reason"
}}
"""

    def review(self, runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> MonitorDecision:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": self.build_prompt(runtime_state, episode_plan)}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        payload = parse_json_response(response.choices[0].message.content)
        decision = str(payload.get("decision", "continue") or "continue").strip().lower()
        suggestion = str(payload.get("suggestion", "") or "")
        reason = str(payload.get("reason", "") or "")
        if decision not in {"continue", "cut", "suggestion"}:
            decision = "continue"
        return MonitorDecision(decision=decision, suggestion=suggestion, reason=reason)

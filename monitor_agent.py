"""监制 / 监控层。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from Agent_model import parse_json_response
from story_state import RuntimeState


@dataclass
class MonitorDecision:
    """监制决策结果。"""

    decision: str = "continue"
    suggestion: str = ""
    reason: str = ""


class RuleBasedMonitor:
    """最小规则版监制，不依赖模型即可运行。"""

    def review(self, runtime_state: RuntimeState, episode_plan: dict[str, Any]) -> MonitorDecision:
        current_turn = runtime_state.story.current_turn
        if current_turn >= 12:
            return MonitorDecision(decision="cut", reason="达到默认最大监制轮次")

        dialogue_events = [event for event in runtime_state.story.event_log if event.kind == "dialogue"]
        if len(dialogue_events) >= 4:
            last_two_dialogues = [event.content for event in dialogue_events[-2:]]
            if len(set(last_two_dialogues)) == 1:
                return MonitorDecision(
                    decision="suggestion",
                    suggestion="避免重复原话，立刻推进新的事实、证据或反击动作。",
                    reason="检测到对白重复",
                )

        return MonitorDecision(decision="continue", reason="当前节奏正常")


class Monitor_Agent:
    """可选 LLM 监制。"""

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
你是短剧推演过程中的监制 Agent，负责判断当前场景是否应该继续、切断，或向演员发出节奏建议。

# Scene Goal:
- 本集主线：{episode_plan["global_plot"]}
- 核心冲突：{episode_plan["core_conflict"]}
- 悬念目标：{episode_plan["plot_twist_or_hook"]}

# Recent Events:
{json.dumps(recent_events, ensure_ascii=False, indent=2)}

# Output:
你必须输出严格 JSON：
{{
  "decision": "continue | cut | suggestion",
  "suggestion": "若 decision 为 suggestion，则给出一条简短、可执行的指导",
  "reason": "说明原因"
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

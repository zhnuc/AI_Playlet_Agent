"""面向 CLI / API 的后端服务层。"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any
from uuid import uuid4

from Agent_model import Planner_Agent, Role_Agent_Box, Summary_Agent, load_env
from formatter_agent import export_artifacts
from input_adapter import build_free_mode_planner_output, build_runtime_config
from main_loop import EpisodeSession, create_episode_session, run_season
from monitor_agent import RuleBasedMonitor
from planner_review import PlannerReviewState, approve_planner_outline, generate_planner_outline, revise_planner_outline


@dataclass
class SessionRecord:
    """保存一次创作会话的核心状态。"""

    session_id: str
    run_mode: str
    runtime_config: dict[str, Any]
    planner_review_state: PlannerReviewState = field(default_factory=PlannerReviewState)
    episode_session: EpisodeSession | None = None
    season_result: dict[str, Any] | None = None
    storyboard_result: dict[str, Any] | None = None

    @property
    def planner_output(self) -> dict[str, Any] | None:
        return self.planner_review_state.planner_output


def build_default_agents() -> tuple[Planner_Agent, Role_Agent_Box, Summary_Agent]:
    """按当前环境变量创建默认模型调用器。"""
    base_url, api_key, model = load_env()
    return (
        Planner_Agent(base_url, api_key, model),
        Role_Agent_Box(base_url, api_key, model),
        Summary_Agent(base_url, api_key, model),
    )


class PlayletService:
    """统一管理创作 session。"""

    ALLOWED_SHOT_TYPES = {"WS", "MS", "CU", "OTS", "ECU"}
    ALLOWED_CAMERA_MOVES = {"static", "push", "pull", "pan", "tilt", "handheld"}

    SHOT_TYPE_ALIASES = {
        "wide": "WS",
        "long": "WS",
        "全景": "WS",
        "远景": "WS",
        "middle": "MS",
        "medium": "MS",
        "中景": "MS",
        "close": "CU",
        "closeup": "CU",
        "特写": "CU",
        "过肩": "OTS",
        "over the shoulder": "OTS",
        "ots": "OTS",
        "extreme close": "ECU",
        "极特写": "ECU",
    }

    CAMERA_MOVE_ALIASES = {
        "固定": "static",
        "静止": "static",
        "static": "static",
        "推进": "push",
        "push": "push",
        "拉远": "pull",
        "pull": "pull",
        "平移": "pan",
        "摇镜": "pan",
        "pan": "pan",
        "俯仰": "tilt",
        "tilt": "tilt",
        "手持": "handheld",
        "handheld": "handheld",
    }

    def __init__(self):
        self.sessions: dict[str, SessionRecord] = {}

    def _new_session_id(self) -> str:
        return uuid4().hex[:12]

    @staticmethod
    def _status_label_from_snapshot(runtime: EpisodeSession | None) -> str:
        if runtime is None:
            return "待机中"
        if runtime.result is not None:
            return f"本集结束：{runtime.result.get('status', runtime.status)}"
        if runtime.status == "paused":
            return "当前已暂停"
        return "推演进行中"

    @staticmethod
    def _build_chat_messages(runtime: EpisodeSession) -> list[dict[str, Any]]:
        triple_kinds = {"thought", "action", "dialogue"}
        events = [
            event
            for event in runtime.runtime_state.story.event_log
            if event.episode == runtime.runtime_state.story.current_episode and event.kind in triple_kinds
        ]
        messages: list[dict[str, Any]] = []
        i = 0
        while i < len(events):
            current = events[i]
            segments: list[dict[str, Any]] = []
            j = i
            while j < len(events):
                evt = events[j]
                if evt.step != current.step or evt.speaker != current.speaker:
                    break
                if evt.kind not in triple_kinds:
                    break
                segments.append(
                    {
                        "event_id": evt.event_id,
                        "kind": evt.kind,
                        "content": evt.content,
                    }
                )
                j += 1

            if segments:
                messages.append(
                    {
                        "message_group_id": f"msg_{current.step}_{current.speaker}",
                        "episode": current.episode,
                        "scene": current.scene,
                        "turn": current.step,
                        "speaker_id": current.speaker,
                        "speaker_name": current.speaker,
                        "segments": segments,
                    }
                )
            i = j if j > i else i + 1
        return messages

    @staticmethod
    def _build_control_events(runtime: EpisodeSession) -> list[dict[str, Any]]:
        title_map = {
            "director": "导演指令",
            "monitor": "监制提示",
            "system": "系统事件",
        }
        events = [
            event
            for event in runtime.runtime_state.story.event_log
            if event.episode == runtime.runtime_state.story.current_episode and event.kind in {"director", "monitor", "system"}
        ]
        control_events: list[dict[str, Any]] = []
        for event in events:
            control_events.append(
                {
                    "event_id": event.event_id,
                    "episode": event.episode,
                    "turn": event.step,
                    "source_type": event.kind,
                    "title": title_map.get(event.kind, "系统事件"),
                    "content": event.content,
                    "target_role_id": None,
                    "target_role_name": None,
                }
            )
        return control_events

    @staticmethod
    def _build_role_profiles(runtime: EpisodeSession) -> dict[str, dict[str, Any]]:
        roster = runtime.runtime_state.story.character_roster
        role_profiles: dict[str, dict[str, Any]] = {}
        for role_name, profile in roster.items():
            role_memory = runtime.runtime_state.role_memories.get(role_name)
            role_profiles[role_name] = {
                "character_id": role_name,
                "static_profile": {
                    "name": role_name,
                    "age": profile.get("age"),
                    "gender": profile.get("gender", "未设定"),
                    "identity": profile.get("identity", ""),
                    "role_position": profile.get("role_position", "supporting"),
                    "role_type": profile.get("role_type", "配角"),
                    "appearance_tags": profile.get("appearance_tags", []),
                    "personality_tags": profile.get("personality_tags", []),
                },
                "dynamic_profile": {
                    "current_goal": role_memory.current_goal if role_memory else "",
                    "beliefs_about_others": role_memory.beliefs_about_others if role_memory else {},
                    "unresolved_hook": role_memory.unresolved_hook if role_memory else "",
                    "episode_digest_public": role_memory.episode_digest_public if role_memory else "",
                    "episode_digest_private": role_memory.episode_digest_private if role_memory else "",
                },
            }
        return role_profiles

    @staticmethod
    def _build_current_episode_records_by_role(runtime: EpisodeSession) -> dict[str, list[dict[str, Any]]]:
        triple_kinds = {"thought", "action", "dialogue"}
        current_episode = runtime.runtime_state.story.current_episode
        records_by_role: dict[str, list[dict[str, Any]]] = {
            role_name: [] for role_name in runtime.runtime_state.story.character_roster.keys()
        }
        for event in runtime.runtime_state.story.event_log:
            if event.episode != current_episode:
                continue
            if event.kind not in triple_kinds:
                continue
            if event.speaker not in records_by_role:
                records_by_role[event.speaker] = []
            records_by_role[event.speaker].append(
                {
                    "event_id": event.event_id,
                    "episode": event.episode,
                    "scene": event.scene,
                    "turn": event.step,
                    "kind": event.kind,
                    "content": event.content,
                }
            )

        for role_name in records_by_role:
            records_by_role[role_name].sort(key=lambda item: (item["turn"], item["event_id"]), reverse=True)
        return records_by_role

    def create_planned_session(
        self,
        config_override: dict[str, Any] | None = None,
        planner_output: dict[str, Any] | None = None,
    ) -> SessionRecord:
        runtime_config = build_runtime_config(config_override)
        session = SessionRecord(
            session_id=self._new_session_id(),
            run_mode="planned",
            runtime_config=runtime_config,
        )
        if planner_output is not None:
            session.planner_review_state.planner_output = planner_output
        self.sessions[session.session_id] = session
        return session

    def create_free_session(
        self,
        config_override: dict[str, Any] | None = None,
        opening_scene: str | None = None,
        scene_roles: list[str] | None = None,
        story_hook: str | None = None,
    ) -> SessionRecord:
        runtime_config = build_runtime_config(config_override)
        planner_output = build_free_mode_planner_output(
            runtime_config,
            opening_scene=opening_scene,
            scene_roles=scene_roles,
            story_hook=story_hook,
        )
        session = SessionRecord(
            session_id=self._new_session_id(),
            run_mode="free",
            runtime_config=runtime_config,
        )
        session.planner_review_state.planner_output = planner_output
        session.planner_review_state.approved = True
        self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionRecord:
        if session_id not in self.sessions:
            raise ValueError(f"session_id={session_id} 不存在")
        return self.sessions[session_id]

    def generate_outline(self, session_id: str, planner_agent: Planner_Agent) -> dict[str, Any] | str:
        session = self.get_session(session_id)
        planner_output = generate_planner_outline(planner_agent, session.runtime_config)
        if isinstance(planner_output, dict):
            episodes = planner_output.get("episodes")
            episode_count = len(episodes) if isinstance(episodes, list) else 0
            print(
                f"[DEBUG][OUTLINE][session={session_id}] type=dict "
                f"has_episodes={isinstance(episodes, list)} episode_count={episode_count}"
            )
        else:
            print(f"[DEBUG][OUTLINE][session={session_id}] type=str value={planner_output}")
        if isinstance(planner_output, dict):
            session.planner_review_state.planner_output = planner_output
            session.planner_review_state.approved = False
        return planner_output

    def revise_outline(self, session_id: str, feedback: str, planner_agent: Planner_Agent) -> dict[str, Any] | str:
        session = self.get_session(session_id)
        return revise_planner_outline(session.planner_review_state, planner_agent, session.runtime_config, feedback)

    def approve_outline(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        return approve_planner_outline(session.planner_review_state)

    def create_episode_runtime(
        self,
        session_id: str,
        role_agent_box: Role_Agent_Box,
        summary_agent: Summary_Agent | None = None,
        episode: int = 1,
        monitor_agent: Any = None,
        log_dir: str = "log",
        max_turns: int = 8,
    ) -> EpisodeSession:
        session = self.get_session(session_id)
        if session.planner_output is None:
            raise ValueError("当前还没有可运行的大纲")
        if session.run_mode == "planned" and not session.planner_review_state.approved:
            raise ValueError("planned 模式需要先审批通过大纲，再进入推演")
        effective_monitor = monitor_agent or RuleBasedMonitor()
        episode_session = create_episode_session(
            session.planner_output,
            role_agent_box,
            episode,
            runtime_config=session.runtime_config,
            summary_agent=summary_agent,
            log_dir=log_dir,
            max_turns=max_turns,
            monitor_agent=effective_monitor,
            run_mode=session.run_mode,
        )
        episode_session.planner_review_state = session.planner_review_state
        episode_session.approved_outline = session.planner_review_state.approved
        session.episode_session = episode_session
        return episode_session

    def get_episode_snapshot(self, session_id: str) -> dict[str, Any]:
        """杩斿洖褰撳墠 episode runtime 鐨勫揩鐓э紝渚涘墠绔姸鎬佸悓姝ャ€?"""
        session = self.get_session(session_id)
        snapshot: dict[str, Any] = {
            "session_id": session.session_id,
            "run_mode": session.run_mode,
            "status_label": self._status_label_from_snapshot(session.episode_session),
            "outline_approved": session.planner_review_state.approved,
            "planner_output": session.planner_output,
            "role_names": list(session.runtime_config["character_roster"].keys()),
            "character_roster": session.runtime_config.get("character_roster", {}),
        }
        if session.episode_session is None:
            return snapshot

        runtime = session.episode_session
        snapshot.update(
            {
                "episode_status": runtime.status,
                "status_label": self._status_label_from_snapshot(runtime),
                "current_episode": runtime.runtime_state.story.current_episode,
                "current_scene": runtime.runtime_state.story.current_scene,
                "episode_plan": runtime.episode_plan,
                "current_turn": runtime.runtime_state.story.current_turn,
                "current_speaker": runtime.current_speaker,
                "soft_turn_limit": runtime.soft_turn_limit,
                "hard_turn_limit": runtime.hard_turn_limit,
                "beat_state": runtime.runtime_state.beat_state,
                "turn_trace": runtime.turn_trace,
                "event_log": runtime.runtime_state.story.event_log,
                "chat_messages": self._build_chat_messages(runtime),
                "control_events": self._build_control_events(runtime),
                "role_profiles": self._build_role_profiles(runtime),
                "current_episode_records_by_role": self._build_current_episode_records_by_role(runtime),
                "interaction": runtime.runtime_state.interaction,
                "result": runtime.result,
            }
        )
        return snapshot

    def start_episode(
        self,
        session_id: str,
        role_agent_box: Role_Agent_Box,
        summary_agent: Summary_Agent | None = None,
        episode: int = 1,
        monitor_agent: Any = None,
        log_dir: str = "log",
        max_turns: int = 8,
    ) -> dict[str, Any]:
        """鍒涘缓鍗曢泦 runtime 浣嗕笉鐩存帴璺戝畬锛岀敤浜?UI 閫愭鎺ㄨ繘銆?"""
        self.create_episode_runtime(
            session_id,
            role_agent_box,
            summary_agent=summary_agent,
            episode=episode,
            monitor_agent=monitor_agent,
            log_dir=log_dir,
            max_turns=max_turns,
        )
        return self.get_episode_snapshot(session_id)

    def step_episode(self, session_id: str) -> dict[str, Any]:
        """鎺ㄨ繘褰撳墠 session 鐨勪竴涓?turn锛屽苟杩斿洖鏈€鏂板揩鐓с€?"""
        session = self.get_session(session_id)
        if session.episode_session is None:
            raise ValueError("褰撳墠 session 杩樻病鏈夋椿璺冪殑 episode runtime")

        step_result = session.episode_session.run_next_turn()
        return {
            "step_result": step_result,
            "snapshot": self.get_episode_snapshot(session_id),
        }

    def run_episode(
        self,
        session_id: str,
        role_agent_box: Role_Agent_Box,
        summary_agent: Summary_Agent | None = None,
        episode: int = 1,
        monitor_agent: Any = None,
        log_dir: str = "log",
        max_turns: int = 8,
    ) -> dict[str, Any]:
        episode_session = self.create_episode_runtime(
            session_id,
            role_agent_box,
            summary_agent=summary_agent,
            episode=episode,
            monitor_agent=monitor_agent,
            log_dir=log_dir,
            max_turns=max_turns,
        )
        return episode_session.run_until_stop()

    def run_season(
        self,
        session_id: str,
        role_agent_box: Role_Agent_Box,
        summary_agent: Summary_Agent | None = None,
        monitor_agent: Any = None,
        log_dir: str = "log",
        max_turns: int = 8,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session.planner_output is None:
            raise ValueError("当前还没有可运行的大纲")
        if session.run_mode == "planned" and not session.planner_review_state.approved:
            raise ValueError("planned 模式需要先审批通过大纲，再进入整季运行")
        session.season_result = run_season(
            session.planner_output,
            role_agent_box,
            runtime_config=session.runtime_config,
            summary_agent=summary_agent,
            monitor_agent=monitor_agent or RuleBasedMonitor(),
            log_dir=log_dir,
            max_turns=max_turns,
            run_mode=session.run_mode,
        )
        return session.season_result

    def apply_director_command(self, session_id: str, **command_kwargs: Any) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session.episode_session is None:
            raise ValueError("当前 session 还没有活跃的 episode runtime")
        return session.episode_session.apply_director_command(**command_kwargs)

    def export_session(self, session_id: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session.episode_session is not None:
            exports = export_artifacts(
                session.episode_session.runtime_state,
                session.episode_session.episode_plan,
                season_summary=session.season_result["season_summary"] if session.season_result else None,
            )
            if session.storyboard_result is None:
                session.storyboard_result = self._build_storyboard_fallback(session.episode_session)
            exports["storyboard"] = session.storyboard_result
            return exports
        if session.season_result is not None:
            return {
                "script": "",
                "shotlist": {},
                "storyboard": session.storyboard_result or {},
                "season_summary": session.season_result["season_summary"],
            }
        raise ValueError("当前 session 还没有可导出的运行结果")

    @classmethod
    def _normalize_shot_type(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return "MS"
        upper = text.upper()
        if upper in cls.ALLOWED_SHOT_TYPES:
            return upper
        lowered = text.lower()
        for alias, mapped in cls.SHOT_TYPE_ALIASES.items():
            if alias in lowered or alias in text:
                return mapped
        return "MS"

    @classmethod
    def _normalize_camera_move(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return "static"
        lowered = text.lower()
        if lowered in cls.ALLOWED_CAMERA_MOVES:
            return lowered
        for alias, mapped in cls.CAMERA_MOVE_ALIASES.items():
            if alias in lowered or alias in text:
                return mapped
        return "static"

    @classmethod
    def _build_storyboard_fallback(cls, runtime: EpisodeSession) -> dict[str, Any]:
        events = [
            event
            for event in runtime.runtime_state.story.event_log
            if event.episode == runtime.runtime_state.story.current_episode and event.kind in {"action", "dialogue"}
        ]

        shots: list[dict[str, Any]] = []
        for index, event in enumerate(events, start=1):
            default_shot_type = cls._normalize_shot_type("CU" if event.kind == "dialogue" else "MS")
            shots.append(
                {
                    "shot_id": f"S{index:02d}",
                    "turn": event.step,
                    "speaker": event.speaker,
                    "shot_type": default_shot_type,
                    "camera_move": cls._normalize_camera_move("static"),
                    "duration_sec": 3,
                    "visual": f"{event.speaker}{event.content}",
                    "dialogue_focus": event.content if event.kind == "dialogue" else "",
                    "sound": "环境音",
                    "prompt_draft": (
                        f"{runtime.runtime_state.story.current_scene}，{event.speaker}，{default_shot_type}，"
                        f"{event.content}，电影感，真实光影"
                    ),
                }
            )

        return {
            "episode": runtime.runtime_state.story.current_episode,
            "scene": runtime.runtime_state.story.current_scene,
            "source": "fallback",
            "shots": shots,
        }

    @classmethod
    def _normalize_storyboard_output(cls, raw_payload: dict[str, Any], runtime: EpisodeSession) -> dict[str, Any]:
        if not isinstance(raw_payload, dict):
            raise ValueError("storyboard payload is not an object")

        raw_shots = raw_payload.get("shots")
        if not isinstance(raw_shots, list):
            raise ValueError("storyboard payload missing shots list")

        normalized_shots: list[dict[str, Any]] = []
        for index, item in enumerate(raw_shots, start=1):
            if not isinstance(item, dict):
                continue
            normalized_shots.append(
                {
                    "shot_id": str(item.get("shot_id", f"S{index:02d}")),
                    "turn": int(item.get("turn") or index),
                    "speaker": str(item.get("speaker", "")),
                    "shot_type": cls._normalize_shot_type(item.get("shot_type", "MS")),
                    "camera_move": cls._normalize_camera_move(item.get("camera_move", "static")),
                    "duration_sec": max(1, int(item.get("duration_sec") or 3)),
                    "visual": str(item.get("visual", "")).strip(),
                    "dialogue_focus": str(item.get("dialogue_focus", "")).strip(),
                    "sound": str(item.get("sound", "环境音")).strip(),
                    "prompt_draft": str(item.get("prompt_draft", "")).strip(),
                }
            )

        if not normalized_shots:
            raise ValueError("storyboard payload has no valid shots")

        return {
            "episode": int(raw_payload.get("episode") or runtime.runtime_state.story.current_episode),
            "scene": str(raw_payload.get("scene") or runtime.runtime_state.story.current_scene),
            "source": "ai",
            "shots": normalized_shots,
        }

    def generate_storyboard(
        self,
        session_id: str,
        planner_agent: Planner_Agent | None = None,
        force_fallback: bool = False,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        if session.episode_session is None:
            raise ValueError("当前 session 还没有可用于分镜生成的运行结果")

        runtime = session.episode_session
        actionable_events = [
            event
            for event in runtime.runtime_state.story.event_log
            if event.episode == runtime.runtime_state.story.current_episode and event.kind in {"action", "dialogue"}
        ]
        if not actionable_events:
            raise ValueError("当前集还没有对白/动作事件，请先推进至少 1 轮后再生成分镜")

        fallback_payload = self._build_storyboard_fallback(runtime)
        if force_fallback or planner_agent is None:
            session.storyboard_result = fallback_payload
            return fallback_payload

        events = [
            {
                "turn": event.step,
                "speaker": event.speaker,
                "kind": event.kind,
                "content": event.content,
            }
            for event in runtime.runtime_state.story.event_log
            if event.episode == runtime.runtime_state.story.current_episode and event.kind in {"action", "dialogue", "thought"}
        ]

        prompt = f"""
你是短剧分镜导演。请基于给定剧情事件生成可拍摄分镜 JSON。
仅输出 JSON，不要解释。每个镜头都要给出 shot_id、turn、speaker、shot_type、camera_move、duration_sec、visual、dialogue_focus、sound、prompt_draft。
shot_type 只能使用：WS/MS/CU/OTS/ECU。
camera_move 建议：static/push/pull/pan/tilt/handheld。

输入：
{json.dumps({
    "episode": runtime.runtime_state.story.current_episode,
    "scene": runtime.runtime_state.story.current_scene,
    "episode_goal": runtime.episode_plan.get("global_plot", ""),
    "hook": runtime.episode_plan.get("plot_twist_or_hook", ""),
    "events": events,
}, ensure_ascii=False)}

输出格式：
{{
  "episode": 1,
  "scene": "场景",
  "shots": [
    {{
      "shot_id": "S01",
      "turn": 1,
      "speaker": "角色名",
      "shot_type": "CU",
      "camera_move": "push",
      "duration_sec": 3,
      "visual": "画面描述",
      "dialogue_focus": "对白焦点",
      "sound": "音效/环境",
      "prompt_draft": "可直接用于文生图/视频的中文提示词"
    }}
  ]
}}
"""

        try:
            response = planner_agent.client.chat.completions.create(
                model=planner_agent.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = response.choices[0].message.content
            raw_payload = parse_json_response(raw_text)
            normalized = self._normalize_storyboard_output(raw_payload, runtime)
            session.storyboard_result = normalized
            return normalized
        except Exception:
            fallback_payload["ai_failed"] = True
            session.storyboard_result = fallback_payload
            return fallback_payload

    def replay_events(self, session_id: str) -> list[dict[str, Any]]:
        session = self.get_session(session_id)
        if session.episode_session is None:
            return []
        return list(session.episode_session.turn_trace)

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from Agent_model import parse_json_response
from monitor_agent import RuleBasedMonitor
from playlet_service import PlayletService, build_default_agents

service = PlayletService()
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
env_file = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file_kv() -> dict[str, str]:
    if not env_file.exists():
        return {}
    data: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _get_config_status() -> dict[str, Any]:
    env_exists = env_file.exists()
    file_kv = _read_env_file_kv()
    base_url = (file_kv.get("base_url") or os.getenv("base_url") or "").strip()
    api_key = (file_kv.get("api_key") or os.getenv("api_key") or "").strip()
    model = (file_kv.get("model") or os.getenv("model") or "").strip()
    missing_fields: list[str] = []
    if not base_url:
        missing_fields.append("base_url")
    if not api_key:
        missing_fields.append("api_key")
    if not model:
        missing_fields.append("model")
    return {
        "env_exists": env_exists,
        "base_url_set": bool(base_url),
        "api_key_set": bool(api_key),
        "model_set": bool(model),
        "missing_fields": missing_fields,
        "needs_setup": (not env_exists) or bool(missing_fields),
    }


def _write_env_config(base_url: str, api_key: str, model: str) -> None:
    env_file.write_text(
        f"base_url={base_url}\napi_key={api_key}\nmodel={model}\n",
        encoding="utf-8",
    )
    os.environ["base_url"] = base_url
    os.environ["api_key"] = api_key
    os.environ["model"] = model


def create_app() -> FastAPI:
    app = FastAPI(title="AI Playlet Agent API", version="0.1.0")

    @app.middleware("http")
    async def perf_middleware(request: Request, call_next):
        started_at = perf_counter()
        response = await call_next(request)
        elapsed_ms = round((perf_counter() - started_at) * 1000, 1)
        print(
            f"[PERF][API] {request.method} {request.url.path} "
            f"status={response.status_code} ms={elapsed_ms}"
        )
        return response

    if frontend_dir.exists():
        app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="ui")

    @app.get("/")
    def root():
        if frontend_dir.exists():
            return RedirectResponse(url="/ui/")
        return {"message": "AI Playlet Agent API is running."}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/config/status")
    def config_status():
        return _get_config_status()

    @app.post("/config/save")
    def save_config(payload: dict[str, Any]):
        base_url = str(payload.get("base_url", "")).strip()
        api_key = str(payload.get("api_key", "")).strip()
        model = str(payload.get("model", "")).strip()
        if not base_url or not api_key or not model:
            raise HTTPException(status_code=400, detail="base_url, api_key, model are required")
        _write_env_config(base_url, api_key, model)
        return {"ok": True, "config": _get_config_status()}

    def _build_agents():
        try:
            planner_agent, role_agent_box, summary_agent = build_default_agents()
            return planner_agent, role_agent_box, summary_agent
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Model init failed: {exc}") from exc

    def _generate_one_line_json(prompt: str) -> dict[str, Any]:
        planner_agent, _, _ = _build_agents()
        started_at = perf_counter()
        response = planner_agent.client.chat.completions.create(
            model=planner_agent.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        elapsed_ms = round((perf_counter() - started_at) * 1000, 1)
        raw_text = response.choices[0].message.content
        print(
            f"[PERF][MODEL][one_line] ms={elapsed_ms} prompt_chars={len(prompt)} "
            f"response_chars={len(raw_text or '')}"
        )
        return parse_json_response(raw_text)

    @app.post("/sessions/planned")
    def create_planned_session(payload: dict[str, Any] | None = None):
        payload = payload or {}
        session = service.create_planned_session(
            config_override=payload.get("config_override"),
            planner_output=payload.get("planner_output"),
        )
        return {"session_id": session.session_id, "run_mode": session.run_mode}

    @app.post("/sessions/free")
    def create_free_session(payload: dict[str, Any] | None = None):
        payload = payload or {}
        session = service.create_free_session(
            config_override=payload.get("config_override"),
            opening_scene=payload.get("opening_scene"),
            scene_roles=payload.get("scene_roles"),
            story_hook=payload.get("story_hook"),
        )
        return {
            "session_id": session.session_id,
            "run_mode": session.run_mode,
            "planner_output": session.planner_output,
        }

    @app.post("/assist/one-line/background")
    def one_line_background(payload: dict[str, Any]):
        text = str(payload.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        prompt = f"""
你是短剧策划助手。根据用户一句话背景，提炼结构化字段并返回JSON。
仅输出JSON，不要解释。

用户输入：
{text}

输出字段：
{{
  "genre": "从以下枚举中选一个: 重生复仇/豪门虐恋/逆袭爽文/先婚后爱/职场博弈/悬疑反转",
  "scene": "开场场景，20字内",
  "logline": "故事核，一句话，60字内",
  "expected_episodes": "整数，1-20"
}}
"""
        try:
            result = _generate_one_line_json(prompt)
            return {"result": result}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/assist/one-line/role")
    def one_line_role(payload: dict[str, Any]):
        text = str(payload.get("text", "")).strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        prompt = f"""
你是短剧角色设计助手。根据用户一句话角色描述，生成角色卡字段并返回JSON。
仅输出JSON，不要解释。
如果用户描述里包含多个角色（例如使用“、/，/,和”等分隔），请输出多个角色。
最多输出 5 个角色。

用户输入：
{text}

输出字段：
{{
  "roles": [
    {{
      "name": "角色名",
      "role_position": "male_lead_1/female_lead_1/chief_villain/male_lead_2/female_lead_2/minor_villain/supporting",
      "gender": "男/女/未设定",
      "age": 20,
      "identity": "身份描述",
      "appearance_tags": ["标签1","标签2"],
      "personality_tags": ["标签1","标签2","标签3"],
      "catchphrase": "口头禅"
    }}
  ]
}}
"""
        try:
            result = _generate_one_line_json(prompt)
            roles_raw: list[dict[str, Any]] = []
            if isinstance(result, dict):
                if isinstance(result.get("roles"), list):
                    roles_raw = [item for item in result["roles"] if isinstance(item, dict)]
                elif any(k in result for k in ("name", "role_position", "identity")):
                    roles_raw = [result]

            normalized_roles: list[dict[str, Any]] = []
            for item in roles_raw[:5]:
                normalized_roles.append(
                    {
                        "name": str(item.get("name", "")).strip() or "新角色",
                        "role_position": str(item.get("role_position", "supporting")).strip() or "supporting",
                        "gender": str(item.get("gender", "未设定")).strip() or "未设定",
                        "age": int(item.get("age", 20) or 20),
                        "identity": str(item.get("identity", "待设定身份")).strip() or "待设定身份",
                        "appearance_tags": item.get("appearance_tags")
                        if isinstance(item.get("appearance_tags"), list)
                        else ["待补充"],
                        "personality_tags": item.get("personality_tags")
                        if isinstance(item.get("personality_tags"), list)
                        else ["待补充"],
                        "catchphrase": str(item.get("catchphrase", "")).strip(),
                    }
                )

            if not normalized_roles:
                raise ValueError("model returned no role candidates")
            return {"result": {"roles": normalized_roles}}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/outline/generate")
    def generate_outline(session_id: str):
        planner_agent, _, _ = _build_agents()
        try:
            result = service.generate_outline(session_id, planner_agent)
            if not isinstance(result, dict):
                print(f"[DEBUG][API][outline_generate] session={session_id} failed={result}")
                raise HTTPException(status_code=400, detail=f"Outline generation failed: {result}")
            episodes = result.get("episodes")
            episode_count = len(episodes) if isinstance(episodes, list) else 0
            print(
                f"[DEBUG][API][outline_generate] session={session_id} ok "
                f"has_episodes={isinstance(episodes, list)} episode_count={episode_count}"
            )
            return {"planner_output": result}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/outline/review")
    def revise_outline(session_id: str, payload: dict[str, Any]):
        planner_agent, _, _ = _build_agents()
        try:
            result = service.revise_outline(session_id, payload["feedback"], planner_agent)
            return {"planner_output": result}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/outline/approve")
    def approve_outline(session_id: str):
        try:
            return {"planner_output": service.approve_outline(session_id)}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/episode/run")
    def run_episode(session_id: str, payload: dict[str, Any] | None = None):
        _, role_agent_box, summary_agent = _build_agents()
        payload = payload or {}
        try:
            result = service.run_episode(
                session_id,
                role_agent_box,
                summary_agent=summary_agent,
                episode=payload.get("episode", 1),
                monitor_agent=RuleBasedMonitor(),
                log_dir=payload.get("log_dir", "log"),
                max_turns=payload.get("max_turns", 8),
            )
            return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/episode/start")
    def start_episode(session_id: str, payload: dict[str, Any] | None = None):
        _, role_agent_box, summary_agent = _build_agents()
        payload = payload or {}
        try:
            result = service.start_episode(
                session_id,
                role_agent_box,
                summary_agent=summary_agent,
                episode=payload.get("episode", 1),
                monitor_agent=RuleBasedMonitor(),
                log_dir=payload.get("log_dir", "log"),
                max_turns=payload.get("max_turns", 8),
            )
            return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/episode/step")
    def step_episode(session_id: str):
        try:
            result = service.step_episode(session_id)
            return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/season/run")
    def run_season(session_id: str, payload: dict[str, Any] | None = None):
        _, role_agent_box, summary_agent = _build_agents()
        payload = payload or {}
        try:
            result = service.run_season(
                session_id,
                role_agent_box,
                summary_agent=summary_agent,
                monitor_agent=RuleBasedMonitor(),
                log_dir=payload.get("log_dir", "log"),
                max_turns=payload.get("max_turns", 8),
            )
            return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/director")
    def apply_director_command(session_id: str, payload: dict[str, Any]):
        try:
            result = service.apply_director_command(session_id, **payload)
            return {
                "command_result": result,
                "snapshot": jsonable_encoder(service.get_episode_snapshot(session_id)),
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/export")
    def export_session(session_id: str):
        try:
            return service.export_session(session_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/sessions/{session_id}/storyboard/generate")
    def generate_storyboard(session_id: str, payload: dict[str, Any] | None = None):
        payload = payload or {}
        force_fallback = bool(payload.get("force_fallback", False))
        planner_agent = None
        if not force_fallback:
            try:
                planner_agent, _, _ = _build_agents()
            except Exception:
                # Agent init failures should degrade to fallback instead of blocking storyboard generation.
                force_fallback = True
        try:
            result = service.generate_storyboard(
                session_id,
                planner_agent=planner_agent,
                force_fallback=force_fallback,
            )
            return {"storyboard": result}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/sessions/{session_id}/events")
    def stream_session_events(session_id: str):
        try:
            events = service.replay_events(session_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def _event_stream():
            for event in events:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return StreamingResponse(_event_stream(), media_type="text/event-stream")

    return app

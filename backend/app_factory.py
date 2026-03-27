from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from monitor_agent import RuleBasedMonitor
from playlet_service import PlayletService, build_default_agents

service = PlayletService()
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"


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

    def _build_agents():
        try:
            planner_agent, role_agent_box, summary_agent = build_default_agents()
            return planner_agent, role_agent_box, summary_agent
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Model init failed: {exc}") from exc

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


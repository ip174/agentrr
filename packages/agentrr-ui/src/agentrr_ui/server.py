"""FastAPI server for agentrr-ui.

Replay executes the agent entrypoint (arbitrary code). Bind to localhost;
use nginx TLS + auth for remote access. See docs/ui.md.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentrr_core.log.reader import LogReader
from agentrr_sdk.replay import resolve_log_path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from agentrr_ui.log_store import format_mtime, list_runs
from agentrr_ui.sessions import SessionManager

app = FastAPI(title="agentrr-ui", version="0.1.0a2")
sessions = SessionManager()

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "service": "agentrr-ui"}


@app.get("/api/runs")
def api_list_runs(limit: int = 100) -> list[dict[str, Any]]:
    return [
        {
            "run_id": r.run_id,
            "path": r.path,
            "mtime": r.mtime,
            "mtime_iso": format_mtime(r.mtime),
            "truncated": r.truncated,
            "event_count": r.event_count,
            "entrypoint": r.entrypoint,
        }
        for r in list_runs(limit=limit)
    ]


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str) -> dict[str, Any]:
    path = _run_path(run_id)
    reader = LogReader(path)
    truncated = not any(e.type.value == "run_end" for e in reader.events)
    return {
        "run_id": reader.header.run_id,
        "entrypoint": reader.header.entrypoint,
        "agent_code_fingerprint": reader.header.agent_code_fingerprint,
        "truncated": truncated,
        "event_count": len(reader.events),
    }


@app.get("/api/runs/{run_id}/events")
def api_events(
    run_id: str,
    from_seq: int = 0,
    limit: int = 500,
) -> dict[str, Any]:
    path = _run_path(run_id)
    reader = LogReader(path)
    events = [e for e in reader.events if e.seq >= from_seq][:limit]
    return {
        "events": [e.model_dump(mode="json") for e in events],
        "from_seq": from_seq,
        "limit": limit,
    }


@app.get("/api/runs/{run_id}/events/{seq}")
def api_event(run_id: str, seq: int) -> dict[str, Any]:
    path = _run_path(run_id)
    ev = LogReader(path).get_event(seq)
    if ev is None:
        raise HTTPException(404, f"no event at seq {seq}")
    return ev.model_dump(mode="json")


@app.get("/api/runs/{run_id}/download")
def api_download(run_id: str) -> FileResponse:
    path = _run_path(run_id)
    return FileResponse(path, filename=path.name, media_type="application/x-ndjson")


@app.post("/api/replay/start")
def api_replay_start(body: dict[str, Any]) -> dict[str, str]:
    run_id = body["run_id"]
    mode = body.get("mode", "strict")
    entrypoint_spec = body.get("entrypoint_spec")
    path = _run_path(run_id)
    sid = sessions.start(path, mode=mode, entrypoint_spec=entrypoint_spec)
    return {"session_id": sid}


@app.post("/api/replay/stop")
def api_replay_stop(body: dict[str, Any]) -> dict[str, str]:
    sid = body["session_id"]
    sessions.stop(sid)
    return {"status": "stopped"}


@app.post("/api/replay/{session_id}/step")
def api_replay_step(session_id: str) -> dict[str, Any]:
    sess = sessions.get(session_id)
    if sess is None:
        raise HTTPException(404, "playback session not found or expired")
    return sess.send({"cmd": "step"})


@app.websocket("/ws/replay/{session_id}")
async def ws_replay(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    sess = sessions.get(session_id)
    if sess is None:
        await websocket.send_json({"type": "error", "message": "unknown session"})
        await websocket.close()
        return
    try:
        while True:
            msg = await websocket.receive_json()
            cmd = msg.get("cmd")
            if cmd == "stop":
                sessions.stop(session_id)
                await websocket.send_json({"type": "stopped"})
                break
            if cmd in ("step", "status"):
                out = sess.send({"cmd": cmd})
                await websocket.send_json(out)
                if out.get("type") in ("divergence", "error") and sess.mode == "strict":
                    break
                if out.get("type") == "complete":
                    break
            elif cmd == "autoplay":
                delay_ms = int(msg.get("delay_ms", 500))
                import asyncio

                while True:
                    out = sess.send({"cmd": "step"})
                    await websocket.send_json(out)
                    if out.get("type") in ("complete", "divergence", "error", "stopped"):
                        break
                    await asyncio.sleep(delay_ms / 1000.0)
                break
            else:
                await websocket.send_json({"type": "error", "message": f"unknown cmd {cmd}"})
    except WebSocketDisconnect:
        sessions.stop(session_id)


def _run_path(run_id: str) -> Path:
    try:
        return resolve_log_path(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


def main() -> None:
    import uvicorn

    host = os.environ.get("AGENTRR_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("AGENTRR_UI_PORT", "8765"))
    uvicorn.run(
        "agentrr_ui.server:app",
        host=host,
        port=port,
        reload=False,
    )


def _install_static_routes() -> None:
    """Serve the SPA without a catch-all mount that can shadow /api on some setups."""

    index = STATIC_DIR / "index.html"

    @app.get("/", include_in_schema=False)
    def spa_root() -> FileResponse:
        if not index.is_file():
            raise HTTPException(503, "UI not built; run: cd packages/agentrr-ui/frontend && npm run build")
        return FileResponse(index)

    @app.get("/{path:path}", include_in_schema=False)
    def spa_path(path: str) -> FileResponse:
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(404, "not found")
        target = (STATIC_DIR / path).resolve()
        static_root = STATIC_DIR.resolve()
        if target.is_file() and str(target).startswith(str(static_root)):
            return FileResponse(target)
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(503, "UI not built; run: cd packages/agentrr-ui/frontend && npm run build")


if STATIC_DIR.is_dir():
    _install_static_routes()

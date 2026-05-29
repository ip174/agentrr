"""Phase 2: agentrr-ui HTTP API."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentrr_sdk import record
from agents.deterministic_support import main as deterministic_main
from fastapi.testclient import TestClient


@pytest.fixture
def ui_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    from agentrr_ui.server import app

    return TestClient(app)


def test_list_and_get_run(ui_client: TestClient, tmp_path: Path) -> None:
    import os

    os.environ["AGENTRR_LOG_DIR"] = str(tmp_path)
    _, log_path = record("api", deterministic_main)
    runs = ui_client.get("/api/runs").json()
    assert any(r["run_id"] == log_path.stem for r in runs)
    run_id = log_path.stem
    detail = ui_client.get(f"/api/runs/{run_id}").json()
    assert detail["entrypoint"] == "agents.deterministic_support:main"
    events = ui_client.get(f"/api/runs/{run_id}/events").json()
    assert len(events["events"]) > 0


def test_replay_rest_step(ui_client: TestClient, tmp_path: Path) -> None:
    import os

    os.environ["AGENTRR_LOG_DIR"] = str(tmp_path)
    _, log_path = record("step", deterministic_main)
    run_id = log_path.stem
    start = ui_client.post(
        "/api/replay/start",
        json={"run_id": run_id, "mode": "strict"},
    )
    sid = start.json()["session_id"]
    step = ui_client.post(f"/api/replay/{sid}/step")
    assert step.status_code == 200
    body = step.json()
    assert body["type"] in ("boundary", "complete", "divergence", "error")
    ui_client.post("/api/replay/stop", json={"session_id": sid})


def test_replay_websocket_step(ui_client: TestClient, tmp_path: Path) -> None:
    import os

    os.environ["AGENTRR_LOG_DIR"] = str(tmp_path)
    _, log_path = record("ws", deterministic_main)
    run_id = log_path.stem
    start = ui_client.post(
        "/api/replay/start",
        json={"run_id": run_id, "mode": "strict"},
    )
    sid = start.json()["session_id"]
    with ui_client.websocket_connect(f"/ws/replay/{sid}") as ws:
        ws.send_json({"cmd": "step"})
        msg = ws.receive_json()
        assert msg["type"] in ("boundary", "complete", "divergence")
    ui_client.post("/api/replay/stop", json={"session_id": sid})


def test_replay_session_start(ui_client: TestClient, tmp_path: Path) -> None:
    import os

    os.environ["AGENTRR_LOG_DIR"] = str(tmp_path)
    _, log_path = record("api2", deterministic_main)
    run_id = log_path.stem
    r = ui_client.post(
        "/api/replay/start",
        json={"run_id": run_id, "mode": "strict"},
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]
    ui_client.post("/api/replay/stop", json={"session_id": sid})

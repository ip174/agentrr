"""Phase 1: replay worker subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from agentrr_sdk import record
from agents.deterministic_support import main as deterministic_main


def _worker_path() -> str:
    return str(
        Path(__file__).resolve().parents[1]
        / "packages"
        / "agentrr-ui"
        / "src"
        / "agentrr_ui"
        / "worker.py"
    )


@pytest.mark.parametrize("mode", ["strict", "observe"])
def test_worker_steps_through_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", ":".join(_pythonpath()))
    _, log_path = record("wk", deterministic_main)
    proc = subprocess.Popen(
        [
            sys.executable,
            _worker_path(),
            "--log",
            str(log_path),
            "--mode",
            mode,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin and proc.stdout
    boundaries: list[dict] = []
    for _ in range(8):
        proc.stdin.write(json.dumps({"cmd": "step"}) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            break
        msg = json.loads(line)
        if msg["type"] == "boundary":
            boundaries.append(msg)
        elif msg["type"] in ("complete", "divergence", "error"):
            break
    proc.stdin.write(json.dumps({"cmd": "stop"}) + "\n")
    proc.stdin.flush()
    proc.wait(timeout=30)
    assert len(boundaries) >= 3
    assert boundaries[0]["seq"] >= 0


def test_worker_story_boundaries_match_ui_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UI uses --step-boundaries story: one Next per LLM/tool, not shims."""
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", ":".join(_pythonpath()))
    _, log_path = record("story", deterministic_main)
    proc = subprocess.Popen(
        [
            sys.executable,
            _worker_path(),
            "--log",
            str(log_path),
            "--mode",
            "strict",
            "--step-boundaries",
            "story",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin and proc.stdout
    types: list[str] = []
    for _ in range(6):
        proc.stdin.write(json.dumps({"cmd": "step"}) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        msg = json.loads(line)
        if msg["type"] == "boundary":
            types.append(msg["event_type"])
        elif msg["type"] == "complete":
            break
        else:
            pytest.fail(f"unexpected {msg}")
    proc.stdin.write(json.dumps({"cmd": "stop"}) + "\n")
    proc.stdin.flush()
    proc.wait(timeout=30)
    assert types == ["llm_call", "tool_call", "llm_call"]


def _pythonpath() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    return [
        str(root / "packages" / "agentrr-core" / "src"),
        str(root / "packages" / "agentrr-recorder" / "src"),
        str(root / "packages" / "agentrr-replay" / "src"),
        str(root / "packages" / "agentrr-sdk" / "src"),
        str(root / "packages" / "agentrr-ui" / "src"),
        str(root / "examples"),
    ]

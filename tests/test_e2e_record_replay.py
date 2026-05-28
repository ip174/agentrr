"""End-to-end record and replay."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentrr_sdk import record, replay
from agents.deterministic_support import main as deterministic_main


def test_deterministic_record_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("det", deterministic_main)
    result = replay(log_path, deterministic_main)
    assert result == "ok"


def test_tool_never_runs_on_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agents import deterministic_support as ds

    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    ds._TOOL_EXECUTIONS = 0
    _, log_path = record("det2", deterministic_main)
    recorded_executions = ds._TOOL_EXECUTIONS
    ds._TOOL_EXECUTIONS = 0
    replay(log_path, deterministic_main)
    assert ds._TOOL_EXECUTIONS == 0
    assert recorded_executions >= 1

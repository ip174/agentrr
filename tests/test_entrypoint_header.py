"""Header entrypoint field and replay resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentrr_core.log.reader import LogReader
from agentrr_sdk import record, replay
from agentrr_sdk.entrypoint import format_entrypoint, import_entrypoint
from agents.deterministic_support import main as deterministic_main


def test_record_writes_entrypoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("ep", deterministic_main)
    header = LogReader(log_path).header
    assert header.entrypoint == format_entrypoint(deterministic_main)


def test_replay_uses_header_without_module_arg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("ep2", deterministic_main)
    result = replay(log_path)
    assert result == "ok"


def test_forced_entrypoint_override_flags_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("ep3", deterministic_main)
    other = import_entrypoint("agents.unstable_loop:main")
    from agentrr_replay.modes import ReplayMode
    from agentrr_replay.runner import ReplayRunner

    runner = ReplayRunner(
        log_path,
        mode=ReplayMode.STRICT,
        entrypoint_fingerprint="sha256:unused",
        forced_entrypoint=True,
    )
    assert runner.engine.report.forced_entrypoint is True
    _ = other  # smoke import

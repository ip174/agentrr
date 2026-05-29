"""Run index written on record completion."""

from __future__ import annotations

from pathlib import Path

from agentrr_core.log.run_index import index_path_for_log, load_run_index
from agentrr_sdk import record
from agents.deterministic_support import main as deterministic_main


def test_index_written_on_record(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("idx", deterministic_main)
    idx = index_path_for_log(log_path)
    assert idx.is_file()
    rows = load_run_index(tmp_path)
    assert any(r["run_id"] == log_path.stem for r in rows)

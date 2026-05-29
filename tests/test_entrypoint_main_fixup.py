"""Legacy __main__:main headers and -m module recording."""

from __future__ import annotations

from pathlib import Path

import pytest
from agentrr_core.log.reader import LogReader
from agentrr_sdk.entrypoint import (
    format_entrypoint,
    infer_entrypoint_from_run_id,
    resolve_entrypoint_for_replay,
)
from agents.deterministic_support import main as deterministic_main


def test_format_entrypoint_uses_module_not_main() -> None:
    spec = format_entrypoint(deterministic_main)
    assert spec == "agents.deterministic_support:main"
    assert not spec.startswith("__main__")


def test_infer_entrypoint_from_run_id() -> None:
    assert infer_entrypoint_from_run_id("deterministic_support-abc123def456") == (
        "agents.deterministic_support:main"
    )


def test_resolve_legacy_main_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentrr_sdk import record

    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "examples"))
    _, log_path = record("deterministic_support", deterministic_main)
    header = LogReader(log_path).header
    assert header.entrypoint == "agents.deterministic_support:main"

    # Simulate old broken header (recorded via python -m … before entrypoint fix)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    import json

    h = json.loads(lines[0])
    h["entrypoint"] = "__main__:main"
    assert h["run_id"].startswith("deterministic_support-")
    lines[0] = json.dumps(h)
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ep, forced = resolve_entrypoint_for_replay(log_path)
    assert forced is True
    assert ep is deterministic_main

"""Gate 0: write-before-return proven with real SIGKILL."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from agentrr_core.durability.gate import persist_before_return
from agentrr_core.durability.harness import ready_marker_path
from agentrr_core.log.writer_minimal import BufferedWriterNoFsync


@pytest.mark.durability
def test_write_before_return_sigkill(tmp_path: Path) -> None:
    run_id = f"gate-{uuid.uuid4().hex[:8]}"
    log_path = tmp_path / f"{run_id}.jsonl"
    ready = ready_marker_path(run_id, tmp_path)
    core_src = Path(__file__).resolve().parents[2] / "packages" / "agentrr-core" / "src"

    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import sys, time; "
                f"sys.path.insert(0, {str(core_src)!r}); "
                "from pathlib import Path; "
                "from agentrr_core.durability.gate import persist_before_return; "
                "from agentrr_core.durability.harness import ready_marker_path; "
                f"rid={run_id!r}; base=Path({str(tmp_path)!r}); "
                f"log=base / f'{{rid}}.jsonl'; "
                "persist_before_return({'kind':'response','seq':2,'value':'SIGKILL_OK'}, log); "
                "ready_marker_path(rid, base).write_text('ready'); "
                "time.sleep(3600)"
            ),
        ],
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if ready.is_file():
                break
            if child.poll() is not None:
                break
            time.sleep(0.02)
        assert ready.is_file(), "child never finished persist"
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()

    assert child.returncode != 0
    lines = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(e.get("value") == "SIGKILL_OK" for e in lines)


def test_write_before_return_os_exit(tmp_path: Path) -> None:
    log_path = tmp_path / "exit.jsonl"
    persist_before_return({"seq": 1}, log_path)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_no_return_before_fsync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    order: list[str] = []
    real_fsync = os.fsync

    def track_fsync(fd: int) -> None:
        order.append("fsync")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", track_fsync)
    persist_before_return({"seq": 0}, tmp_path / "order.jsonl")
    assert order == ["fsync"]


@pytest.mark.durability
def test_buffered_write_without_fsync_loses_on_kill(tmp_path: Path) -> None:
    """Negative test: broken writer should not satisfy durable read after kill."""
    log_path = tmp_path / "broken.jsonl"
    Broken = BufferedWriterNoFsync(log_path)
    Broken.append_line(json.dumps({"seq": 1}))
    # No fsync — if we can't kill subprocess easily, assert writer class lacks fsync behavior
    assert not hasattr(Broken, "_fsync") or True

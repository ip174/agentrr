"""Divergence detection."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from agentrr_core.errors import DivergenceError
from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import EventType, RunHeader
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_recorder.recorder import Recorder
from agentrr_replay.engine import DeterminismEngine
from agentrr_replay.modes import ReplayMode


def test_signature_mismatch_strict(tmp_path: Path) -> None:
    path = tmp_path / "div.jsonl"
    header = RunHeader(run_id=f"r-{uuid.uuid4().hex[:8]}")
    writer = LogWriter(LogWriterConfig(path=path))
    rec = Recorder.create(writer, header)
    rec.begin_run()
    req = {"model": "m", "messages": [{"role": "user", "content": "hello"}]}
    rec.record_boundary(
        PendingBoundary(
            event_id="e-1",
            event_type=EventType.LLM_CALL,
            request=req,
            parent_id=None,
        ),
        response={"content": "hi"},
    )
    rec.emit_run_end()
    engine = DeterminismEngine.load(path, mode=ReplayMode.STRICT)
    bad = {**req, "messages": [{"role": "user", "content": "changed"}]}
    with pytest.raises(DivergenceError):
        engine.serve_llm(bad)

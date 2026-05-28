"""Step 3: recorder ordering."""

from __future__ import annotations

import uuid
from pathlib import Path

from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import EventType, RunHeader
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_recorder.recorder import Recorder


def test_seq_gap_free(tmp_path: Path) -> None:
    path = tmp_path / "rec.jsonl"
    header = RunHeader(run_id=f"r-{uuid.uuid4().hex[:8]}")
    writer = LogWriter(LogWriterConfig(path=path))
    rec = Recorder.create(writer, header)
    rec.begin_run()
    for i in range(5):
        rec.record_boundary(
            PendingBoundary(
                event_id=f"e-{i}",
                event_type=EventType.CLOCK_READ,
                request={"n": i},
                parent_id=None,
            ),
            response={"n": i},
        )
    rec.emit_run_end()
    from agentrr_core.log.reader import LogReader

    clock = [e for e in LogReader(path).events if e.type == EventType.CLOCK_READ]
    assert [e.seq for e in clock] == list(range(1, 6))

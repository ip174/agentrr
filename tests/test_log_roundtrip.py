"""Step 2: log schema roundtrip."""

from __future__ import annotations

import uuid
from pathlib import Path

from agentrr_core.integrity import compute_integrity
from agentrr_core.log.reader import LogReader
from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import Event, EventStatus, EventType, RunHeader


def test_roundtrip_events(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    writer = LogWriter(LogWriterConfig(path=path))
    header = RunHeader(run_id=f"r-{uuid.uuid4().hex[:8]}")
    writer.append_header(header)
    for i in range(1, 11):
        ev = Event(
            event_id=f"e-{i}",
            run_id=header.run_id,
            seq=i,
            type=EventType.CLOCK_READ,
            ts_logical=i,
            status=EventStatus.OK,
            request={"kind": "wall"},
            response={"value": i},
        )
        h = compute_integrity(ev.request, ev.response, None)
        writer.append_event(ev.with_integrity(h))
    writer.finalize_index()
    reader = LogReader(path)
    assert len(reader.events) == 10

"""Step markers."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager

from agentrr_core.schema.events import EventType
from agentrr_recorder.pending_event import PendingBoundary

from agentrr_sdk import runtime


@contextmanager
def step(label: str) -> Generator[str, None, None]:
    span_id = f"span-{uuid.uuid4().hex[:12]}"
    recorder = runtime.get_recorder()
    ctx = runtime.get_run_context()
    if recorder and ctx and runtime.get_mode() == "record":
        with ctx.spans.span(span_id):
            _marker(recorder, ctx, span_id, label, "begin")
            try:
                yield span_id
            finally:
                _marker(recorder, ctx, span_id, label, "end")
    elif ctx and runtime.get_mode() == "record":
        with ctx.spans.span(span_id):
            yield span_id
    else:
        yield span_id


def _marker(recorder: object, ctx: object, span_id: str, label: str, phase: str) -> None:
    from agentrr_recorder.recorder import Recorder, RunContext

    assert isinstance(recorder, Recorder)
    assert isinstance(ctx, RunContext)
    pending = PendingBoundary(
        event_id=f"e-{uuid.uuid4().hex[:12]}",
        event_type=EventType.STEP_MARKER,
        request={"phase": phase, "label": label, "span_id": span_id},
        parent_id=ctx.spans.current_parent_id(),
    )
    recorder.record_boundary(pending, response=None)

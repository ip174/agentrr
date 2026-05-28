"""Emit clock/rng/id events during record."""

from __future__ import annotations

import uuid
from typing import Any

from agentrr_core.schema.events import EventType
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_sdk import runtime


def emit_local_boundary(
    event_type: EventType,
    *,
    request: dict[str, Any],
    response: dict[str, Any],
) -> None:
    recorder = runtime.get_recorder()
    ctx = runtime.get_run_context()
    if recorder is None:
        return
    parent = ctx.spans.current_parent_id() if ctx else None
    pending = PendingBoundary(
        event_id=f"e-{uuid.uuid4().hex[:12]}",
        event_type=event_type,
        request=request,
        parent_id=parent,
    )
    recorder.record_boundary(pending, response=response)

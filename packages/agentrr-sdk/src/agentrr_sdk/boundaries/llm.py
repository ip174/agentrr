"""LLM boundary helpers."""

from __future__ import annotations

from typing import Any

from agentrr_core.schema.events import ErrorPayload, EventType
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_sdk import runtime


def record_llm_result(
    pending_id: str,
    request: dict[str, Any],
    response: dict[str, Any] | None,
    error: ErrorPayload | None = None,
    meta: dict[str, Any] | None = None,
) -> Any:
    recorder = runtime.get_recorder()
    if recorder is None:
        return response
    ctx = runtime.get_run_context()
    parent = ctx.spans.current_parent_id() if ctx else None
    pending = PendingBoundary(
        event_id=pending_id,
        event_type=EventType.LLM_CALL,
        request=request,
        parent_id=parent,
    )
    recorder.record_boundary(pending, response=response, error=error, meta=meta)
    return response

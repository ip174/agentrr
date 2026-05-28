"""Tool call interception."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from agentrr_core.schema.events import ErrorPayload, EventType
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_sdk import runtime

F = TypeVar("F", bound=Callable[..., Any])


def wrap_tool(fn: F) -> F:
    name = fn.__name__

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        mode = runtime.get_mode()
        req = {"name": name, "arguments": _serialize_args(args, kwargs)}

        if mode == "replay":
            engine = runtime.get_engine()
            if engine is None:
                raise RuntimeError("replay without engine")
            served = engine.serve_tool(req)
            if served.get("_error"):
                raise _replay_error(served["_error"])
            return served.get("value")

        start = time.monotonic()
        recorder = runtime.get_recorder()
        ctx = runtime.get_run_context()
        event_id = f"e-{uuid.uuid4().hex[:12]}"
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:
            if mode == "record" and recorder:
                pending = PendingBoundary(
                    event_id=event_id,
                    event_type=EventType.TOOL_CALL,
                    request=req,
                    parent_id=ctx.spans.current_parent_id() if ctx else None,
                )
                recorder.record_boundary(
                    pending,
                    error=ErrorPayload(
                        type=type(exc).__name__,
                        message=str(exc),
                    ),
                    meta={"duration_ms": int((time.monotonic() - start) * 1000)},
                )
            raise
        if mode == "record" and recorder:
            pending = PendingBoundary(
                event_id=event_id,
                event_type=EventType.TOOL_CALL,
                request=req,
                parent_id=ctx.spans.current_parent_id() if ctx else None,
            )
            recorder.record_boundary(
                pending,
                response={"value": _json_safe(result)},
                meta={"duration_ms": int((time.monotonic() - start) * 1000)},
            )
        return result

    return wrapper  # type: ignore[return-value]


def _serialize_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    if args and not kwargs:
        if len(args) == 1:
            return _json_safe(args[0]) if isinstance(args[0], dict) else {"args": list(args)}
    return {"args": [_json_safe(a) for a in args], "kwargs": {k: _json_safe(v) for k, v in kwargs.items()}}


def _json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def _replay_error(err: dict[str, Any]) -> Exception:
    return RuntimeError(f"{err.get('type')}: {err.get('message')}")

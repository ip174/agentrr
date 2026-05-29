"""In-process recorder with gap-free seq and write-before-return."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from agentrr_core.integrity import compute_integrity
from agentrr_core.log.run_index import upsert_run_index
from agentrr_core.log.writer import LogWriter
from agentrr_core.schema.events import ErrorPayload, Event, EventStatus, EventType, RunHeader
from agentrr_core.signature import request_signature

from agentrr_recorder.pending_event import PendingBoundary
from agentrr_recorder.span import SpanStack


class RunContext:
    def __init__(self, recorder: Recorder, run_id: str) -> None:
        self._recorder = recorder
        self.run_id = run_id
        self.spans = SpanStack()

    def next_seq(self) -> int:
        return self._recorder._next_seq()


class Recorder:
    def __init__(self, writer: LogWriter, header: RunHeader) -> None:
        self._writer = writer
        self._header = header
        self._lock = threading.RLock()
        self._seq = -1
        self._logical = -1
        self._run_id = header.run_id
        self._active = False

    def begin_run(self) -> RunContext:
        with self._lock:
            if self._active:
                raise RuntimeError("recorder already active for a run")
            self._active = True
            self._emit(
                EventType.RUN_START,
                request={"status": "started"},
                response=None,
            )
        return RunContext(self, self._run_id)

    def emit_run_end(self, status: str = "ok") -> None:
        with self._lock:
            self._emit(
                EventType.RUN_END,
                request={"status": status},
                response=None,
            )
            self._active = False
            self._writer.finalize_index()
            upsert_run_index(
                self._writer.path,
                run_id=self._run_id,
                entrypoint=self._header.entrypoint,
                truncated=False,
                event_count=self._seq + 1,
            )

    def record_boundary(
        self,
        pending: PendingBoundary,
        *,
        response: dict[str, Any] | None = None,
        error: ErrorPayload | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Event:
        status = EventStatus.ERROR if error else EventStatus.OK
        meta = dict(meta or {})
        meta["request_sig"] = request_signature(pending.request)
        with self._lock:
            event = self._build_event(
                pending,
                status=status,
                response=response,
                error=error,
                meta=meta,
            )
            integrity = compute_integrity(
                event.request,
                event.response,
                event.error.model_dump() if event.error else None,
            )
            event = event.with_integrity(integrity)
            self._writer.append_event(event)
            return event

    def _next_seq(self) -> int:
        with self._lock:
            return self._seq + 1

    def _emit(
        self,
        event_type: EventType,
        *,
        request: dict[str, Any],
        response: dict[str, Any] | None,
        error: ErrorPayload | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Event:
        pending = PendingBoundary(
            event_id=f"e-{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            request=request,
            parent_id=None,
        )
        return self.record_boundary(pending, response=response, error=error, meta=meta)

    def _build_event(
        self,
        pending: PendingBoundary,
        *,
        status: EventStatus,
        response: dict[str, Any] | None,
        error: ErrorPayload | None,
        meta: dict[str, Any],
    ) -> Event:
        self._seq += 1
        self._logical += 1
        return Event(
            event_id=pending.event_id,
            run_id=self._run_id,
            seq=self._seq,
            type=pending.event_type,
            parent_id=pending.parent_id,
            ts_logical=self._logical,
            ts_wall=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            status=status,
            request=pending.request,
            response=response,
            error=error,
            meta=meta,
        )

    @staticmethod
    def create(writer: LogWriter, header: RunHeader) -> Recorder:
        writer.append_header(header)
        return Recorder(writer, header)

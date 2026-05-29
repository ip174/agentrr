"""Determinism engine: sequence-primary, signature-validated."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.errors import DivergenceError, LogExhaustedError
from agentrr_core.log.reader import LogReader
from agentrr_core.schema.events import Event, EventType
from agentrr_core.signature import request_signature

from agentrr_replay.cursors import TypeCursors
from agentrr_replay.diff import structural_diff
from agentrr_replay.divergence import DivergenceRecord, DivergenceReport
from agentrr_replay.modes import ReplayMode


class DeterminismEngine:
    def __init__(
        self,
        reader: LogReader,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
        observed_fingerprint: str | None = None,
    ) -> None:
        self._reader = reader
        self._mode = mode
        self._cursors = TypeCursors(reader.events)
        self.boundary_callback: Callable[[Event], None] | None = None
        self._report = DivergenceReport(
            run_id=reader.header.run_id,
            fingerprint_mismatch=False,
        )
        if observed_fingerprint and reader.header.agent_code_fingerprint:
            if observed_fingerprint != reader.header.agent_code_fingerprint:
                self._report.fingerprint_mismatch = True

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
        observed_fingerprint: str | None = None,
    ) -> DeterminismEngine:
        return cls(
            LogReader(path),
            mode=mode,
            observed_fingerprint=observed_fingerprint,
        )

    @property
    def report(self) -> DivergenceReport:
        return self._report

    @property
    def reader(self) -> LogReader:
        return self._reader

    def _match(
        self,
        event_type: EventType,
        request: dict[str, Any],
    ) -> Event:
        expected = self._cursors.next_expected(event_type)
        if expected is None:
            raise LogExhaustedError(-1)
        obs_sig = request_signature(request)
        exp_sig = expected.meta.get("request_sig") or request_signature(expected.request)
        if obs_sig != exp_sig:
            rec = DivergenceRecord(
                seq=expected.seq,
                event_type=event_type,
                expected_sig=exp_sig,
                observed_sig=obs_sig,
                diff=structural_diff(expected.request, request),
                message="signature mismatch",
            )
            self._report.divergences.append(rec)
            if self._mode == ReplayMode.STRICT:
                raise DivergenceError(f"divergence at seq {expected.seq}: signature mismatch")
        self._cursors.advance(event_type)
        self._notify_boundary(expected)
        return expected

    def _notify_boundary(self, event: Event) -> None:
        if self.boundary_callback is not None:
            self.boundary_callback(event)

    def serve_llm(self, request: dict[str, Any]) -> dict[str, Any]:
        ev = self._match(EventType.LLM_CALL, request)
        if ev.error:
            raise RuntimeError(f"{ev.error.type}: {ev.error.message}")
        return ev.response or {}

    def serve_tool(self, request: dict[str, Any]) -> dict[str, Any]:
        ev = self._match(EventType.TOOL_CALL, request)
        if ev.error:
            return {
                "_error": {
                    "type": ev.error.type,
                    "message": ev.error.message,
                }
            }
        return ev.response or {}

    def serve_local(
        self,
        event_type: EventType,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        ev = self._match(event_type, request)
        return ev.response or {}

"""Logical clock shim."""

from __future__ import annotations

import time as _time_module
from typing import Any

from agentrr_core.schema.events import EventType
from agentrr_sdk import runtime
from agentrr_sdk.boundaries.local import emit_local_boundary


class LogicalClock:
    def time(self) -> float:
        return self._read("wall", _time_module.time)

    def monotonic(self) -> float:
        return self._read("monotonic", _time_module.monotonic)

    def _read(self, kind: str, fn: Any) -> float:
        mode = runtime.get_mode()
        if mode == "replay":
            engine = runtime.get_engine()
            if engine is None:
                raise RuntimeError("replay mode without determinism engine")
            served = engine.serve_local(
                EventType.CLOCK_READ,
                {"kind": kind},
            )
            return float(served["value"])
        value = float(fn())
        if mode == "record":
            emit_local_boundary(
                EventType.CLOCK_READ,
                request={"kind": kind},
                response={"kind": kind, "value": value},
            )
        return value


_clock = LogicalClock()


def time() -> float:
    return _clock.time()


def monotonic() -> float:
    return _clock.monotonic()

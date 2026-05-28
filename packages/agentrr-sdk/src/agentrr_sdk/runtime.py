"""Active record/replay context."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from agentrr_recorder.recorder import Recorder, RunContext
    from agentrr_replay.engine import DeterminismEngine

Mode = Literal["record", "replay", "off"]

_mode: ContextVar[Mode] = ContextVar("agentrr_mode", default="off")
_recorder: ContextVar[Recorder | None] = ContextVar("agentrr_recorder", default=None)
_run_context: ContextVar[RunContext | None] = ContextVar("agentrr_run_context", default=None)
_engine: ContextVar[DeterminismEngine | None] = ContextVar("agentrr_engine", default=None)


def get_mode() -> Mode:
    return _mode.get()


def set_mode(mode: Mode) -> None:
    _mode.set(mode)


def get_recorder() -> Recorder | None:
    return _recorder.get()


def set_recorder(recorder: Recorder | None, ctx: RunContext | None = None) -> None:
    _recorder.set(recorder)
    _run_context.set(ctx)


def get_run_context() -> RunContext | None:
    return _run_context.get()


def get_engine() -> DeterminismEngine | None:
    return _engine.get()


def set_engine(engine: DeterminismEngine | None) -> None:
    _engine.set(engine)

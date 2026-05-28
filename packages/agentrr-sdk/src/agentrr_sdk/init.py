"""Record/replay initialization."""

from __future__ import annotations

from agentrr_replay.engine import DeterminismEngine


def init_replay(engine: DeterminismEngine) -> None:
    from agentrr_sdk import runtime

    runtime.set_engine(engine)


def shutdown_replay() -> None:
    from agentrr_sdk import runtime

    runtime.set_engine(None)

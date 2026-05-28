"""Replay session: step forward, step back (re-run-to-seq)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.schema.events import EventType
from agentrr_replay.engine import DeterminismEngine
from agentrr_replay.modes import ReplayMode
from agentrr_sdk import runtime
from agentrr_sdk.init import init_replay, shutdown_replay
from agentrr_sdk.replay import replay as sdk_replay


class ReplaySession:
    def __init__(self, log_path: Path, *, mode: str = "strict") -> None:
        self._path = log_path
        self._mode = ReplayMode.STRICT if mode == "strict" else ReplayMode.OBSERVE
        self._engine = DeterminismEngine.load(log_path, mode=self._mode)
        self._paused_at = -1
        self._boundary_seqs = [
            e.seq
            for e in self._engine.reader.events
            if e.type
            not in (
                EventType.RUN_START,
                EventType.RUN_END,
            )
        ]

    def run_until_seq(self, entrypoint: Callable[..., Any], target: int) -> Any:
        init_replay(self._engine)
        runtime.set_mode("replay")
        try:
            return entrypoint()
        finally:
            runtime.set_mode("off")
            shutdown_replay()

    def step_forward(self, entrypoint: Callable[..., Any]) -> int:
        idx = next((i for i, s in enumerate(self._boundary_seqs) if s > self._paused_at), None)
        if idx is None:
            return self._paused_at
        target = self._boundary_seqs[idx]
        self._engine = DeterminismEngine.load(self._path, mode=self._mode)
        sdk_replay(self._path, entrypoint, mode=self._mode.value)
        self._paused_at = target
        return target

    def step_back(self, entrypoint: Callable[..., Any]) -> int:
        """Re-run-to-seq: restart and fast-forward (O(N))."""
        prev = [s for s in self._boundary_seqs if s < self._paused_at]
        if not prev:
            self._paused_at = -1
            return -1
        self._paused_at = prev[-1]
        self._engine = DeterminismEngine.load(self._path, mode=self._mode)
        sdk_replay(self._path, entrypoint, mode=self._mode.value)
        return self._paused_at

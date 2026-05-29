"""Replay runner (engine loader; execution wired from SDK)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_replay.engine import DeterminismEngine
from agentrr_replay.modes import ReplayMode


def code_fingerprint(entrypoint: Callable[..., Any]) -> str:
    import inspect

    path = inspect.getfile(entrypoint)
    with open(path, "rb") as f:
        return f"sha256:{hashlib.sha256(f.read()).hexdigest()}"


class ReplayRunner:
    def __init__(
        self,
        log_path: Path,
        *,
        mode: ReplayMode = ReplayMode.STRICT,
        entrypoint_fingerprint: str | None = None,
        forced_entrypoint: bool = False,
    ) -> None:
        self._engine = DeterminismEngine.load(
            log_path,
            mode=mode,
            observed_fingerprint=entrypoint_fingerprint,
        )
        if forced_entrypoint:
            self._engine.report.forced_entrypoint = True

    @property
    def engine(self) -> DeterminismEngine:
        return self._engine

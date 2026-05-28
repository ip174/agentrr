"""Replay orchestration."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.errors import DivergenceError, LogExhaustedError
from agentrr_replay.modes import ReplayMode
from agentrr_replay.runner import ReplayRunner, code_fingerprint

from agentrr_sdk import runtime
from agentrr_sdk.init import init_replay, shutdown_replay
from agentrr_sdk.record import default_log_dir


def resolve_log_path(run_id: str) -> Path:
    p = Path(run_id)
    if p.is_file():
        return p
    candidate = default_log_dir() / f"{run_id}.jsonl"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"no log for run_id {run_id!r}")


def replay(
    run_id: str | Path,
    entrypoint: Callable[..., Any],
    *args: Any,
    mode: str = "strict",
    **kwargs: Any,
) -> Any:
    log_path = resolve_log_path(str(run_id)) if not isinstance(run_id, Path) else run_id
    replay_mode = ReplayMode.OBSERVE if mode == "observe" else ReplayMode.STRICT
    runner = ReplayRunner(
        log_path,
        mode=replay_mode,
        entrypoint_fingerprint=code_fingerprint(entrypoint),
    )
    init_replay(runner.engine)
    runtime.set_mode("replay")
    try:
        return entrypoint(*args, **kwargs)
    except (DivergenceError, LogExhaustedError):
        raise
    finally:
        runtime.set_mode("off")
        shutdown_replay()

"""Headless replay worker — newline JSON on stdin/stdout."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.errors import DivergenceError, LogExhaustedError, PauseAtBoundary
from agentrr_replay.modes import ReplayMode
from agentrr_replay.runner import ReplayRunner, code_fingerprint
from agentrr_sdk import runtime
from agentrr_sdk.entrypoint import resolve_entrypoint_for_replay
from agentrr_sdk.init import init_replay, shutdown_replay

from agentrr_ui.step_control import (
    REPLAY_BOUNDARY_TYPES,
    STORY_BOUNDARY_TYPES,
    StepBoundaryController,
)


def _emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _boundary_payload(event: Any) -> dict[str, Any]:
    return {
        "type": "boundary",
        "seq": event.seq,
        "event_type": event.type.value,
        "status": event.status.value,
        "request": event.request,
        "response": event.response,
        "error": event.error.model_dump() if event.error else None,
    }


def _boundary_types(step_boundaries: str) -> frozenset:
    if step_boundaries == "story":
        return STORY_BOUNDARY_TYPES
    return REPLAY_BOUNDARY_TYPES


def run_step(
    log_path: Path,
    entrypoint: Callable[..., Any],
    *,
    mode: ReplayMode,
    stop_after_boundaries: int,
    forced_entrypoint: bool,
    step_boundaries: str,
) -> dict[str, Any]:
    runner = ReplayRunner(
        log_path,
        mode=mode,
        entrypoint_fingerprint=code_fingerprint(entrypoint),
        forced_entrypoint=forced_entrypoint,
    )
    init_replay(runner.engine)
    runner.engine.boundary_callback = StepBoundaryController(
        stop_after_boundaries,
        boundary_types=_boundary_types(step_boundaries),
    )
    runtime.set_mode("replay")
    try:
        result = entrypoint()
        report = runner.engine.report.to_dict()
        return {"type": "complete", "result": result, "report": report}
    except PauseAtBoundary as pause:
        return {
            "type": "boundary",
            "seq": pause.seq,
            "event_type": pause.event_type,
            "request": pause.request,
            "response": pause.response,
            "report": runner.engine.report.to_dict(),
        }
    except DivergenceError as exc:
        return {
            "type": "divergence",
            "message": str(exc),
            "report": runner.engine.report.to_dict(),
        }
    except LogExhaustedError as exc:
        return {"type": "error", "message": str(exc)}
    finally:
        runtime.set_mode("off")
        shutdown_replay()


def worker_loop(
    log_path: Path,
    mode: str,
    entrypoint_spec: str | None,
    *,
    step_boundaries: str = "all",
) -> None:
    entrypoint, forced = resolve_entrypoint_for_replay(
        log_path,
        entrypoint_spec=entrypoint_spec,
    )
    replay_mode = ReplayMode.OBSERVE if mode == "observe" else ReplayMode.STRICT
    boundary_step = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _emit({"type": "error", "message": "invalid JSON"})
            continue
        cmd = msg.get("cmd")
        if cmd == "stop":
            _emit({"type": "stopped"})
            break
        if cmd == "status":
            _emit(
                {
                    "type": "status",
                    "boundary_step": boundary_step,
                    "mode": mode,
                    "entrypoint": entrypoint_spec,
                }
            )
            continue
        if cmd == "step":
            boundary_step += 1
            out = run_step(
                log_path,
                entrypoint,
                mode=replay_mode,
                stop_after_boundaries=boundary_step,
                forced_entrypoint=forced,
                step_boundaries=step_boundaries,
            )
            _emit(out)
            if out.get("type") in ("divergence", "error"):
                if replay_mode == ReplayMode.STRICT:
                    continue
            continue
        _emit({"type": "error", "message": f"unknown cmd {cmd!r}"})


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="agentrr replay worker")
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--mode", default="strict", choices=("strict", "observe"))
    parser.add_argument("--entrypoint", default=None, help="override module:callable")
    parser.add_argument(
        "--step-boundaries",
        default="all",
        choices=("all", "story"),
        help="all: every shim/LLM/tool boundary; story: LLM + tool only (UI default)",
    )
    args = parser.parse_args()
    # Only pass explicit CLI override; header resolution (incl. __main__ fixup) is in resolve_entrypoint_for_replay.
    worker_loop(args.log, args.mode, args.entrypoint, step_boundaries=args.step_boundaries)


if __name__ == "__main__":
    main()

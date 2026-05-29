"""Record orchestration."""

from __future__ import annotations

import hashlib
import inspect
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import RunHeader
from agentrr_core.version import __version__
from agentrr_recorder.recorder import Recorder

from agentrr_sdk import runtime
from agentrr_sdk.entrypoint import format_entrypoint
from agentrr_sdk.init import shutdown_replay


def default_log_dir() -> Path:
    base = os.environ.get("AGENTRR_LOG_DIR", ".agentrr/runs")
    return Path(base)


def code_fingerprint(entrypoint: Callable[..., Any]) -> str:
    path = inspect.getfile(entrypoint)
    with open(path, "rb") as f:
        return f"sha256:{hashlib.sha256(f.read()).hexdigest()}"


def record(
    run_name: str,
    entrypoint: Callable[..., Any],
    *args: Any,
    log_path: Path | None = None,
    initial_input: dict[str, Any] | None = None,
    **kwargs: Any,
) -> tuple[Any, Path]:
    run_id = f"{run_name}-{uuid.uuid4().hex[:12]}"
    path = log_path or (default_log_dir() / f"{run_id}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)

    header = RunHeader(
        run_id=run_id,
        sdk_version=__version__,
        agent_code_fingerprint=code_fingerprint(entrypoint),
        entrypoint=format_entrypoint(entrypoint),
        initial_input=initial_input,
        clock_origin={"wall": None},
        rng_seed_origin={},
    )
    fsync = os.environ.get("AGENTRR_FSYNC", "1") != "0"
    writer = LogWriter(LogWriterConfig(path=path, fsync_every_event=fsync))
    recorder = Recorder.create(writer, header)
    ctx = recorder.begin_run()
    runtime.set_recorder(recorder, ctx)
    runtime.set_mode("record")
    try:
        result = entrypoint(*args, **kwargs)
        recorder.emit_run_end("ok")
        return result, path
    except Exception:
        recorder.emit_run_end("error")
        raise
    finally:
        runtime.set_mode("off")
        runtime.set_recorder(None, None)
        shutdown_replay()

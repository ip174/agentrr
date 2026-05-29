"""Read runs from AGENTRR_LOG_DIR."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agentrr_core.log.reader import LogReader
from agentrr_core.log.run_index import load_run_index
from agentrr_core.schema.events import EventType
from agentrr_sdk.record import default_log_dir


@dataclass
class RunSummary:
    run_id: str
    path: str
    mtime: float
    truncated: bool
    event_count: int
    entrypoint: str | None


def log_dir() -> Path:
    return Path(os.environ.get("AGENTRR_LOG_DIR", str(default_log_dir())))


def list_runs(*, limit: int = 100) -> list[RunSummary]:
    base = log_dir()
    if not base.is_dir():
        return []
    indexed = load_run_index(base)
    if indexed:
        out: list[RunSummary] = []
        for row in indexed[:limit]:
            path = Path(row["path"])
            if not path.is_file():
                continue
            out.append(
                RunSummary(
                    run_id=row["run_id"],
                    path=str(path),
                    mtime=float(row.get("mtime", path.stat().st_mtime)),
                    truncated=bool(row.get("truncated", False)),
                    event_count=int(row.get("event_count", 0)),
                    entrypoint=row.get("entrypoint"),
                )
            )
        if out:
            return out
    files = sorted(base.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for path in files[:limit]:
        try:
            reader = LogReader(path)
            truncated = not any(e.type == EventType.RUN_END for e in reader.events)
            out.append(
                RunSummary(
                    run_id=reader.header.run_id,
                    path=str(path),
                    mtime=path.stat().st_mtime,
                    truncated=truncated,
                    event_count=len(reader.events),
                    entrypoint=reader.header.entrypoint,
                )
            )
        except Exception:
            continue
    return out


def format_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()

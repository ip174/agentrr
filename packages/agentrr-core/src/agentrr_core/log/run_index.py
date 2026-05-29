"""Append-only run index at ``<log-dir-parent>/index.json`` (``.agentrr/index.json``)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def index_path_for_log(log_path: Path) -> Path:
    """``.agentrr/runs/foo.jsonl`` → ``.agentrr/index.json``."""
    if log_path.parent.name == "runs":
        return log_path.parent.parent / "index.json"
    return log_path.parent / "index.json"


def upsert_run_index(
    log_path: Path,
    *,
    run_id: str,
    entrypoint: str | None,
    truncated: bool,
    event_count: int,
) -> None:
    idx_path = index_path_for_log(log_path)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "run_id": run_id,
        "path": str(log_path.resolve()),
        "mtime": log_path.stat().st_mtime,
        "truncated": truncated,
        "event_count": event_count,
        "entrypoint": entrypoint,
    }
    runs: dict[str, dict[str, Any]] = {}
    if idx_path.is_file():
        try:
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            for row in data.get("runs", []):
                runs[row["run_id"]] = row
        except (json.JSONDecodeError, KeyError, TypeError):
            runs = {}
    runs[run_id] = entry
    ordered = sorted(runs.values(), key=lambda r: r["mtime"], reverse=True)
    payload = json.dumps({"runs": ordered}, indent=2) + "\n"
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())


def load_run_index(log_dir: Path) -> list[dict[str, Any]]:
    if log_dir.name == "runs":
        idx_path = log_dir.parent / "index.json"
    else:
        idx_path = log_dir / "index.json"
    if not idx_path.is_file():
        return []
    try:
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        return list(data.get("runs", []))
    except (json.JSONDecodeError, KeyError, TypeError):
        return []

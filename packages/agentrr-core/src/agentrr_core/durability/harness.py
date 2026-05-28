"""Test helpers for durability gate."""

from __future__ import annotations

from pathlib import Path


def ready_marker_path(run_id: str, base: Path) -> Path:
    return base / f"{run_id}.ready"

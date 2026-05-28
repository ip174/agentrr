"""Write-before-return contract API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentrr_core.log.writer_minimal import DurabilityWriter


def persist_before_return(payload: dict[str, Any], path: Path, *, fsync: bool = True) -> str:
    """
    Write one NDJSON event line. MUST NOT return until durable on disk (when fsync=True).
    Returns the line written (for tests).
    """
    line = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    DurabilityWriter(path, fsync=fsync).append_line(line)
    return line

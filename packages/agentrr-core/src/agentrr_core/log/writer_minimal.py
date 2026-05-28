"""Minimal durable append — Step 1 gate; used by LogWriter."""

from __future__ import annotations

import os
from pathlib import Path


class DurabilityWriter:
    """Append one line with flush + fsync before return."""

    def __init__(self, path: Path, *, fsync: bool = True) -> None:
        self._path = path
        self._fsync = fsync
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append_line(self, line: str) -> None:
        data = line if line.endswith("\n") else line + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            if self._fsync:
                os.fsync(f.fileno())


class BufferedWriterNoFsync:
    """Intentionally broken writer for negative gate tests."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append_line(self, line: str) -> None:
        data = line if line.endswith("\n") else line + "\n"
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(data)
            f.flush()

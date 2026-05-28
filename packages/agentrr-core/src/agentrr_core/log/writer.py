"""Full log writer extending DurabilityWriter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from agentrr_core.log.writer_minimal import DurabilityWriter
from agentrr_core.schema.events import Event, RunHeader


@dataclass
class LogWriterConfig:
    path: Path
    fsync_every_event: bool = True


class LogWriter:
    def __init__(self, config: LogWriterConfig) -> None:
        self._config = config
        self._durability = DurabilityWriter(config.path, fsync=config.fsync_every_event)
        self._offsets: list[tuple[int, int]] = []

    @property
    def path(self) -> Path:
        return self._config.path

    def append_header(self, header: RunHeader) -> None:
        line = header.model_dump_json()
        self._append_raw(line, seq=-1)

    def append_event(self, event: Event) -> None:
        line = event.model_dump_json()
        self._append_raw(line, seq=event.seq)

    def _append_raw(self, line: str, seq: int) -> None:
        if self._config.path.exists():
            offset = self._config.path.stat().st_size
        else:
            offset = 0
        self._durability.append_line(line)
        if seq >= 0:
            self._offsets.append((seq, offset))

    def offsets(self) -> list[tuple[int, int]]:
        return list(self._offsets)

    def finalize_index(self) -> Path:
        idx_path = self._config.path.with_suffix(self._config.path.suffix + ".idx")
        with open(idx_path, "w", encoding="utf-8") as f:
            for seq, off in self._offsets:
                f.write(f"{seq}\t{off}\n")
            f.flush()
            os.fsync(f.fileno())
        return idx_path

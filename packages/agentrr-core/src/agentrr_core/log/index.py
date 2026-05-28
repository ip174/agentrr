"""seq -> byte offset index."""

from __future__ import annotations

from pathlib import Path


class SeqIndex:
    def __init__(self) -> None:
        self._map: dict[int, int] = {}

    @classmethod
    def load(cls, path: Path) -> SeqIndex:
        idx = cls()
        if not path.is_file():
            return idx
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2:
                    idx._map[int(parts[0])] = int(parts[1])
        return idx

    def get(self, seq: int) -> int | None:
        return self._map.get(seq)

    def __len__(self) -> int:
        return len(self._map)

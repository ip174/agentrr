"""NDJSON log reader."""

from __future__ import annotations

import json
from pathlib import Path

from agentrr_core.errors import CorruptEventError, UnsupportedLogVersionError
from agentrr_core.integrity import verify_integrity
from agentrr_core.log.index import SeqIndex
from agentrr_core.schema.events import Event, RunHeader

SUPPORTED_LOG_FORMAT = "1.0"


class LogReader:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._header: RunHeader | None = None
        self._events: list[Event] = []
        self._index = SeqIndex.load(path.with_suffix(path.suffix + ".idx"))
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def header(self) -> RunHeader:
        if self._header is None:
            raise CorruptEventError(-1, "missing header")
        return self._header

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    @property
    def truncated(self) -> bool:
        return not any(e.type.value == "run_end" for e in self._events)

    def get_event(self, seq: int) -> Event | None:
        for e in self._events:
            if e.seq == seq:
                return e
        return None

    def _load(self) -> None:
        if not self._path.is_file():
            raise FileNotFoundError(self._path)
        with open(self._path, encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        if not lines:
            raise CorruptEventError(-1, "empty log")
        first = json.loads(lines[0])
        if first.get("kind") == "header":
            major = str(first.get("log_format_version", "")).split(".")[0]
            if major != SUPPORTED_LOG_FORMAT.split(".")[0]:
                raise UnsupportedLogVersionError(
                    first.get("log_format_version", "?"),
                    SUPPORTED_LOG_FORMAT,
                )
            self._header = RunHeader.model_validate(first)
            raw_events = lines[1:]
        else:
            raw_events = lines
        last_valid = -1
        for line in raw_events:
            try:
                data = json.loads(line)
                ev = Event.model_validate(data)
                if ev.integrity and not verify_integrity(
                    ev.integrity,
                    ev.request,
                    ev.response,
                    ev.error.model_dump() if ev.error else None,
                ):
                    raise CorruptEventError(ev.seq, "integrity mismatch")
                self._events.append(ev)
                last_valid = ev.seq
            except json.JSONDecodeError as exc:
                raise CorruptEventError(last_valid + 1, str(exc)) from exc
        self._events.sort(key=lambda e: e.seq)

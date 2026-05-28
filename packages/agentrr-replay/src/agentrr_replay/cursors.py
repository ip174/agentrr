"""Per-type event cursors."""

from __future__ import annotations

from agentrr_core.schema.events import Event, EventType


class TypeCursors:
    """Track next expected event index per type in global seq order."""

    def __init__(self, events: list[Event]) -> None:
        self._events = sorted(events, key=lambda e: e.seq)
        self._by_type: dict[EventType, list[Event]] = {}
        for e in self._events:
            if e.type in (EventType.RUN_START, EventType.RUN_END):
                continue
            self._by_type.setdefault(e.type, []).append(e)
        self._indices: dict[EventType, int] = {t: 0 for t in self._by_type}

    def next_expected(self, event_type: EventType) -> Event | None:
        bucket = self._by_type.get(event_type, [])
        idx = self._indices.get(event_type, 0)
        if idx >= len(bucket):
            return None
        return bucket[idx]

    def advance(self, event_type: EventType) -> None:
        self._indices[event_type] = self._indices.get(event_type, 0) + 1

    @property
    def global_cursor(self) -> int:
        if not self._events:
            return -1
        return min(
            (self._indices.get(t, 0) for t in self._by_type),
            default=0,
        )

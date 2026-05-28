"""Breakpoint predicates."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agentrr_core.schema.events import Event, EventType


@dataclass
class Breakpoint:
    event_type: EventType | None = None
    tool_name: str | None = None
    prompt_regex: str | None = None
    _compiled: re.Pattern[str] | None = None

    def __post_init__(self) -> None:
        if self.prompt_regex:
            self._compiled = re.compile(self.prompt_regex)

    def matches(self, event: Event) -> bool:
        if self.event_type and event.type != self.event_type:
            return False
        if self.tool_name and event.request.get("name") != self.tool_name:
            return False
        if self._compiled:
            blob = str(event.request)
            if not self._compiled.search(blob):
                return False
        return True

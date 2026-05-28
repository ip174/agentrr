"""Two-phase boundary recording."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentrr_core.schema.events import EventType


@dataclass
class PendingBoundary:
    event_id: str
    event_type: EventType
    request: dict[str, Any]
    parent_id: str | None
    span_id: str | None = None

"""Step-at-boundary controller for replay worker."""

from __future__ import annotations

from agentrr_core.errors import PauseAtBoundary
from agentrr_core.schema.events import Event, EventType

REPLAY_BOUNDARY_TYPES = frozenset(
    {
        EventType.LLM_CALL,
        EventType.TOOL_CALL,
        EventType.CLOCK_READ,
        EventType.RNG_DRAW,
        EventType.ID_GEN,
    }
)

# UI stepping: one Next click = one narrative beat (AI call or tool use).
STORY_BOUNDARY_TYPES = frozenset(
    {
        EventType.LLM_CALL,
        EventType.TOOL_CALL,
    }
)


class StepBoundaryController:
    """Pause replay after N boundary crossings (1-based N)."""

    def __init__(
        self,
        stop_after_boundaries: int,
        *,
        boundary_types: frozenset[EventType] | None = None,
    ) -> None:
        self._stop_after = stop_after_boundaries
        self._served = 0
        self._boundary_types = boundary_types or REPLAY_BOUNDARY_TYPES

    def __call__(self, event: Event) -> None:
        if event.type not in self._boundary_types:
            return
        self._served += 1
        if self._served >= self._stop_after:
            raise PauseAtBoundary(
                event.seq,
                event.type.value,
                event.request,
                event.response,
            )

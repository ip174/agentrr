"""Span stack for parent_id / span_id nesting."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class SpanStack:
    _stack: list[str] = field(default_factory=list)

    def current_parent_id(self) -> str | None:
        return self._stack[-1] if self._stack else None

    @contextmanager
    def span(self, span_id: str | None = None) -> Generator[str, None, None]:
        sid = span_id or f"span-{uuid.uuid4().hex[:12]}"
        self._stack.append(sid)
        try:
            yield sid
        finally:
            self._stack.pop()

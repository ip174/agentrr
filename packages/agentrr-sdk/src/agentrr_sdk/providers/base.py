"""
Minimal interface extracted after OpenAI + Anthropic wrappers share the same flow.

Both implement: wrap client -> intercept create -> record request/response -> replay serve.
"""

from __future__ import annotations

from typing import Any, Protocol


class ProviderWrapper(Protocol):
    def wrap(self, client: Any) -> Any: ...

"""Tool registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from agentrr_sdk.tools.wrapper import wrap_tool

F = TypeVar("F", bound=Callable[..., object])

_REGISTRY: dict[str, Callable[..., object]] = {}


def tool(fn: F) -> F:
    wrapped = wrap_tool(fn)
    _REGISTRY[fn.__name__] = wrapped
    return wrapped  # type: ignore[return-value]


def register_tool(fn: F) -> F:
    return tool(fn)

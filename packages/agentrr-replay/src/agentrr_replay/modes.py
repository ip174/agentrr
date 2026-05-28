"""Strict vs observe replay modes."""

from __future__ import annotations

from enum import StrEnum


class ReplayMode(StrEnum):
    STRICT = "strict"
    OBSERVE = "observe"

"""Validate log file integrity and schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentrr_core.errors import AgentRrError
from agentrr_core.log.reader import LogReader


@dataclass
class ValidationResult:
    ok: bool
    last_valid_seq: int
    errors: list[str]
    truncated: bool


def validate_log(path: Path) -> ValidationResult:
    errors: list[str] = []
    try:
        reader = LogReader(path)
        last = reader.events[-1].seq if reader.events else -1
        return ValidationResult(
            ok=True,
            last_valid_seq=last,
            errors=[],
            truncated=reader.truncated,
        )
    except AgentRrError as exc:
        errors.append(str(exc))
        seq = getattr(exc, "seq", -1)
        return ValidationResult(ok=False, last_valid_seq=seq, errors=errors, truncated=True)

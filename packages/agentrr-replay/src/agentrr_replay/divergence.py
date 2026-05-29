"""Divergence reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentrr_core.schema.events import EventType

DIVERGENCE_FORMAT_VERSION = "1.0"


@dataclass
class DivergenceRecord:
    seq: int
    event_type: EventType
    expected_sig: str
    observed_sig: str
    diff: dict[str, Any]
    message: str


@dataclass
class DivergenceReport:
    divergence_format_version: str = DIVERGENCE_FORMAT_VERSION
    run_id: str = ""
    halted: bool = True
    divergences: list[DivergenceRecord] = field(default_factory=list)
    fingerprint_mismatch: bool = False
    forced_entrypoint: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "divergence_format_version": self.divergence_format_version,
            "run_id": self.run_id,
            "halted": self.halted,
            "fingerprint_mismatch": self.fingerprint_mismatch,
            "forced_entrypoint": self.forced_entrypoint,
            "divergences": [
                {
                    "seq": d.seq,
                    "type": d.event_type.value,
                    "expected_sig": d.expected_sig,
                    "observed_sig": d.observed_sig,
                    "diff": d.diff,
                    "message": d.message,
                }
                for d in self.divergences
            ],
        }

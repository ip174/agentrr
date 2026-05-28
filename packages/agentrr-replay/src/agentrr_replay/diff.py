"""Structural diff for divergence reports."""

from __future__ import annotations

import json
from typing import Any


def structural_diff(expected: Any, observed: Any) -> dict[str, Any]:
    exp = json.dumps(expected, sort_keys=True, default=str)
    obs = json.dumps(observed, sort_keys=True, default=str)
    return {
        "expected_preview": exp[:500],
        "observed_preview": obs[:500],
        "equal": exp == obs,
    }

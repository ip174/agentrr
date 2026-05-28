"""Per-event integrity hashes."""

from __future__ import annotations

import hashlib
from typing import Any

from agentrr_core.canonicalize import canonical_json


def compute_integrity(request: Any, response: Any, error: Any) -> str:
    payload = {"request": request, "response": response, "error": error}
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    return f"sha256:{digest}"


def verify_integrity(
    integrity: str,
    request: Any,
    response: Any,
    error: Any,
) -> bool:
    expected = compute_integrity(request, response, error)
    return integrity == expected

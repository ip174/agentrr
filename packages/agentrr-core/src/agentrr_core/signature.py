"""Request signature for divergence validation."""

from __future__ import annotations

import hashlib
from typing import Any

from agentrr_core.canonicalize import canonical_json


def request_signature(request: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(request)).hexdigest()
    return f"sha256:{digest}"

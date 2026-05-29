"""Pytest path setup."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
for p in (
    ROOT / "packages" / "agentrr-core" / "src",
    ROOT / "packages" / "agentrr-recorder" / "src",
    ROOT / "packages" / "agentrr-sdk" / "src",
    ROOT / "packages" / "agentrr-replay" / "src",
    ROOT / "packages" / "agentrr-cli" / "src",
    ROOT / "packages" / "agentrr-ui" / "src",
    EXAMPLES,
):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

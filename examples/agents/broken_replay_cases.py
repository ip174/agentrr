"""Negative test scenarios (documented)."""

from __future__ import annotations

# Scenarios exercised in tests/test_broken_replay.py:
# - edited prompt (signature mismatch)
# - missing tool registration
# - truncated log
# - corrupt integrity hash

SCENARIOS = [
    "edited_prompt",
    "missing_tool_registration",
    "truncated_log",
    "corrupt_hash",
]

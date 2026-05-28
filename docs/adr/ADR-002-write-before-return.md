# ADR-002: Write-before-return

## Status

Accepted — verified Step 1, permanent CI gate.

## Decision

Every boundary event is `flush` + `fsync` before returning to agent code.

## Verification

`tests/durability/test_write_before_return_sigkill.py` — child SIGKILL after persist; parent asserts response line parseable.

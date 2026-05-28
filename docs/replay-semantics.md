# Replay semantics

## Strict vs observe

- **strict** (default): halt on signature mismatch.
- **observe**: serve by sequence position, record divergences in report.

## Step back

Not reverse execution. **Re-run-to-seq**: restart agent from beginning, serve boundaries until target `seq` (O(N)).

## Routing nondeterminism

Use `agentrr_sdk.shims` for clock/RNG/ID. Unwrapped `random` / `time` will diverge on replay (detected, not silent).

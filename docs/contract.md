# Correctness contract

## Guarantees

- Faithful replay for the **instrumented boundary set** (LLM, registered tools, clock/RNG/ID shims).
- **First-mismatch** divergence detection (strict mode).
- **Side-effect-free** replay for wrapped LLM and tools.
- Per-event integrity hashes; corruption halts load.

## Not guaranteed

- Universal determinism for arbitrary third-party code.
- Concurrency / completion-order races.
- Streaming chunk fidelity (MVP replays final LLM output only).
- Fuzzy log matching (forbidden).

## Failure behavior

When faithfulness cannot be guaranteed: **halt and report** at the exact point.

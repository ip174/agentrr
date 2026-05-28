# Performance notes (MVP)

Baseline on laptop-class hardware (reference):

- 10k small event append: target &lt;2s with fsync per event.
- Replay 50-boundary run: target &lt;2× record time.

Run benchmarks: `uv run pytest tests --benchmark-only` (when benchmark tests added).

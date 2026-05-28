# Architecture

## Components

| Component | Location | Role |
|-----------|----------|------|
| Interceptor SDK | `agentrr-sdk` | Wrap LLM, tools, clock/RNG/ID |
| Recorder | `agentrr-recorder` | Gap-free `seq`, write-before-return |
| Log Writer | `agentrr-core` | NDJSON + fsync |
| Replay Engine | `agentrr-replay` | Determinism engine, divergence |
| CLI | `agentrr_cli` (in `agentrr` distribution) | `record`, `replay`, `inspect`, `validate` |

PyPI ships one package: **`agentrr`** (wheel/sdist bundle all `packages/agentrr-*/src` trees).

## Invariant #1: Write-before-return

Boundary events are flushed and `fsync`'d before the interceptor returns to agent code. Verified in CI via real `SIGKILL` (`tests/durability/`).

## State

Agent state is **reconstructed** by re-running code against frozen boundary values — not snapshotted.

## Record flow

```
Agent → SDK interceptor → Recorder → LogWriter (fsync) → file
                ↓
           live provider/tool (record only)
```

## Replay flow

```
CLI → ReplayRunner → DeterminismEngine → SDK serve path (no external I/O)
```

# Replay worker protocol (v1)

Process: `python -m agentrr_ui.worker --log PATH [--mode strict|observe] [--entrypoint module:callable] [--step-boundaries all|story]`

`--step-boundaries story` (default for `agentrr-ui` sessions): pause only on `llm_call` and `tool_call`, matching the “What happened” timeline. `all` includes clock/rng/id shims.

Newline-delimited JSON on stdin/stdout.

## Commands (stdin)

```json
{"cmd": "step"}
{"cmd": "status"}
{"cmd": "stop"}
```

## Responses (stdout)

**boundary** — paused after serving N boundaries (N = number of step commands so far):

```json
{"type": "boundary", "seq": 5, "event_type": "llm_call", "request": {}, "response": {}, "report": {}}
```

**divergence** — strict mode signature mismatch:

```json
{"type": "divergence", "message": "...", "report": {"divergences": [...], "forced_entrypoint": false}}
```

**complete** — entrypoint returned without further boundaries:

```json
{"type": "complete", "result": "ok", "report": {}}
```

**error** / **stopped** / **status**

Each `step` re-runs the agent from the beginning until the next boundary index (O(N) per step).

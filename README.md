# agentrr

**Deterministic record-and-replay debugger for AI agent runs.**

When an AI agent does something wrong in production, you usually can't reproduce it. Run it again and it takes a different path — the model samples differently, the tool returns different data, and the bug you saw is gone.

agentrr records every nondeterministic boundary an agent crosses — every LLM call, tool call, clock read, and random draw — then replays the run **deterministically and offline**. The agent's real logic runs again; every external answer is served from the recording. No API calls, no side effects, no cost. You step through the exact failing run as many times as you need.

It's `rr` / time-travel debugging, for AI agents.

## Install (PyPI)

Alpha releases on [PyPI](https://pypi.org/):

```bash
pip install agentrr
agentrr version
```

Optional local web UI:

```bash
pip install agentrr-ui
agentrr-ui   # http://127.0.0.1:8765 — see docs/ui.md
```

## Quick start (from source)

```bash
git clone https://github.com/ip174/agentrr.git
cd agentrr
uv sync --group dev
export PYTHONPATH=examples
```

### 1. Record a run

Use `python -m …` so the log stores a stable entrypoint for replay:

```bash
uv run python -m agents.deterministic_support
# run_id: deterministic_support-<id>
# log: .agentrr/runs/deterministic_support-<id>.jsonl
```

### 2. Replay in the CLI

```bash
uv run agentrr replay deterministic_support-<id>
```

Entrypoint is read from the log header (`0.1.0a2+`); override only when needed.

Edit the agent and replay again — strict mode stops at the first divergence:

```
DivergenceError: divergence at seq 5: signature mismatch
```

### 3. Inspect in the web UI (optional)

```bash
# dev checkout: install UI + built frontend
cd packages/agentrr-ui/frontend && npm ci && npm run build
cd ../../..
uv pip install -e . -e packages/agentrr-ui

export PYTHONPATH=examples
export AGENTRR_LOG_DIR=.agentrr/runs   # optional; this is the default
agentrr-ui
```

Open http://127.0.0.1:8765 — pick a session, read **What happened**, then **Check replay** and **Next** to step through AI/tool steps. **Replay matched** means today's run followed the same path as the recording.

See [docs/ui.md](docs/ui.md) for security, nginx, and troubleshooting.

## What it guarantees

- **Faithful replay** for every captured boundary — the replayed boundary sequence exactly matches the recording (verified in CI).
- **Offline and safe** — replay makes zero live LLM calls and never re-executes tools. Replaying an agent that issued a refund does not issue another.
- **Crash-safe recording** — an event is durably on disk (`fsync`) before the agent acts on it. Verified with real `SIGKILL` in CI. A killed run produces a *truncated* log, never a *holed* one.
- **Honest divergence** — when replay can't reproduce faithfully, it **halts at the exact point and tells you**, with a diff. It never silently guesses or serves a mismatched response.

## What it does NOT do (by design)

Single-process, synchronous agents. No marketplace, no backend, no hosted service. Concurrency, streaming-chunk replay, and multi-agent pipelines are out of scope for v0.1. See [docs/contract.md](docs/contract.md).

## How it works

| Layer | Recorded | Served on replay |
|-------|----------|------------------|
| LLM calls (OpenAI, Anthropic) | full request + response + metadata | recorded response |
| Tool calls | name, args, return/error | recorded result (tool never runs) |
| Clock / RNG / IDs | every read and draw | recorded values, in order |

Matching is **sequence-primary, signature-validated** — no fuzzy search. A request that doesn't match the next expected event is divergence.

## Development

```bash
uv sync --group dev
export PYTHONPATH=examples
make test          # full suite (excludes durability subdir by default in Makefile)
make durability    # SIGKILL write-before-return gate
make ui-build      # compile React → agentrr_ui/static/
make lint
gitleaks detect    # before you push
```

### Reference agents

| Agent | Purpose |
|-------|---------|
| `examples/agents/deterministic_support.py` | Golden path (mock LLM, registered tools, shims) |
| `examples/agents/unstable_loop.py` | Unwrapped `random` — diverges on replay (by design) |
| `examples/agents/tool_caller.py` | LLM → tool → LLM loop |
| `examples/agents/broken_replay_cases.py` | Negative scenarios |

### Docs

| Doc | Topic |
|-----|--------|
| [docs/ui.md](docs/ui.md) | Web UI install and run |
| [docs/RELEASING.md](docs/RELEASING.md) | PyPI release checklist |
| [docs/contract.md](docs/contract.md) | Guarantees and exclusions |
| [docs/replay-worker-protocol.md](docs/replay-worker-protocol.md) | UI worker IPC |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor workflow |

## License

Apache-2.0 — see [LICENSE](LICENSE).

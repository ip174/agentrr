# agentrr

**Deterministic record-and-replay debugger for AI agent runs.**

When an AI agent does something wrong in production, you usually can't reproduce it. Run it again and it takes a different path — the model samples differently, the tool returns different data, and the bug you saw is gone.

agentrr records every nondeterministic boundary an agent crosses — every LLM call, tool call, clock read, and random draw — then replays the run **deterministically and offline**. The agent's real logic runs again; every external answer is served from the recording. No API calls, no side effects, no cost. You step through the exact failing run as many times as you need.

It's `rr` / time-travel debugging, for AI agents.

## The 60-second demo

From a clone of this repo:

```bash
uv sync --group dev
export PYTHONPATH=examples
```

Record a run:

```bash
uv run python -m agents.deterministic_support
# run_id: deterministic_support-<id>
# log: .agentrr/runs/deterministic_support-<id>.jsonl
```

Replay it — deterministically, with no network and no live LLM calls (the demo agent uses a mock client; replay never calls it):

```bash
uv run agentrr replay deterministic_support-<id> agents.deterministic_support:main
```

Now edit the agent's prompt and replay again. agentrr halts at the **exact** boundary where behavior first diverges, with a signature mismatch and a structural diff in the divergence report:

```
DivergenceError: divergence at seq 5: signature mismatch
```

Strict mode halts on the first mismatch; use `mode="observe"` to continue and collect every divergence. The report includes structural diff previews (`expected_preview` / `observed_preview`), not the error string alone.

That's the core loop: turn a one-time, irreproducible failure into a fixed artifact you can re-enter and dissect.

## What it guarantees

- **Faithful replay** for every captured boundary — the replayed boundary sequence exactly matches the recording (verified in CI).
- **Offline and safe** — replay makes zero live LLM calls and never re-executes tools. Replaying an agent that issued a refund does not issue another.
- **Crash-safe recording** — an event is durably on disk (`fsync`) before the agent acts on it. Verified with real `SIGKILL` in CI. A killed run produces a *truncated* log, never a *holed* one.
- **Honest divergence** — when replay can't reproduce faithfully, it **halts at the exact point and tells you**, with a diff. It never silently guesses or serves a mismatched response.

## What it does NOT do (by design)

Single-process, synchronous agents. No marketplace, no backend, no GUI. Concurrency, streaming-chunk replay, and multi-agent pipelines are out of scope for v0.1. See [docs/contract.md](docs/contract.md) for the full contract and exclusions.

## How it works

agentrr intercepts at the boundaries where an agent touches nondeterminism, and freezes them on replay:

| Layer | Recorded | Served on replay |
|-------|----------|------------------|
| LLM calls (OpenAI, Anthropic) | full request + response + metadata | recorded response |
| Tool calls | name, args, return/error | recorded result (tool never runs) |
| Clock / RNG / IDs | every read and draw | recorded values, in order |

Matching is **sequence-primary, signature-validated** — no fuzzy search, ever. A request that doesn't match the next expected event is divergence, not a thing to paper over.

## Install

From source (PyPI publish pending):

```bash
git clone https://github.com/<OWNER>/agentrr.git
cd agentrr
uv sync --group dev
export PYTHONPATH=examples   # for example agents
```

## Development

```bash
uv sync --group dev
make test          # full suite incl. credibility gates
make durability    # SIGKILL write-before-return gate
gitleaks detect    # secret scan before you push
```

### Reference agents

| Agent | Purpose |
|-------|---------|
| `examples/agents/deterministic_support.py` | Golden path (mock LLM, registered tools, shims) |
| `examples/agents/unstable_loop.py` | Unwrapped `random` — diverges on replay (by design) |
| `examples/agents/tool_caller.py` | LLM → tool → LLM loop |
| `examples/agents/broken_replay_cases.py` | Negative scenarios (edited prompt, missing tool, truncated/corrupt log) |

## License

Apache-2.0 — see [LICENSE](LICENSE).

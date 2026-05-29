# agentrr-ui

Local web UI for [agentrr](https://pypi.org/project/agentrr/) — list saved agent runs, read a plain-language timeline, and step through replay to see if behavior still matches the recording.

**Requires:** Python 3.11+, [`agentrr>=0.1.0a2`](https://pypi.org/project/agentrr/) (installed automatically).

## What it does

1. **Lists sessions** — every recorded agent run in your log directory.
2. **Shows what happened** — a short story (Started → Asked AI → Used tool → Finished), not raw JSON.
3. **Check replay** — re-runs your agent step-by-step and compares it to the saved recording.
4. **Shows differences** — if something changed, highlights the step and shows saved vs replay side-by-side.

## Install

```bash
pip install agentrr-ui
```

This pulls in `agentrr`, FastAPI, and uvicorn. No Node.js required for end users — the frontend is bundled in the wheel.

## Quick start (record → open UI)

### 1. Record an agent run

In your project, instrument with agentrr and record using a **module entrypoint** (so replay can import your code):

```bash
pip install agentrr
export PYTHONPATH=src   # or wherever your agents package lives
python -m your_app.agents.support   # example
# writes: .agentrr/runs/your_app-<id>.jsonl
```

Use `python -m package.module`, not a bare script path (`python foo.py`), so the log stores a stable entrypoint.

### 2. Start the UI

```bash
export PYTHONPATH=src                 # same path as when you recorded
export AGENTRR_LOG_DIR=.agentrr/runs  # optional; this is the default
agentrr-ui
```

Open **http://127.0.0.1:8765**

### 3. Inspect and replay

1. Click a session on the home page.
2. Read **What happened** (the timeline).
3. Click **Check replay**, then **Next** for each important step (AI calls and tool use).
4. **Replay matched** means today's run followed the same steps as the recording.

## Run options

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENTRR_LOG_DIR` | `.agentrr/runs` | Directory containing `*.jsonl` run logs |
| `AGENTRR_UI_HOST` | `127.0.0.1` | Bind address |
| `AGENTRR_UI_PORT` | `8765` | Bind port |

Example — custom log directory:

```bash
export AGENTRR_LOG_DIR=/var/lib/agentrr/runs
agentrr-ui
```

Always start the app with the **`agentrr-ui` command**. Do **not** serve the static files with `python -m http.server` — that has no `/api` routes and the UI will break.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty session list | Record a run first, or set `AGENTRR_LOG_DIR` to where your `.jsonl` files live |
| Refresh shows HTML 404 | Wrong process on port 8765. Run `lsof -i :8765`, stop any `http.server`, use `agentrr-ui` |
| Replay hangs or errors | Set `PYTHONPATH` so replay can import your agent module; re-record with `python -m …` |
| "Next" does nothing | Restart `agentrr-ui` after upgrading; each step can take several seconds |

## Security

Replay **executes your agent's real Python entrypoint** — arbitrary code execution by design.

- **Default:** bind to `127.0.0.1` only (localhost).
- **Never** expose port 8765 on a public network without TLS and authentication.
- For remote access, use nginx (below) or another reverse proxy with HTTPS + auth.

## nginx (TLS + basic auth)

Run `agentrr-ui` on the same host, bound to localhost. Put nginx in front for HTTPS and password protection:

```nginx
server {
    listen 443 ssl;
    server_name agentrr.example.com;

    ssl_certificate     /etc/ssl/certs/agentrr.crt;
    ssl_certificate_key /etc/ssl/private/agentrr.key;

    auth_basic           "agentrr";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Create credentials:

```bash
htpasswd -c /etc/nginx/.htpasswd youruser
```

Reload nginx. Users hit `https://agentrr.example.com`; the app stays on `127.0.0.1:8765`.

## Development (from source)

```bash
git clone https://github.com/ip174/agentrr.git
cd agentrr
uv sync --group dev
cd packages/agentrr-ui/frontend && npm ci && npm run build
uv pip install -e . -e packages/agentrr-ui
export PYTHONPATH=examples
agentrr-ui
```

## More documentation

- [Full UI guide](https://github.com/ip174/agentrr/blob/main/docs/ui.md) — session page, architecture, dev workflow
- [agentrr README](https://github.com/ip174/agentrr#readme) — recording, CLI replay, guarantees
- [Replay worker protocol](https://github.com/ip174/agentrr/blob/main/docs/replay-worker-protocol.md) — IPC for stepping

## License

Apache-2.0

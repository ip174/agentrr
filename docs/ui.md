# agentrr-ui

Optional local web UI for listing recorded runs, inspecting `.jsonl` events, and stepping through replay with a visual divergence diff.

**Security:** Replay executes the agent's real Python entrypoint (arbitrary code execution by design). Bind to `127.0.0.1` by default. For remote access, put nginx in front with TLS and authentication — never expose the UI publicly without auth.

## Install

```bash
pip install agentrr-ui
```

Requires `agentrr>=0.1.0a2` (log header `entrypoint` field).

## Run

```bash
# from a dev checkout — pick up local fixes
uv pip install -e . -e packages/agentrr-ui

export AGENTRR_LOG_DIR=.agentrr/runs   # optional; default matches agentrr
export PYTHONPATH=examples             # so replay can import your agents
agentrr-ui
```

Record agents with `python -m agents.your_agent` (not a bare script path) so playback can find the entrypoint.

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

Do **not** serve `static/` with `python -m http.server` — that has no `/api` routes and Refresh will show a 404 HTML error. Always use the `agentrr-ui` command (uvicorn + API + static together).

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Refresh shows HTML `Error code: 404` / `File not found` | Wrong server on port 8765. `lsof -i :8765`, stop `http.server`, run `agentrr-ui` |
| Empty runs list | Record a run first, or set `AGENTRR_LOG_DIR` to your `.agentrr/runs` path |
| Vite dev (`npm run dev`) | Run `agentrr-ui` on **8765** in another terminal; Vite proxies `/api` and `/ws` |

Environment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENTRR_LOG_DIR` | `.agentrr/runs` | Directory of `*.jsonl` run logs |
| `AGENTRR_UI_HOST` | `127.0.0.1` | Bind address |
| `AGENTRR_UI_PORT` | `8765` | Bind port |

## Development

```bash
cd packages/agentrr-ui/frontend
npm install && npm run build   # → packages/agentrr-ui/src/agentrr_ui/static/
uv pip install -e packages/agentrr-ui
agentrr-ui
```

## nginx (TLS + basic auth)

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

Generate credentials: `htpasswd -c /etc/nginx/.htpasswd youruser`

Run `agentrr-ui` on the same host, bound to localhost only.

## Using the session page

1. **Saved session** — recording on disk; nothing re-run yet.
2. **What happened** — timeline (Started → Asked AI → Used tool → Finished). Expand a row only for technical JSON.
3. **Check replay** — starts a replay session (strict mode, story steps only: AI + tool boundaries).
4. **Next** — one check per important step; rows show **Checking now** then **Matched**.
5. **Replay matched** — re-running the agent today followed the same steps as the recording.

## Architecture

- **No duplicated replay logic** — the UI spawns `agentrr-replay-worker` (subprocess) using the same engine as the CLI.
- **Entrypoint** comes from the run log header by default; overrides are explicit and flagged in the divergence report.
- **Stepping** — `POST /api/replay/{session_id}/step` (primary). WebSocket `/ws/replay/{session_id}` is also available for autoplay.

See [replay-worker-protocol.md](replay-worker-protocol.md) for the stdin/stdout JSON protocol (`--step-boundaries story` for UI sessions).

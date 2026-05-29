# agentrr-ui

Local web UI for [agentrr](https://pypi.org/project/agentrr/) — list saved agent runs, read a plain-language timeline, and step through replay to see if behavior still matches the recording.

```bash
pip install agentrr-ui
export PYTHONPATH=path/to/your/agents   # so replay can import entrypoints
agentrr-ui
```

Open http://127.0.0.1:8765

Full documentation: [docs/ui.md](https://github.com/ip174/agentrr/blob/main/docs/ui.md) in the main repository.

**Security:** replay runs your agent’s real Python entrypoint. Bind to localhost only unless you add TLS and authentication in front (see docs).

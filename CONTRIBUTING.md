# Contributing

## Setup

```bash
git clone https://github.com/ip174/agentrr.git
cd agentrr
uv sync --group dev
export PYTHONPATH=examples
```

## Checks before a PR

```bash
make test
make durability
make lint
gitleaks detect
```

If you changed the web UI:

```bash
make ui-build
```

## UI development

```bash
make ui-build
uv pip install -e . -e packages/agentrr-ui
export PYTHONPATH=examples AGENTRR_LOG_DIR=.agentrr/runs
agentrr-ui
```

Frontend dev server (proxies API to port 8765):

```bash
# terminal 1
agentrr-ui
# terminal 2
cd packages/agentrr-ui/frontend && npm run dev
```

## Design docs

See `docs/adr/` for architecture decisions.

## Releases

Maintainers: [docs/RELEASING.md](docs/RELEASING.md).

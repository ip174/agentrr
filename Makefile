.PHONY: sync test lint fmt durability ui-build ui record-agent replay-agent

sync:
	uv sync --group dev

test:
	uv run python -m pytest tests packages -v --ignore=tests/durability
	uv run python -m pytest tests/test_credibility_gates.py -v

durability:
	uv run python -m pytest tests/durability -v -m durability

lint:
	uv run ruff check packages tests examples
	uv run mypy packages/agentrr-core/src packages/agentrr-recorder/src packages/agentrr-replay/src

fmt:
	uv run ruff format packages tests examples

ui-build:
	cd packages/agentrr-ui/frontend && npm ci && npm run build

ui: ui-build
	uv run agentrr-ui

record-agent:
	uv run python -m agents.deterministic_support

replay-agent:
	@test -n "$(RUN)" || (echo "Usage: make replay-agent RUN=<run_id>"; exit 1)
	uv run agentrr replay $(RUN) agents.deterministic_support:main

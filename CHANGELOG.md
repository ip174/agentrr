# Changelog

## [0.1.0a3] - 2026-05-28

### Changed

- Expanded `agentrr-ui` PyPI README: install, quick start, troubleshooting, nginx, security.

## [0.1.0a2] - 2026-05-28

### Added

- `agentrr-ui` on PyPI: local web UI (`agentrr-ui`), replay worker (`agentrr-replay-worker`), REST step API.
- Log header `entrypoint` for reliable replay (including `python -m` module fixup).
- Story-based session view: saved timeline, step-through replay, divergence diff.

### Fixed

- UI replay stepping aligned with narrative beats (`--step-boundaries story`).
- Release workflow publishes both `agentrr` and `agentrr-ui` wheels.

## [0.1.0a1] - 2026-05-28

### Added

- Single PyPI distribution `agentrr` bundling core, recorder, sdk, replay, and CLI.
- GitHub Actions release workflow with PyPI trusted publishing (OIDC).

## [0.1.0] - 2026-05-28

### Added

- Monorepo: core, recorder, sdk, replay, cli.
- Record/replay with OpenAI and Anthropic client wrappers.
- Strict divergence detection, NDJSON logs, SIGKILL durability gate.

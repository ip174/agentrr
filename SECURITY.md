# Security

## Reporting vulnerabilities

Please report security issues privately via [GitHub Security Advisories](https://github.com/ip174/agentrr/security/advisories/new) for this repository. Do not open public issues for exploitable vulnerabilities.

## agentrr-ui

The web UI runs your agent’s real Python entrypoint during replay. Treat it as **arbitrary code execution**:

- Bind to `127.0.0.1` (default).
- Do not expose port 8765 on a public network without TLS and authentication (see [docs/ui.md](docs/ui.md)).

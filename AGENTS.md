# Agent instructions

- **No fuzzy log matching** — sequence-primary, signature-validated only.
- **Write-before-return** — never return from a boundary before fsync completes.
- MVP excludes concurrency, multi-agent, GUI, cloud backend.

# Log format v1.0

- Line 0: header (`kind: header`, `log_format_version: "1.0"`, `run_id`, fingerprints).
- Lines 1..N: events with monotonic `seq`, `type`, `request`, `response`/`error`, `integrity`.

## Fsync policy

`AGENTRR_FSYNC=1` (default): fsync after each event. Set `0` only for local perf experiments.

## Index

Sidecar `*.jsonl.idx`: `seq<TAB>byte_offset` per line.

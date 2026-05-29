"""Entrypoint spec formatting and resolution for record/replay."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentrr_core.log.reader import LogReader


def _module_name_for_callable(entrypoint: Callable[..., Any]) -> str:
    mod = inspect.getmodule(entrypoint)
    if mod is None:
        raise ValueError("cannot resolve module for entrypoint callable")
    if mod.__name__ != "__main__":
        return mod.__name__
    # python -m package.module sets __name__ == "__main__" but __spec__.name is stable
    spec = getattr(mod, "__spec__", None)
    if spec is not None and spec.name and spec.name != "__main__":
        return spec.name
    raise ValueError(
        "cannot serialize entrypoint recorded as __main__; "
        "re-record using `python -m agents.your_agent` (module form) not a bare script path"
    )


def infer_entrypoint_from_run_id(run_id: str) -> str | None:
    """Best-effort fix for legacy logs stored as ``__main__:main`` (examples agents)."""
    import re

    m = re.match(r"^(.+)-[a-f0-9]{8,}$", run_id, re.IGNORECASE)
    if not m:
        return None
    stem = m.group(1)
    if "." in stem or "/" in stem:
        return None
    return f"agents.{stem}:main"


def format_entrypoint(entrypoint: Callable[..., Any]) -> str:
    name = entrypoint.__name__
    if name.startswith("<"):
        raise ValueError("cannot serialize lambda or nested entrypoint")
    return f"{_module_name_for_callable(entrypoint)}:{name}"


def import_entrypoint(spec: str) -> Callable[..., Any]:
    if ":" not in spec:
        raise ValueError(f"invalid entrypoint spec {spec!r}; expected module.path:callable")
    mod_name, _, fn_name = spec.partition(":")
    mod = importlib.import_module(mod_name)
    entry = getattr(mod, fn_name)
    if not callable(entry):
        raise TypeError(f"{spec!r} is not callable")
    return entry


def resolve_entrypoint_for_replay(
    log_path: Path,
    entrypoint: Callable[..., Any] | None = None,
    *,
    entrypoint_spec: str | None = None,
) -> tuple[Callable[..., Any], bool]:
    """Return (callable, forced_entrypoint). forced=True when replay diverges from logged entrypoint."""
    reader = LogReader(log_path)
    header_spec = reader.header.entrypoint

    if entrypoint_spec is not None:
        forced = header_spec is not None and entrypoint_spec != header_spec
        return import_entrypoint(entrypoint_spec), forced or header_spec is None

    if entrypoint is not None:
        used = format_entrypoint(entrypoint)
        if header_spec is None:
            return entrypoint, True
        return entrypoint, used != header_spec

    if header_spec:
        if header_spec == "__main__:main":
            inferred = infer_entrypoint_from_run_id(reader.header.run_id)
            if inferred:
                return import_entrypoint(inferred), True
            raise ValueError(
                "log entrypoint is __main__:main and cannot be replayed; "
                "re-record the run or pass entrypoint_spec=module.path:callable"
            )
        return import_entrypoint(header_spec), False

    raise ValueError(
        "no entrypoint in log header; pass entrypoint callable or module.path:callable"
    )

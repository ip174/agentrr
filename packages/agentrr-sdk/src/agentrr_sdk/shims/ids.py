"""Sequenced ID generation."""

from __future__ import annotations

import uuid

from agentrr_core.schema.events import EventType
from agentrr_sdk import runtime
from agentrr_sdk.boundaries.local import emit_local_boundary


def uuid4() -> str:
    if runtime.get_mode() == "replay":
        engine = runtime.get_engine()
        if engine is None:
            raise RuntimeError("replay mode without determinism engine")
        served = engine.serve_local(
            EventType.ID_GEN,
            {"generator": "uuid4"},
        )
        return str(served["value"])
    value = str(uuid.uuid4())
    if runtime.get_mode() == "record":
        emit_local_boundary(
            EventType.ID_GEN,
            request={"generator": "uuid4"},
            response={"value": value},
        )
    return value

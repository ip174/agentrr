"""Sequenced RNG shim."""

from __future__ import annotations

import secrets

from agentrr_core.schema.events import EventType
from agentrr_sdk import runtime
from agentrr_sdk.boundaries.local import emit_local_boundary


class SequencedRNG:
    def random(self) -> float:
        req = {"method": "random", "args": []}
        if runtime.get_mode() == "replay":
            engine = runtime.get_engine()
            if engine is None:
                raise RuntimeError("replay mode without determinism engine")
            served = engine.serve_local(EventType.RNG_DRAW, req)
            return float(served["value"])
        value = secrets.randbelow(10**15) / 10**15
        if runtime.get_mode() == "record":
            emit_local_boundary(
                EventType.RNG_DRAW,
                request=req,
                response={"value": value},
            )
        return value


_rng = SequencedRNG()


def random() -> float:
    return _rng.random()

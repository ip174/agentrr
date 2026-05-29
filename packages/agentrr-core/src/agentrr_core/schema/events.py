"""Event and run header models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    RUN_START = "run_start"
    RUN_END = "run_end"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    CLOCK_READ = "clock_read"
    RNG_DRAW = "rng_draw"
    ID_GEN = "id_gen"
    STEP_MARKER = "step_marker"


class EventStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TRUNCATED = "truncated"


class ErrorPayload(BaseModel):
    type: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RunHeader(BaseModel):
    kind: str = "header"
    log_format_version: str = "1.0"
    run_id: str
    sdk_version: str = "0.1.0"
    agent_code_fingerprint: str | None = None
    entrypoint: str | None = None
    clock_origin: dict[str, Any] | None = None
    rng_seed_origin: dict[str, Any] | None = None
    initial_input: dict[str, Any] | None = None
    secrets_warning_ack: bool = False


class Event(BaseModel):
    event_id: str
    run_id: str
    seq: int
    type: EventType
    parent_id: str | None = None
    ts_logical: int
    ts_wall: str | None = None
    status: EventStatus
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] | None = None
    error: ErrorPayload | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    integrity: str = ""

    def with_integrity(self, hash_value: str) -> Event:
        return self.model_copy(update={"integrity": hash_value})

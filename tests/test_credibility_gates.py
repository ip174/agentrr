"""
Credibility gates — prove core guarantees, not just "todos completed".

Run: uv run pytest tests/test_credibility_gates.py -v -s
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from agentrr_core.errors import DivergenceError
from agentrr_core.log.reader import LogReader
from agentrr_core.schema.events import EventType
from agentrr_core.signature import request_signature
from agentrr_replay.engine import DeterminismEngine
from agentrr_replay.modes import ReplayMode
from agentrr_sdk import record, replay
from agentrr_sdk.providers.openai_client import wrap_openai_client
from agents import deterministic_support as ds
from agents.deterministic_support import main as deterministic_main
from openai.types.chat import ChatCompletion

# Boundaries re-issued during replay (step_marker is record-only).
REPLAY_BOUNDARY_TYPES = frozenset(
    {
        EventType.LLM_CALL,
        EventType.TOOL_CALL,
        EventType.CLOCK_READ,
        EventType.RNG_DRAW,
        EventType.ID_GEN,
    }
)


def _boundary_sequence(reader: LogReader) -> list[tuple[str, str]]:
    return [
        (e.type.value, e.meta.get("request_sig") or request_signature(e.request))
        for e in reader.events
        if e.type in REPLAY_BOUNDARY_TYPES
    ]


def _fake_completion(model: str, messages: list[dict[str, str]]) -> ChatCompletion:
    user = messages[-1]["content"]
    if "tool" in user.lower() or "order" in user.lower():
        return ChatCompletion.model_validate(
            {
                "id": "fake",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "done",
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_order",
                                        "arguments": '{"order_id": "123"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }
        )
    return ChatCompletion.model_validate(
        {
            "id": "fake",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Your order is shipped."},
                    "finish_reason": "stop",
                }
            ],
        }
    )


# --- Gate 1: fixed-point ---


def test_gate1_fixed_point_strict_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replay boundary attempts must equal recorded boundary sequence (type + signature)."""
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("gate1", deterministic_main)
    expected = _boundary_sequence(LogReader(log_path))

    attempts: list[tuple[str, str]] = []
    original_match = DeterminismEngine._match

    def tracking_match(
        self: DeterminismEngine,
        event_type: EventType,
        request: dict[str, Any],
    ) -> Any:
        attempts.append((event_type.value, request_signature(request)))
        return original_match(self, event_type, request)

    with patch.object(DeterminismEngine, "_match", tracking_match):
        replay(log_path, deterministic_main, mode="strict")

    assert attempts == expected, (
        f"fixed-point mismatch\n  recorded ({len(expected)}): {expected}\n  replay   ({len(attempts)}): {attempts}"
    )


# --- Gate 2: offline replay ---


def test_gate2_offline_replay_no_provider_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Multi-boundary replay must not call live provider create (freeze path only)."""
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    live_create_calls: list[int] = []

    class GuardCompletions:
        def create(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ChatCompletion:
            live_create_calls.append(1)
            return _fake_completion(model, messages)

    class GuardChat:
        completions = GuardCompletions()

    class GuardClient:
        chat = GuardChat()

    def guard_mock_client() -> Any:
        return wrap_openai_client(GuardClient())  # type: ignore[arg-type]

    monkeypatch.setattr(ds, "_mock_client", guard_mock_client)
    _, log_path = record("gate2", deterministic_main)

    live_create_calls.clear()
    replay(log_path, deterministic_main, mode="strict")

    assert live_create_calls == [], f"live provider create called {len(live_create_calls)} times during replay"


# --- Gate 3: tool side-effect counter ---


def test_gate3_tool_body_not_invoked_on_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    ds._TOOL_EXECUTIONS = 0
    _, log_path = record("gate3", deterministic_main)
    assert ds._TOOL_EXECUTIONS >= 1
    ds._TOOL_EXECUTIONS = 0
    replay(log_path, deterministic_main, mode="strict")
    assert ds._TOOL_EXECUTIONS == 0


# --- Gate 4: divergence halts with diff ---


def test_gate4_edited_prompt_halts_with_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTRR_LOG_DIR", str(tmp_path))
    _, log_path = record("gate4", deterministic_main)

    reader = LogReader(log_path)
    first_llm = next(e for e in reader.events if e.type == EventType.LLM_CALL)
    edited = {
        **first_llm.request,
        "messages": [{"role": "user", "content": "EDITED PROMPT — should diverge"}],
    }

    engine = DeterminismEngine.load(log_path, mode=ReplayMode.STRICT)
    with pytest.raises(DivergenceError) as exc_info:
        engine.serve_llm(edited)

    assert "divergence at seq" in str(exc_info.value)
    assert len(engine.report.divergences) == 1
    d0 = engine.report.divergences[0]
    assert d0.expected_sig != d0.observed_sig
    assert d0.diff.get("equal") is False
    assert "EDITED" in d0.diff.get("observed_preview", "")
    assert "expected_preview" in d0.diff

    # Full agent replay must also halt (headline workflow)
    def main_edited() -> str:
        from agentrr_sdk.shims import clock, ids, rng

        _ = clock.time()
        _ = rng.random()
        _ = ids.uuid4()
        client = ds._mock_client()
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "EDITED PROMPT — should diverge"}],
        )
        return "never"

    with pytest.raises(DivergenceError):
        replay(log_path, main_edited, mode="strict")


# --- Gate 5: SIGKILL on real Recorder path ---


@pytest.mark.durability
def test_gate5_sigkill_after_record_boundary(tmp_path: Path) -> None:
    """SIGKILL after record_boundary returns — tool event must survive on disk."""
    run_id = f"rec-gate-{uuid.uuid4().hex[:8]}"
    log_path = tmp_path / f"{run_id}.jsonl"
    ready = tmp_path / f"{run_id}.ready"

    root = Path(__file__).resolve().parents[1]
    child_code = f"""
import sys, time
sys.path[:0] = [
    {str(root / "packages" / "agentrr-core" / "src")!r},
    {str(root / "packages" / "agentrr-recorder" / "src")!r},
]
from pathlib import Path
from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import EventType, RunHeader
from agentrr_recorder.pending_event import PendingBoundary
from agentrr_recorder.recorder import Recorder

log = Path({str(log_path)!r})
ready = Path({str(ready)!r})
header = RunHeader(run_id={run_id!r})
writer = LogWriter(LogWriterConfig(path=log, fsync_every_event=True))
rec = Recorder.create(writer, header)
rec.begin_run()
pending = PendingBoundary(
    event_id="e-boundary",
    event_type=EventType.TOOL_CALL,
    request={{"name": "test_tool", "arguments": {{"x": 1}}}},
    parent_id=None,
)
rec.record_boundary(pending, response={{"value": {{"ok": True}}}})
ready.write_text("ready")
time.sleep(3600)
"""

    child = subprocess.Popen([sys.executable, "-c", child_code])
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if ready.is_file():
                break
            if child.poll() is not None:
                break
            time.sleep(0.02)
        assert ready.is_file(), "child died before record_boundary completed"
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()

    assert child.returncode != 0
    reader = LogReader(log_path)
    tool_events = [e for e in reader.events if e.type == EventType.TOOL_CALL]
    assert len(tool_events) == 1
    assert tool_events[0].response == {"value": {"ok": True}}
    seqs = sorted(e.seq for e in reader.events)
    assert 0 in seqs and 1 in seqs

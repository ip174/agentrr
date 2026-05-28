#!/usr/bin/env python3
"""
Throwaway POC: record one OpenAI chat completion to disk, replay without calling OpenAI.

stdlib + openai SDK only. Run: python poc_openai_record_replay.py
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from openai.types.chat import ChatCompletion

Mode = Literal["record", "replay"]


def _runs_dir() -> Path:
    return Path(tempfile.gettempdir()) / "agentrr_poc_runs"


def log_path_for_run(run_id: str) -> Path:
    return _runs_dir() / f"{run_id}.jsonl"


def _ready_marker_path(run_id: str) -> Path:
    return _runs_dir() / f"{run_id}.ready"


def _durable_append(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def wrapped_chat_completion(
    client: OpenAI | None,
    *,
    run_id: str,
    mode: Mode,
    model: str,
    messages: list[dict[str, str]],
    **kwargs: Any,
) -> ChatCompletion:
    """
    Record: request durable -> live API -> response durable -> return.
    Replay: read response from run file only; never call OpenAI.
    """
    path = log_path_for_run(run_id)
    request_payload = {"model": model, "messages": messages, **kwargs}

    if mode == "record":
        if client is None:
            raise ValueError("record mode requires an OpenAI client")
        _durable_append(
            path,
            {"kind": "request", "run_id": run_id, "payload": request_payload},
        )
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        _durable_append(
            path,
            {
                "kind": "response",
                "run_id": run_id,
                "payload": response.model_dump(mode="json"),
            },
        )
        if os.environ.get("POC_CRASH_AFTER_RESPONSE") == "1":
            os._exit(137)
        return response

    if mode == "replay":
        events = _read_events(path)
        responses = [e for e in events if e.get("kind") == "response"]
        if not responses:
            raise RuntimeError(
                f"replay failed: no recorded response in {path}. "
                "Will not call OpenAI."
            )
        if len(responses) > 1:
            raise RuntimeError(f"replay failed: expected one response, got {len(responses)}")
        return ChatCompletion.model_validate(responses[-1]["payload"])

    raise ValueError(f"unknown mode: {mode!r}")


def _response_text(completion: ChatCompletion) -> str:
    return completion.choices[0].message.content or ""


def _client_for_tests() -> tuple[OpenAI, str]:
    """Real OpenAI client if OPENAI_API_KEY is set; else minimal fake for local POC runs."""
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAI(), "live"

    class _FakeCompletions:
        def create(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ChatCompletion:
            user = next((m["content"] for m in messages if m["role"] == "user"), "")
            return ChatCompletion.model_validate(
                {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion",
                    "created": 0,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": user},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    return _FakeClient(), "fake"  # type: ignore[return-value]


# --- tests ---


def test_1_basic_round_trip() -> bool:
    client, source = _client_for_tests()
    if source == "fake":
        print("  (using fake client — set OPENAI_API_KEY for a live call)")

    run_id = f"test1-{uuid.uuid4()}"
    path = log_path_for_run(run_id)
    if path.exists():
        path.unlink()

    recorded = wrapped_chat_completion(
        client,
        run_id=run_id,
        mode="record",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Reply with exactly: POC_OK"}],
        max_tokens=16,
        temperature=0,
    )

    replayed = wrapped_chat_completion(
        None,
        run_id=run_id,
        mode="replay",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "ignored on replay"}],
    )

    ok = recorded.model_dump(mode="json") == replayed.model_dump(mode="json")
    print(f"TEST 1 — basic round trip: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(f"  recorded text: {_response_text(recorded)!r}")
        print(f"  replayed text: {_response_text(replayed)!r}")
    return ok


def test_2_crash_after_response() -> bool:
    _, source = _client_for_tests()
    if source == "fake":
        print("  (using fake client — set OPENAI_API_KEY for a live call)")

    run_id = f"test2-{uuid.uuid4()}"
    path = log_path_for_run(run_id)
    if path.exists():
        path.unlink()

    env = {**os.environ, "POC_CRASH_AFTER_RESPONSE": "1"}
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os, sys; "
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r}); "
                "from poc_openai_record_replay import wrapped_chat_completion, _client_for_tests; "
                "c, _ = _client_for_tests(); "
                "wrapped_chat_completion(c, "
                f"run_id={run_id!r}, mode='record', "
                "model='gpt-4o-mini', "
                "messages=[{'role':'user','content':'Reply: CRASH_OK'}], "
                "max_tokens=16, temperature=0)"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    crashed = proc.returncode != 0

    events = _read_events(path)
    responses = [e for e in events if e.get("kind") == "response"]
    requests = [e for e in events if e.get("kind") == "request"]

    ok = (
        crashed
        and len(requests) == 1
        and len(responses) == 1
        and "CRASH_OK" in json.dumps(responses[0])
    )
    print(f"TEST 2 — crash after response persisted: {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(f"  subprocess returncode: {proc.returncode}")
        print(f"  requests: {len(requests)}, responses: {len(responses)}")
        if proc.stderr:
            print(f"  stderr: {proc.stderr[:500]}")
    return ok


def test_4_real_sigkill_after_response() -> bool:
    """Record in a child, SIGKILL after response is on disk, verify in parent."""
    client, source = _client_for_tests()
    if source == "fake":
        print("  (using fake client — set OPENAI_API_KEY for a live call)")

    run_id = f"test4-{uuid.uuid4()}"
    path = log_path_for_run(run_id)
    ready = _ready_marker_path(run_id)
    for p in (path, ready):
        if p.exists():
            p.unlink()

    poc_dir = str(Path(__file__).resolve().parent)
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import sys, time; "
                f"sys.path.insert(0, {poc_dir!r}); "
                "from pathlib import Path; "
                "from poc_openai_record_replay import ("
                "  wrapped_chat_completion, _client_for_tests, _ready_marker_path, "
                "); "
                "c, _ = _client_for_tests(); "
                f"rid = {run_id!r}; "
                "wrapped_chat_completion(c, run_id=rid, mode='record', "
                "model='gpt-4o-mini', "
                "messages=[{'role':'user','content':'Reply: SIGKILL_OK'}], "
                "max_tokens=16, temperature=0); "
                "_ready_marker_path(rid).write_text('ready', encoding='utf-8'); "
                "time.sleep(3600)"
            ),
        ],
        env=os.environ.copy(),
    )

    try:
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if ready.is_file():
                break
            if child.poll() is not None:
                break
            time.sleep(0.02)
        else:
            print("TEST 4 — real SIGKILL after response on disk: FAIL")
            print("  timed out waiting for child to finish recording")
            return False

        if child.poll() is not None:
            print("TEST 4 — real SIGKILL after response on disk: FAIL")
            print(f"  child exited early with code {child.returncode}")
            return False

        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()

    killed_by_sigkill = child.returncode is not None and child.returncode != 0
    survived = False
    detail = ""
    try:
        events = _read_events(path)
        responses = [e for e in events if e.get("kind") == "response"]
        if len(responses) != 1:
            detail = f"expected 1 response event, got {len(responses)}"
        else:
            ChatCompletion.model_validate(responses[0]["payload"])
            survived = "SIGKILL_OK" in json.dumps(responses[0])
            if not survived:
                detail = "response JSON parseable but missing expected content"
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        detail = str(exc)

    ok = killed_by_sigkill and survived
    print(f"TEST 4 — real SIGKILL after response on disk: {'PASS' if ok else 'FAIL'}")
    print(f"  child exit code: {child.returncode} (SIGKILL expected non-zero)")
    print(f"  response event survived on local FS: {'yes' if survived else 'no'}")
    if detail:
        print(f"  detail: {detail}")
    if ready.exists():
        ready.unlink()
    return ok


def test_3_offline_replay() -> bool:
    client, source = _client_for_tests()
    if source == "fake":
        print("  (recorded with fake client — replay still must not call OpenAI)")

    run_id = f"test3-{uuid.uuid4()}"
    path = log_path_for_run(run_id)
    if path.exists():
        path.unlink()

    wrapped_chat_completion(
        client,
        run_id=run_id,
        mode="record",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Reply with exactly: OFFLINE_OK"}],
        max_tokens=16,
        temperature=0,
    )

    env = {**os.environ, "OPENAI_API_KEY": "sk-invalid-offline-test"}
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r}); "
                "from poc_openai_record_replay import wrapped_chat_completion, _response_text; "
                f"c = wrapped_chat_completion(None, run_id={run_id!r}, mode='replay', "
                "model='gpt-4o-mini', messages=[]); "
                "print(_response_text(c))"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    ok = proc.returncode == 0 and "OFFLINE_OK" in proc.stdout
    combined = (proc.stdout or "") + (proc.stderr or "")
    if "Incorrect API key" in combined or "authentication" in combined.lower():
        ok = False

    print(f"TEST 3 — offline replay (no OpenAI call): {'PASS' if ok else 'FAIL'}")
    if not ok:
        print(f"  returncode: {proc.returncode}")
        print(f"  stdout: {proc.stdout!r}")
        print(f"  stderr: {proc.stderr!r}")
    return ok


def main() -> None:
    print("agentrr OpenAI record/replay POC\n")
    r1 = test_1_basic_round_trip()
    r2 = test_2_crash_after_response()
    r3 = test_3_offline_replay()
    r4 = test_4_real_sigkill_after_response()

    example_dir = _runs_dir()
    jsonl_files = sorted(example_dir.glob("test1-*.jsonl"), key=lambda p: p.stat().st_mtime)
    if jsonl_files:
        example = jsonl_files[-1]
        print(f"\nExample run file: {example}")
        print("--- file contents ---")
        print(example.read_text(encoding="utf-8"))
        print("--- end ---")

    if not all([r1, r2, r3, r4]):
        sys.exit(1)


if __name__ == "__main__":
    main()

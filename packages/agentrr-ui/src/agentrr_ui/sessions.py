"""Replay session manager with subprocess worker."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_STEP_TIMEOUT_SEC = 120


def _worker_pythonpath() -> str:
    """Packages + examples so replay can import agent entrypoints (dev checkout)."""
    existing = os.environ.get("PYTHONPATH", "")
    ui_pkg = Path(__file__).resolve().parent
    repo = ui_pkg.parents[3]
    examples = repo / "examples"
    if not examples.is_dir():
        return existing
    parts = [
        repo / "packages/agentrr-core/src",
        repo / "packages/agentrr-recorder/src",
        repo / "packages/agentrr-replay/src",
        repo / "packages/agentrr-sdk/src",
        repo / "packages/agentrr-cli/src",
        repo / "packages/agentrr-ui/src",
        examples,
    ]
    paths = [str(p) for p in parts if p.is_dir()]
    if existing:
        paths.append(existing)
    return os.pathsep.join(paths)


@dataclass
class ReplaySession:
    session_id: str
    log_path: Path
    mode: str
    entrypoint_spec: str | None
    process: subprocess.Popen[str]
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_active = time.time()

    def _write_and_read(self, cmd: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin and self.process.stdout
        self.process.stdin.write(json.dumps(cmd) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            err = ""
            if self.process.stderr:
                err = self.process.stderr.read() or ""
            return {
                "type": "error",
                "message": err.strip() or "worker closed stdout",
            }
        return json.loads(line)

    def send(self, cmd: dict[str, Any], *, timeout: float = _STEP_TIMEOUT_SEC) -> dict[str, Any]:
        self.touch()
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(self._write_and_read, cmd)
            try:
                return fut.result(timeout=timeout)
            except TimeoutError:
                self._kill_process()
                return {
                    "type": "error",
                    "message": f"replay step timed out after {int(timeout)}s",
                }

    def _kill_process(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            if self.process.stdin:
                self.process.stdin.write(json.dumps({"cmd": "stop"}) + "\n")
                self.process.stdin.flush()
        except Exception:
            pass
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def stop(self) -> None:
        self._kill_process()


class SessionManager:
    def __init__(self, *, ttl_seconds: int = 1800) -> None:
        self._sessions: dict[str, ReplaySession] = {}
        self._ttl = ttl_seconds

    def _worker_cmd(self, log_path: Path, mode: str, entrypoint_spec: str | None) -> list[str]:
        cmd = [
            sys.executable,
            "-m",
            "agentrr_ui.worker",
            "--log",
            str(log_path),
            "--mode",
            mode,
            "--step-boundaries",
            "story",
        ]
        if entrypoint_spec:
            cmd.extend(["--entrypoint", entrypoint_spec])
        return cmd

    def _worker_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = _worker_pythonpath()
        return env

    def start(
        self,
        log_path: Path,
        *,
        mode: str = "strict",
        entrypoint_spec: str | None = None,
    ) -> str:
        self.evict_stale()
        sid = uuid.uuid4().hex
        proc = subprocess.Popen(
            self._worker_cmd(log_path, mode, entrypoint_spec),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self._worker_env(),
        )
        self._sessions[sid] = ReplaySession(
            session_id=sid,
            log_path=log_path,
            mode=mode,
            entrypoint_spec=entrypoint_spec,
            process=proc,
        )
        return sid

    def get(self, session_id: str) -> ReplaySession | None:
        self.evict_stale()
        return self._sessions.get(session_id)

    def stop(self, session_id: str) -> None:
        sess = self._sessions.pop(session_id, None)
        if sess:
            sess.stop()

    def evict_stale(self) -> None:
        now = time.time()
        stale = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_active > self._ttl or s.process.poll() is not None
        ]
        for sid in stale:
            self.stop(sid)

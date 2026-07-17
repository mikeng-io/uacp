"""Thin, self-authored ACP client for the Proving Ground runner.

Productionizes the S0 spike harness (``scratchpad/s0-spike/acp_harness.py``): JSON-RPC over
NDJSON on a subprocess's stdio, the ``initialize -> initialized -> session/new ->
session/prompt`` lifecycle, streaming ``session/update`` collection, permission auto-reply, and a
hard watchdog that turns a hung agent into a distinct ``timeout`` outcome instead of a hang.

The full raw exchange (every line in and out, with a direction marker and a monotonic offset) is
captured to a transcript file. Per 10-topology this transcript is **runner-side ground truth** —
collected on the runner's side of the stdio boundary, which the system under test cannot author.

Permission handling is *mined* from OpenAB's Rust client
(``crates/openab-core/src/acp/connection.rs:845-885`` -- ``build_permission_response`` /
``pick_best_option``), reimplemented here rather than imported (S0 decision: the protocol is small
enough to re-author to our own seam). The mined behaviour, verbatim:

* prefer an option whose ``kind`` is ``allow_always``, then ``allow_once`` (return its ``optionId``)
* otherwise fall back to the first option whose ``kind`` is not ``reject_once`` / ``reject_always``;
* if only reject options exist, answer with a ``cancelled`` outcome;
* if the request carries no ``options`` array at all, default to ``optionId: "allow_always"``.

stdlib only.
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Sentinel returned by a transport's ``read_line`` when the underlying stream has closed (EOF).
EOF = object()

# Outcome vocabulary (also the replicate outcome enum in replicates.py).
OUTCOME_COMPLETED = "completed"
OUTCOME_TIMEOUT = "timeout"
OUTCOME_ERROR = "error"


def _status_outcome(status: str) -> str:
    """Collapse an ``_await_id`` status ("timeout" | "eof" | ...) into the closed outcome enum."""
    return OUTCOME_TIMEOUT if status == "timeout" else OUTCOME_ERROR


# --------------------------------------------------------------------------------------------------
# Permission response -- mined from openab-core/src/acp/connection.rs:845-885
# --------------------------------------------------------------------------------------------------
def pick_best_option(options: Sequence[Mapping[str, Any]]) -> str | None:
    """Choose the permission ``optionId``. Mined verbatim from OpenAB's pick_best_option."""
    for kind in ("allow_always", "allow_once"):
        for option in options:
            if option.get("kind") == kind:
                option_id = option.get("optionId")
                if isinstance(option_id, str):
                    return option_id
    for option in options:
        if option.get("kind") in ("reject_once", "reject_always"):
            continue
        option_id = option.get("optionId")
        if isinstance(option_id, str):
            return option_id
    return None


def build_permission_response(params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build the ``session/request_permission`` response. Mined from OpenAB."""
    options = (params or {}).get("options")
    if not isinstance(options, list):
        return {"outcome": {"outcome": "selected", "optionId": "allow_always"}}
    option_id = pick_best_option(options)
    if option_id is not None:
        return {"outcome": {"outcome": "selected", "optionId": option_id}}
    return {"outcome": {"outcome": "cancelled"}}


# --------------------------------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------------------------------
class SubprocessTransport:
    """NDJSON-over-stdio transport backed by a subprocess (``docker run -i ...`` or a bare command).

    A reader thread drains stdout into a queue so ``read_line`` can honour a hard per-read timeout
    (a blocking ``readline`` cannot be interrupted). stderr is drained into a bounded tail buffer.
    """

    def __init__(
        self,
        command: Sequence[str],
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
        stderr_tail: int = 200,
    ) -> None:
        self._proc = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env) if env is not None else None,
            cwd=cwd,
            text=True,
            bufsize=1,
        )
        self._queue: queue.Queue[Any] = queue.Queue()
        # deque(maxlen=...) bounds AND stays safe to snapshot while the pump thread appends;
        # a plain list with append+del races the reader's copy.
        self._stderr: deque[str] = deque(maxlen=stderr_tail)
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def _pump_stdout(self) -> None:
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            stripped = line.rstrip("\n")
            if stripped.strip():
                self._queue.put(stripped)
        self._queue.put(EOF)

    def _pump_stderr(self) -> None:
        assert self._proc.stderr is not None
        for line in self._proc.stderr:
            self._stderr.append(line.rstrip("\n"))

    def write_line(self, line: str) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def read_line(self, timeout: float | None) -> Any:
        """Return the next stdout line (str), ``EOF`` on stream close, or ``None`` on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close_stdin(self) -> None:
        if self._proc.stdin is not None:
            try:
                self._proc.stdin.close()
            except OSError:
                pass

    def terminate(self, grace: float = 2.0) -> None:
        """Terminate the subprocess, escalating to kill. Never blocks longer than ``grace``."""
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                try:
                    self._proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass

    @property
    def stderr_tail(self) -> list[str]:
        return list(self._stderr)

    @property
    def returncode(self) -> int | None:
        return self._proc.poll()

    def is_alive(self) -> bool:
        return self._proc.poll() is None


# --------------------------------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------------------------------
@dataclass
class PromptResult:
    """The result of driving one prompt. ``outcome`` is the terminal-state classification."""

    outcome: str  # OUTCOME_COMPLETED | OUTCOME_TIMEOUT | OUTCOME_ERROR
    stop_reason: str | None = None
    text: str = ""
    session_id: str | None = None
    error: dict[str, Any] | None = None
    detail: str | None = None
    update_count: int = 0
    stderr_tail: list[str] = field(default_factory=list)


class AcpClient:
    """Drives one ACP conversation over a transport, capturing the raw exchange to a transcript."""

    def __init__(
        self, transport: SubprocessTransport, transcript_path: str | Path | None = None
    ) -> None:
        self._t = transport
        self._id = 0
        self._start = time.monotonic()
        self._transcript = None
        if transcript_path is not None:
            self._transcript = open(transcript_path, "w", encoding="utf-8")  # noqa: SIM115

    # --- transcript / io ---
    def _log(self, direction: str, obj: Any) -> None:
        if self._transcript is None:
            return
        offset = time.monotonic() - self._start
        self._transcript.write(f"[{offset:8.3f}] {direction} {json.dumps(obj)}\n")
        self._transcript.flush()

    def _request(self, method: str, params: Any = None) -> int:
        """Send a JSON-RPC request (with id) and return that id."""
        self._id += 1
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "id": self._id}
        if params is not None:
            msg["params"] = params
        self._t.write_line(json.dumps(msg))
        self._log("-->", msg)
        return self._id

    def _notify(self, method: str, params: Any = None) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        msg: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._t.write_line(json.dumps(msg))
        self._log("-->", msg)

    def _respond(self, request_id: Any, result: Any) -> None:
        msg = {"jsonrpc": "2.0", "id": request_id, "result": result}
        self._t.write_line(json.dumps(msg))
        self._log("-->", msg)

    def _handle_server_request(self, obj: Mapping[str, Any]) -> None:
        method = obj.get("method", "")
        if "permission" in method:
            self._respond(obj["id"], build_permission_response(obj.get("params")))
        else:
            # Generic ack for unknown fs/terminal requests. Hermes runs its own tools inside the
            # container against the mounted workspace, so it does not delegate fs writes to us; an
            # empty ack keeps the loop from deadlocking on any request we do not model.
            self._respond(obj["id"], {})

    def _await_id(self, target_id: int, deadline: float) -> tuple[str, Any, list[dict[str, Any]]]:
        """Pump messages until the response with ``target_id`` arrives or ``deadline`` passes.

        Returns ``(status, payload, updates)`` where status is ``"ok"`` (payload = response obj),
        ``"timeout"``, or ``"eof"``.
        """
        updates: list[dict[str, Any]] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "timeout", None, updates
            item = self._t.read_line(remaining)
            if item is None:
                return "timeout", None, updates
            if item is EOF:
                return "eof", None, updates
            try:
                obj = json.loads(item)
            except json.JSONDecodeError:
                # Non-JSON stdout noise; log and ignore rather than crash the drive.
                self._log("<~~", {"unparsed": item[:400]})
                continue
            self._log("<--", obj)
            if "method" in obj and "id" in obj:  # server -> client request
                self._handle_server_request(obj)
                continue
            if "method" in obj:  # notification (e.g. session/update)
                updates.append(obj)
                continue
            if obj.get("id") == target_id:
                return "ok", obj, updates

    def close(self) -> None:
        if self._transcript is not None:
            self._transcript.close()
            self._transcript = None

    # --- high-level drive ---
    def drive_prompt(self, cwd: str, prompt_text: str, timeout: float) -> PromptResult:
        """Run the full lifecycle for one prompt under a single wall-clock ``timeout`` budget."""
        deadline = time.monotonic() + timeout

        iid = self._request("initialize", {"protocolVersion": 1, "clientCapabilities": {}})
        status, obj, _ = self._await_id(iid, deadline)
        if status != "ok":
            # Map the await status into the CLOSED outcome vocabulary: an early EOF (agent died /
            # was never an ACP speaker) is an "error" outcome, never a leaked "eof".
            return self._terminal(_status_outcome(status), detail=f"initialize: {status}")
        if obj.get("error"):
            return self._terminal("error", error=obj["error"], detail="initialize")

        self._notify("initialized")

        sid = self._request("session/new", {"cwd": cwd, "mcpServers": []})
        status, obj, _ = self._await_id(sid, deadline)
        if status != "ok":
            return self._terminal(_status_outcome(status), detail=f"session/new: {status}")
        if obj.get("error"):
            return self._terminal("error", error=obj["error"], detail="session/new")
        session_id = (obj.get("result") or {}).get("sessionId")
        if not session_id:
            return self._terminal("error", detail="session/new: no sessionId")

        pid = self._request(
            "session/prompt",
            {"sessionId": session_id, "prompt": [{"type": "text", "text": prompt_text}]},
        )
        status, obj, updates = self._await_id(pid, deadline)
        if status == "timeout":
            return self._terminal(
                "timeout", session_id=session_id, updates=updates, detail="session/prompt"
            )
        if status == "eof":
            return self._terminal(
                "error", session_id=session_id, updates=updates, detail="session/prompt: eof"
            )
        if obj.get("error"):
            return self._terminal(
                "error",
                session_id=session_id,
                updates=updates,
                error=obj["error"],
                detail="session/prompt",
            )
        stop_reason = (obj.get("result") or {}).get("stopReason")
        if stop_reason != "end_turn":
            # A refused/cancelled/limit-stopped prompt did NOT do the task; counting it as
            # `completed` would inflate success in the aggregate. The reason is preserved.
            return self._terminal(
                OUTCOME_ERROR,
                session_id=session_id,
                updates=updates,
                stop_reason=stop_reason,
                detail=f"session/prompt: stop_reason={stop_reason!r}",
            )
        return self._terminal(
            OUTCOME_COMPLETED,
            session_id=session_id,
            updates=updates,
            stop_reason=stop_reason,
        )

    def _terminal(
        self,
        outcome: str,
        *,
        session_id: str | None = None,
        updates: list[dict[str, Any]] | None = None,
        stop_reason: str | None = None,
        error: dict[str, Any] | None = None,
        detail: str | None = None,
    ) -> PromptResult:
        updates = updates or []
        return PromptResult(
            outcome=outcome,
            stop_reason=stop_reason,
            text=extract_agent_text(updates),
            session_id=session_id,
            error=error,
            detail=detail,
            update_count=len(updates),
            stderr_tail=self._t.stderr_tail,
        )


def extract_agent_text(updates: Sequence[Mapping[str, Any]]) -> str:
    """Concatenate agent message text chunks from ``session/update`` notifications."""
    chunks: list[str] = []
    for update in updates:
        params = update.get("params") or {}
        payload = params.get("update") if isinstance(params.get("update"), Mapping) else params
        if not isinstance(payload, Mapping):
            continue
        # ONLY user-visible assistant message chunks count as reply evidence. Reasoning models
        # stream far more `agent_thought_chunk` text than message text (observed live: 64
        # thought chunks vs 2 message chunks in one hermes turn) — counting thoughts would let
        # a turn with no actual reply pass the R3 real-reply discriminator.
        if payload.get("sessionUpdate") != "agent_message_chunk":
            continue
        content = payload.get("content")
        if isinstance(content, Mapping):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


def run_prompt(
    command: Sequence[str],
    prompt_text: str,
    *,
    cwd: str,
    session_cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 240.0,
    transcript_path: str | Path | None = None,
) -> PromptResult:
    """Spawn ``command``, drive one prompt, and always tear the subprocess down (no hangs).

    ``cwd`` is the subprocess working directory; ``session_cwd`` is the path sent in
    ``session/new`` (inside the container it is the mount point, e.g. ``/workspace``) and defaults
    to ``cwd`` when not given.
    """
    try:
        transport = SubprocessTransport(command, env=env, cwd=cwd)
    except OSError as exc:
        # A missing/unexecutable command (docker absent, adapter not installed) is a replicate
        # `error` outcome, not a crash — one bad spawn must not abort a whole serial sweep.
        return PromptResult(outcome=OUTCOME_ERROR, detail=f"spawn failed: {exc}")
    client = AcpClient(transport, transcript_path=transcript_path)
    try:
        return client.drive_prompt(session_cwd or cwd, prompt_text, timeout)
    except OSError as exc:
        # An agent that dies right after spawn breaks the stdin pipe on the next request write
        # (BrokenPipeError). Same contract as a failed spawn: this replicate is an `error`
        # outcome, never an exception that aborts the sweep.
        return PromptResult(
            outcome=OUTCOME_ERROR,
            detail=f"transport write failed: {exc}",
            stderr_tail=transport.stderr_tail,
        )
    finally:
        transport.close_stdin()
        transport.terminate()
        client.close()

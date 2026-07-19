#!/usr/bin/env python3
"""A minimal fake ACP agent for tests: NDJSON JSON-RPC over stdio, no docker, no model. stdlib only.

Exercises the real client framing/permission/streaming paths without any container. Modes via the
FAKE_MODE env var:

* ``complete`` (default): full handshake; on prompt it emits a streaming ``session/update`` with
  text ``PONG``, then a ``session/request_permission`` request, then -- only if the client selected
  a non-reject option -- a final result with ``stopReason: end_turn``. So a ``completed`` outcome
  with ``end_turn`` proves the client auto-answered the permission request with an allow option.
* ``hang_prompt``: handshake + session succeed, but on ``session/prompt`` it never responds
  (sleeps), so the client's watchdog must fire and produce a ``timeout`` outcome.
* ``refuse_prompt``: the permission request offers ONLY reject options, so the client answers
  ``cancelled`` and the agent finishes with ``stopReason: refused`` — the client must map that
  to an ``error`` outcome, never ``completed``.
* ``junk_frames``: on ``session/prompt`` it writes valid-but-non-object JSON frames (``[]`` and
  ``null``) then hangs — the client must skip them as noise (not AttributeError) and time out.
"""

from __future__ import annotations

import json
import os
import sys
import time


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def read_msg() -> dict | None:
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        line = line.strip()
        if line:
            return json.loads(line)


def main() -> None:
    mode = os.environ.get("FAKE_MODE", "complete")
    while True:
        msg = read_msg()
        if msg is None:
            return
        method = msg.get("method")
        mid = msg.get("id")
        if method == "initialize":
            send(
                {
                    "jsonrpc": "2.0",
                    "id": mid,
                    "result": {"protocolVersion": 1, "agentInfo": {"name": "fake", "version": "0"}},
                }
            )
        elif method == "initialized":
            continue
        elif method == "session/new":
            send({"jsonrpc": "2.0", "id": mid, "result": {"sessionId": "fake-session"}})
        elif method == "session/prompt":
            if mode == "junk_frames":
                sys.stdout.write("[]\n")
                sys.stdout.write("null\n")
                sys.stdout.flush()
                time.sleep(3600)
                return
            if mode == "hang_prompt":
                time.sleep(3600)
                return
            # A thought chunk BEFORE the message chunk: the client must exclude it from reply
            # evidence (real reasoning agents stream far more thought text than message text).
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "update": {
                            "sessionUpdate": "agent_thought_chunk",
                            "content": {"type": "text", "text": "thinking..."},
                        }
                    },
                }
            )
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "update": {
                            "sessionUpdate": "agent_message_chunk",
                            "content": {"type": "text", "text": "PONG"},
                        }
                    },
                }
            )
            if mode == "refuse_prompt":
                options = [
                    {"kind": "reject_once", "optionId": "no"},
                    {"kind": "reject_always", "optionId": "never"},
                ]
            else:
                options = [
                    {"kind": "reject_once", "optionId": "no"},
                    {"kind": "allow_always", "optionId": "yes"},
                ]
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 9001,
                    "method": "session/request_permission",
                    "params": {"options": options},
                }
            )
            resp = read_msg() or {}
            selected = ((resp.get("result") or {}).get("outcome") or {}).get("optionId")
            stop = "end_turn" if selected == "yes" else "refused"
            send({"jsonrpc": "2.0", "id": mid, "result": {"stopReason": stop}})
        else:
            if mid is not None:
                send({"jsonrpc": "2.0", "id": mid, "result": {}})


if __name__ == "__main__":
    main()

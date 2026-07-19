"""NDJSON framing round-trip + permission auto-reply, against the fake ACP agent (no docker)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from acp_client import run_prompt

FAKE = Path(__file__).resolve().parent / "fake_acp_agent.py"


def test_framing_round_trip_completes(tmp_path):
    transcript = tmp_path / "exchange.log"
    result = run_prompt(
        [sys.executable, str(FAKE)],
        "ping",
        cwd=str(tmp_path),
        env={**os.environ, "FAKE_MODE": "complete"},
        timeout=15,
        transcript_path=transcript,
    )
    # A completed end_turn is only reachable if initialize/session/prompt framing all round-tripped
    # AND the client auto-answered the permission request with the allow option.
    assert result.outcome == "completed"
    assert result.stop_reason == "end_turn"
    # Both updates (thought + message) are captured, but ONLY the message chunk is reply text.
    assert result.update_count == 2
    assert result.text == "PONG"


def test_transcript_captures_both_directions(tmp_path):
    transcript = tmp_path / "exchange.log"
    run_prompt(
        [sys.executable, str(FAKE)],
        "ping",
        cwd=str(tmp_path),
        env={**os.environ, "FAKE_MODE": "complete"},
        timeout=15,
        transcript_path=transcript,
    )
    text = transcript.read_text()
    # Runner-side ground truth: every line in and out, both directions present.
    assert "--> " in text
    assert "<-- " in text
    assert "initialize" in text
    assert "session/prompt" in text
    # The auto-sent permission response must be in the runner-side transcript.
    assert "selected" in text


def test_unspawnable_command_is_error_outcome_not_crash(tmp_path):
    """docker absent / adapter missing must yield the closed `error` outcome for THIS replicate,
    never an exception that aborts a whole serial sweep (Codex P2 on PR #158)."""
    result = run_prompt(["/nonexistent-proving-ground-binary"], "hi", cwd=str(tmp_path), timeout=5)
    assert result.outcome == "error"
    assert result.detail is not None and result.detail.startswith("spawn failed:")


def test_agent_dying_immediately_is_error_outcome_not_crash(tmp_path):
    """An agent that exits right after spawn must yield the closed `error` outcome — whether the
    failure surfaces as EOF on read or BrokenPipeError on the next stdin write, neither may
    escape run_prompt and abort a sweep (Codex P1 on PR #158)."""
    result = run_prompt(["true"], "hi", cwd=str(tmp_path), timeout=5)
    assert result.outcome == "error"
    # A dead-immediately agent that closes stdin while staying briefly alive forces the
    # broken-pipe write path specifically.
    result2 = run_prompt(["sh", "-c", "exec 0<&-; sleep 2"], "hi", cwd=str(tmp_path), timeout=5)
    assert result2.outcome == "error"


def test_refused_stop_reason_is_error_not_completed(tmp_path):
    """A prompt the agent finishes with stopReason != end_turn (e.g. `refused` after an
    all-reject permission request) did NOT do the task — counting it `completed` would inflate
    the aggregate (Codex P1 on PR #158). The reason is preserved for audit."""
    result = run_prompt(
        [sys.executable, str(FAKE)],
        "do something",
        cwd=str(tmp_path),
        env={**os.environ, "FAKE_MODE": "refuse_prompt"},
        timeout=10,
    )
    assert result.outcome == "error"
    assert result.stop_reason == "refused"
    assert "stop_reason" in (result.detail or "")


def test_thought_chunks_are_excluded_from_reply_evidence():
    """Only agent_message_chunk text is reply evidence — an end_turn with thoughts but no
    message must not read as a genuine reply (Codex P2 on PR #158; observed live: 64 thought
    chunks vs 2 message chunks in one hermes turn)."""
    from acp_client import extract_agent_text

    updates = [
        {
            "params": {
                "update": {
                    "sessionUpdate": "agent_thought_chunk",
                    "content": {"type": "text", "text": "let me reason..."},
                }
            }
        },
        {
            "params": {
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "PONG"},
                }
            }
        },
        {"params": {"update": {"sessionUpdate": "usage_update", "used": 5}}},
    ]
    assert extract_agent_text(updates) == "PONG"
    assert extract_agent_text(updates[:1]) == ""


def test_non_object_json_frame_does_not_crash_drive(tmp_path):
    """A faulty agent emitting valid-but-non-object JSON (`[]`, `null`) before its frames must
    not crash the drive with AttributeError — the frame is skipped as noise (Codex P2 on #158).
    The agent then hangs, so the drive ends in the closed `timeout` outcome, never a raise."""
    result = run_prompt(
        [sys.executable, str(FAKE)],
        "ping",
        cwd=str(tmp_path),
        env={**os.environ, "FAKE_MODE": "junk_frames"},
        timeout=2,
    )
    assert result.outcome in ("timeout", "error", "completed")  # NOT an exception
    assert result.outcome == "timeout"  # the junk-frame agent hangs after emitting noise

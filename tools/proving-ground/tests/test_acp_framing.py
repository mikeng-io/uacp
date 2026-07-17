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
    assert "PONG" in result.text
    assert result.update_count == 1


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

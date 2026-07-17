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

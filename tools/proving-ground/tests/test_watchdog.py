"""Watchdog: a hung agent must produce a distinct ``timeout`` outcome, promptly, never a hang."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from acp_client import OUTCOME_TIMEOUT, run_prompt

FAKE = Path(__file__).resolve().parent / "fake_acp_agent.py"


def test_hung_prompt_yields_timeout_outcome(tmp_path):
    timeout = 1.0
    t0 = time.monotonic()
    result = run_prompt(
        [sys.executable, str(FAKE)],
        "ping",
        cwd=str(tmp_path),
        env={**os.environ, "FAKE_MODE": "hang_prompt"},
        timeout=timeout,
        transcript_path=tmp_path / "exchange.log",
    )
    elapsed = time.monotonic() - t0
    assert result.outcome == OUTCOME_TIMEOUT
    assert result.detail and "session/prompt" in result.detail
    # It must return promptly after the deadline (watchdog fired), not hang for the fake's sleep.
    assert elapsed < timeout + 8.0

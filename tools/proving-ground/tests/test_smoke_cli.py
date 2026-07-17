"""Smoke CLI contract: the 40-benchmark N>=5 floor is enforced before anything runs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SMOKE = Path(__file__).resolve().parents[1] / "scripts" / "smoke.py"


def test_smoke_rejects_replicates_below_five():
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "-n", "1"], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode != 0
    assert "at least 5 replicates" in proc.stderr

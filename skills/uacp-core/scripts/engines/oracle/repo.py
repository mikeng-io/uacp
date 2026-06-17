"""Minimal git helpers for the Oracle engine. No external deps."""
from __future__ import annotations

import subprocess
from pathlib import Path


def repo_commit(workspace: Path) -> str:
    """Return the HEAD commit SHA for the repo at workspace, or '' on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""

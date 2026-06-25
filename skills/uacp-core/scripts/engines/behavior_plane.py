"""UACP behavioral-plane runner (capsule #3 / node 32 — the reality-binding endgame, slice 0).

A ``uacp.check.behavioral`` exercises the work and binds to the RESULT, not an artifact: it runs a
DECLARED command and binds PASS/FAIL/ERROR to the command's outcome (exit code, optionally stdout).

ISOLATION (node 32 class E — env-FRAGILITY): the run is isolated from incidental state for
REPRODUCIBILITY — a contained cwd under the workspace, a SCRUBBED minimal env (PATH only, NOT the
inherited environment), no inherited stdin (DEVNULL), and a bounded timeout. The command is an ARGV
LIST run with ``shell=False`` — never a shell string (no shell injection / glob surprises).

HONEST SCOPE: this is env-isolation for REPRODUCIBILITY, NOT a security sandbox against a HOSTILE
command — container-grade isolation (network / filesystem / resource jails) is the deferred
follow-on (node 32: "heaviest, later"). The command is the agent's own governed verification step.

FAIL-CLOSED (never a silent pass): a malformed command, a cwd escaping the workspace, a bad timeout,
a timeout expiry, or any spawn failure is an ERROR (block). A command that runs but exits with an
unexpected code (or whose stdout lacks the expected text) is a FAIL. Never raises.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_DEFAULT_TIMEOUT = 30
_MAX_TIMEOUT = 300


def resolve_behavior(workspace: str | Path, bind: dict, expect: object) -> tuple[str, str]:
    """Return ``(PASS|FAIL|ERROR, detail)`` for a ``uacp.check.behavioral`` bind by running
    ``bind.command`` (argv list) in an isolated subprocess and comparing its result to ``expect``
    (``exit_code`` default 0, optional ``stdout_contains``). Never raises."""
    cmd = bind.get("command")
    if not isinstance(cmd, list) or not cmd or not all(isinstance(a, str) for a in cmd):
        return ("ERROR", "behavioral: bind.command must be a non-empty list of string args (argv)")
    try:
        base = Path(str(workspace)).resolve()
    except OSError as exc:
        return ("ERROR", f"behavioral: workspace unresolvable: {type(exc).__name__}: {exc}")
    cwd_rel = str(bind.get("cwd") or "")
    try:
        cwd = (base / cwd_rel).resolve()
        cwd.relative_to(base)  # containment — the command may not run outside the workspace
    except (ValueError, OSError):
        return ("ERROR", f"behavioral: cwd {cwd_rel!r} escapes the workspace")
    if not cwd.is_dir():
        return ("ERROR", f"behavioral: cwd {cwd_rel!r} is not a directory")
    try:
        timeout = max(1, min(int(bind.get("timeout", _DEFAULT_TIMEOUT)), _MAX_TIMEOUT))
    except (TypeError, ValueError):
        return ("ERROR", f"behavioral: timeout {bind.get('timeout')!r} is not an integer")
    exp = expect if isinstance(expect, dict) else {}
    try:
        expected_code = int(exp.get("exit_code", 0))
    except (TypeError, ValueError):
        return ("ERROR", f"behavioral: expect.exit_code {exp.get('exit_code')!r} is not an integer")
    # SCRUBBED env (isolation from incidental state): PATH only, never the inherited os.environ.
    env = {"PATH": os.environ.get("PATH", "")}
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), env=env, capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL, check=False,
        )
    except subprocess.TimeoutExpired:
        return ("ERROR", f"behavioral: command timed out after {timeout}s")
    except (OSError, ValueError) as exc:
        return ("ERROR", f"behavioral: command could not run: {type(exc).__name__}: {exc}")
    if proc.returncode != expected_code:
        return ("FAIL", f"command exited {proc.returncode} != expected {expected_code}")
    contains = exp.get("stdout_contains")
    if contains is not None and str(contains) not in proc.stdout:
        return ("FAIL", f"stdout does not contain {str(contains)!r}")
    return ("PASS", "")

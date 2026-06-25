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
import signal
import subprocess
import tempfile
from pathlib import Path

_DEFAULT_TIMEOUT = 30
_MAX_TIMEOUT = 300
_MAX_OUTPUT = 1 << 20  # 1 MiB captured is ample for a stdout_contains check (bounds gate memory)


def _int_field(value: object) -> int | None:
    """A strict int (YAML ints), rejecting bool (an int subclass) + float/str. None == reject."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _terminate_group(proc: subprocess.Popen) -> None:
    """SIGKILL the child's whole process GROUP and reap it — a double-forking command must not leak
    orphan/grandchild processes past the gate (council). Best-effort; never raises."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass


def resolve_behavior(workspace: str | Path, bind: object, expect: object) -> tuple[str, str]:
    """Return ``(PASS|FAIL|ERROR, detail)`` for a ``uacp.check.behavioral`` bind by running
    ``bind.command`` (argv list) in an isolated subprocess and comparing its result to ``expect``
    (``exit_code`` default 0, optional ``stdout_contains``). Never raises."""
    if not isinstance(bind, dict):
        return ("ERROR", "behavioral: bind must be a mapping")
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
    raw_to = bind.get("timeout", _DEFAULT_TIMEOUT)
    secs = _int_field(raw_to)
    if secs is None or secs < 1:
        return ("ERROR", f"behavioral: timeout {raw_to!r} must be a positive integer (seconds)")
    timeout = min(secs, _MAX_TIMEOUT)
    exp = expect if isinstance(expect, dict) else {}
    expected_code = _int_field(exp.get("exit_code", 0))
    if expected_code is None:
        return ("ERROR", f"behavioral: expect.exit_code {exp.get('exit_code')!r} must be an int")
    # SCRUBBED env (isolation from incidental state): PATH only, never the inherited os.environ.
    env = {"PATH": os.environ.get("PATH", "")}
    # Capture stdout to a TEMP FILE (not an in-memory pipe) so a runaway command cannot OOM the
    # verifying gate (council: 80MB stdout drove RSS +280MB); read back only a bounded slice. The
    # child runs in its OWN process group (start_new_session) so a timeout kills the whole tree.
    try:
        with tempfile.TemporaryFile() as out:
            try:
                proc = subprocess.Popen(
                    cmd, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                    stdout=out, stderr=subprocess.DEVNULL, start_new_session=True,
                )
            except (OSError, ValueError) as exc:
                return ("ERROR", f"behavioral: command could not run: {type(exc).__name__}: {exc}")
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_group(proc)
                return ("ERROR", f"behavioral: command timed out after {timeout}s")
            out.seek(0)
            stdout = out.read(_MAX_OUTPUT).decode("utf-8", "replace")
    except OSError as exc:
        return ("ERROR", f"behavioral: capture failed: {type(exc).__name__}: {exc}")
    if proc.returncode != expected_code:
        return ("FAIL", f"command exited {proc.returncode} != expected {expected_code}")
    contains = exp.get("stdout_contains")
    if contains is not None and str(contains) not in stdout:
        return ("FAIL", f"stdout does not contain {str(contains)!r}")
    return ("PASS", "")

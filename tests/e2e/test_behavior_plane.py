"""E2E (capsule #3 / node 32): the behavioral-plane runner (slice 0).

`uacp.check.behavioral` exercises the work and binds to the RESULT: it runs a declared argv command
in an isolated subprocess (contained cwd, SCRUBBED env, timeout, no inherited stdin) and binds
PASS/FAIL/ERROR to the exit code / expected stdout. Env-isolation for reproducibility (node 32 class
E) — NOT a security sandbox; fail-closed on any spawn/timeout/malformed-input.
"""

from __future__ import annotations

import sys
from pathlib import Path

from engines.behavior_plane import resolve_behavior

PY = sys.executable


def test_passing_command_binds_pass(tmp_path: Path):
    assert resolve_behavior(tmp_path, {"command": [PY, "-c", "print('ok')"]}, {})[0] == "PASS"


def test_nonzero_exit_fails(tmp_path: Path):
    bind = {"command": [PY, "-c", "import sys; sys.exit(3)"]}
    status, detail = resolve_behavior(tmp_path, bind, {})
    assert status == "FAIL" and "3" in detail


def test_expected_nonzero_exit_passes(tmp_path: Path):
    bind = {"command": [PY, "-c", "import sys; sys.exit(3)"]}
    assert resolve_behavior(tmp_path, bind, {"exit_code": 3})[0] == "PASS"


def test_stdout_contains(tmp_path: Path):
    bind = {"command": [PY, "-c", "print('the-token')"]}
    assert resolve_behavior(tmp_path, bind, {"stdout_contains": "the-token"})[0] == "PASS"
    assert resolve_behavior(tmp_path, bind, {"stdout_contains": "absent"})[0] == "FAIL"


def test_timeout_is_error(tmp_path: Path):
    bind = {"command": [PY, "-c", "import time; time.sleep(5)"], "timeout": 1}
    status, detail = resolve_behavior(tmp_path, bind, {})
    assert status == "ERROR" and "timed out" in detail


def test_malformed_command_is_error(tmp_path: Path):
    for bad in ([], "echo hi", [1, 2], None):
        assert resolve_behavior(tmp_path, {"command": bad}, {})[0] == "ERROR"


def test_missing_executable_is_error(tmp_path: Path):
    status, _ = resolve_behavior(tmp_path, {"command": ["definitely_not_a_real_cmd_xyz"]}, {})
    assert status == "ERROR"


def test_cwd_escape_is_error(tmp_path: Path):
    status, detail = resolve_behavior(tmp_path, {"command": [PY, "-c", "pass"], "cwd": "../.."}, {})
    assert status == "ERROR" and "escapes" in detail


def test_env_is_scrubbed(tmp_path: Path, monkeypatch):
    # isolation: an incidental env var must NOT leak into the run (only PATH is passed).
    monkeypatch.setenv("UACP_INCIDENTAL_SECRET", "leak")
    code = "import os,sys; sys.exit(1 if 'UACP_INCIDENTAL_SECRET' in os.environ else 0)"
    bind = {"command": [PY, "-c", code]}
    assert resolve_behavior(tmp_path, bind, {})[0] == "PASS"  # exit 0 == var absent == scrubbed


def test_behavioral_wired_into_replay_not_unwired_error(tmp_path: Path):
    # the kind is WIRED: a behavioral check must resolve (PASS/FAIL), not the until-wired
    # "plane not wired" ERROR that every OTHER behavior-plane kind still gets.
    from engines.manifest.projection import _evaluate_check

    bind = {"plane": "behavior", "command": [PY, "-c", "print('x')"]}
    status, detail = _evaluate_check(tmp_path, "uacp.check.behavioral", bind, {}, set(), {}, {})
    assert status == "PASS", (status, detail)
    # a DIFFERENT behavior-plane kind still ERRORs fail-closed-until-wired.
    s2, d2 = _evaluate_check(tmp_path, "uacp.check.field_equals", {"plane": "behavior"}, {},
                             set(), {}, {})
    assert s2 == "ERROR" and "not wired" in d2

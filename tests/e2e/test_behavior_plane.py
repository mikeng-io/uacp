"""E2E (capsule #3 / node 32): the behavioral-plane runner (slice 0).

`uacp.check.behavioral` exercises the work and binds to the RESULT: it runs a declared argv command
in an isolated subprocess (contained cwd, SCRUBBED env, timeout, no inherited stdin) and binds
PASS/FAIL/ERROR to the exit code / expected stdout. Env-isolation for reproducibility (node 32 class
E) — NOT a security sandbox; fail-closed on any spawn/timeout/malformed-input.
"""

from __future__ import annotations

import sys
import time
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


def test_non_dict_bind_is_error_not_raise(tmp_path: Path):
    # council: "Never raises" — a non-dict bind must ERROR, not AttributeError.
    for bad in (None, "nope", [1, 2], 7):
        assert resolve_behavior(tmp_path, bad, {})[0] == "ERROR"


def test_non_integer_timeout_is_error(tmp_path: Path):
    # council: strict int — float/bool/negative/string timeouts ERROR (not silently coerced).
    for bad in (1.9, True, -5, "10", None):
        bind = {"command": [PY, "-c", "pass"], "timeout": bad}
        assert resolve_behavior(tmp_path, bind, {})[0] == "ERROR", bad


def test_large_output_is_bounded_not_oom(tmp_path: Path):
    # council: a runaway-output command must not OOM the gate — captured to a capped tempfile.
    bind = {"command": [PY, "-c", "print('x' * (3 * 1024 * 1024))"]}  # 3 MiB to stdout
    assert resolve_behavior(tmp_path, bind, {})[0] == "PASS"


def test_timeout_kills_the_process_group(tmp_path: Path):
    # council MEDIUM (proved end-to-end): a timeout must kill the child's whole process GROUP, so a
    # double-forked grandchild can't outlive the gate. The grandchild writes a marker after 3s; the
    # runner times out at 1s and group-kills it, so the marker must never appear.
    marker = tmp_path / "gc.marker"
    gc = tmp_path / "gc.py"
    gc.write_text(f"import time; time.sleep(3); open(r'{marker}', 'w').write('x')")
    parent = tmp_path / "parent.py"
    parent.write_text(
        f"import subprocess,sys,time; subprocess.Popen([sys.executable, r'{gc}']); time.sleep(10)"
    )
    status, _ = resolve_behavior(tmp_path, {"command": [PY, str(parent)], "timeout": 1}, {})
    assert status == "ERROR"
    time.sleep(4)  # past the grandchild's 3s sleep
    assert not marker.exists()  # the process-group kill stopped it before it could write


def test_behavioral_wired_into_replay_not_unwired_error(tmp_path: Path):
    # the kind is WIRED: a behavioral check must resolve (PASS/FAIL), not the until-wired
    # "plane not wired" ERROR that every OTHER behavior-plane kind still gets.
    from engines.manifest.projection import _evaluate_check

    bind = {"plane": "behavior", "command": [PY, "-c", "print('x')"]}
    status, detail = _evaluate_check(tmp_path, "uacp.check.behavioral", bind, {}, set(), {}, {})
    assert status == "PASS", (status, detail)
    # a DIFFERENT behavior-plane kind still ERRORs fail-closed-until-wired.
    s2, d2 = _evaluate_check(
        tmp_path, "uacp.check.field_equals", {"plane": "behavior"}, {}, set(), {}, {}
    )
    assert s2 == "ERROR" and "not wired" in d2

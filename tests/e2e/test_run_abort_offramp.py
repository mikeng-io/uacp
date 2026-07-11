"""E2E (#107): the governed abort off-ramp under PRODUCTION gate defaults.

Drives init -> register -> abort for a run through the REAL Guardian + governed
handlers (the byte-equivalent of the MCP transport) against the production config
tree (mirrors the keystone ``prod_uacp_root`` bypass so Layer-B admission is the
real one, not the fixture's slim stages stub). Proves the acceptance criteria:

  * an active run can be aborted in one governed call from a mid-lifecycle phase;
  * the abort is admitted by Guardian Layer-B as a governed ``state.uacp`` writer
    (never falls through to an ungoverned mutator or gets false-blocked);
  * the run's registry entry is deregistered so its ``write_paths`` no longer block
    an overlapping SUCCESSOR run (which then registers the same path cleanly);
  * the active-run pointer is released with provenance; the manifest is aborted;
  * an aborted run can no longer transition.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import state_machine
import yaml
from state import _handle_uacp_run_abort, _handle_uacp_run_registry_update

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites

RUN_A = "uacp-abort-e2e-A"
RUN_B = "uacp-abort-e2e-B"
SHARED_PATH = "executions/shared-artifact.txt"


@pytest.fixture
def prod_uacp_root() -> Generator[Path]:
    """Sandbox UACP_ROOT wired with the PRODUCTION config tree (no stages stub ->
    stages_default() applies, so Guardian Layer-B uses the real allowlists)."""
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-abort-e2e-"))
    original_cwd = os.getcwd()
    base = test_dir / ".uacp"
    for sub in ("state/runs", "state/gate-ledger", "state/escalations", "plans", "executions"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (test_dir / "docs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REAL_CONFIG, test_dir / "config")
    (test_dir / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_VALIDATOR, test_dir / "scripts" / "validate_uacp_artifacts.py")
    os.chdir(test_dir)
    old = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = str(test_dir)
    try:
        yield test_dir
    finally:
        if old is None:
            os.environ.pop("UACP_ROOT", None)
        else:
            os.environ["UACP_ROOT"] = old
        os.chdir(original_cwd)
        shutil.rmtree(test_dir, ignore_errors=True)


def _ctx(root: Path, run_id: str, phase: str, **extra) -> dict:
    base = {
        "uacp_run_id": run_id,
        "uacp_phase": phase,
        "workspace": str(root),
        "policy_version": "0.1",
        "authority_artifact": "plans/test.yaml",
        "reason": "e2e abort off-ramp",
        "declared_side_effects": [],
    }
    base.update(extra)
    return base


def _register(driver: Driver, root: Path, run_id: str, phase: str) -> dict:
    return driver.call(
        "uacp_run_registry_update",
        _handle_uacp_run_registry_update,
        _ctx(
            root,
            run_id,
            phase,
            op="register",
            entry={
                "run_id": run_id,
                "phase": phase,
                "write_paths": [SHARED_PATH],
                "scope_artifact_path": f"plans/{run_id}-scope.yaml",
                "started_at": 0,
            },
        ),
        phase=phase,
    )


def _registered_ids(root: Path) -> list[str]:
    reg = root / ".uacp" / "state" / "run-registry.yaml"
    data = yaml.safe_load(reg.read_text()) if reg.exists() else {}
    return [e["run_id"] for e in (data.get("active_runs") or [])]


def test_governed_abort_frees_paths_for_a_successor(prod_uacp_root: Path) -> None:
    root = prod_uacp_root
    driver_a = Driver(root, RUN_A)

    # Create run A and drive it to EXECUTE, then register its write_paths.
    init = driver_a.call(
        "uacp_state_write",
        state_machine.handle_init,
        {"workspace": str(root), "run_id": RUN_A, "source": "operator-request"},
        phase="triage",
    )
    assert init.get("ok") is True, init
    # #99: the live plan->execute path forces the scope-artifact + PLAN_VALIDATION +
    # run-registry gates. Seed the faithful plan-exit prerequisites; declare the run's
    # write_paths so the scope matches what run A later registers (SHARED_PATH). The
    # empty registry seeded here holds no active runs, so plan->execute self-blocks on
    # nothing — the overlap semantics (A frees the path for successor B) still hold.
    seed_plan_exit_prerequisites(root, RUN_A, write_paths=[SHARED_PATH])
    for frm, to in (("triage", "propose"), ("propose", "plan"), ("plan", "execute")):
        tr = driver_a.call(
            "uacp_state_write",
            state_machine.handle_transition,
            {"workspace": str(root), "run_id": RUN_A, "from_phase": frm, "to_phase": to},
            phase=frm,
        )
        assert tr.get("ok") is True, tr
    reg = _register(driver_a, root, RUN_A, "execute")
    assert reg.get("ok") is True, reg
    assert RUN_A in _registered_ids(root)

    # ABORT run A through the GOVERNED wrapper — Guardian Layer-B must admit it as
    # a state.uacp writer in the execute phase (the Driver asserts no false-block).
    out = driver_a.call(
        "uacp_run_abort",
        _handle_uacp_run_abort,
        _ctx(root, RUN_A, "execute", disposition="abandoned"),
        phase="execute",
    )
    assert out.get("ok") is True, out
    assert out["status"] == "aborted"
    assert out["phase_at_abort"] == "execute"

    # Registry entry gone -> write_paths freed.
    assert RUN_A not in _registered_ids(root)

    # Pointer released with provenance.
    cur = yaml.safe_load((root / ".uacp" / "state" / "current.yaml").read_text())
    assert cur["active_run_id"] is None
    assert cur["released_by"] == f"{RUN_A}@abort"

    # Manifest is aborted with the disposition recorded; ledger carries ABORT.
    m = yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{RUN_A}.yaml").read_text())
    assert m["status"] == "aborted"
    assert m["abort"]["disposition"] == "abandoned"
    ledger = (root / ".uacp" / "state" / "gate-ledger" / f"{RUN_A}.jsonl").read_text()
    assert '"gate": "ABORT"' in ledger or '"ABORT"' in ledger

    # An aborted run can no longer transition.
    blocked = driver_a.call(
        "uacp_state_write",
        state_machine.handle_transition,
        {"workspace": str(root), "run_id": RUN_A, "from_phase": "execute", "to_phase": "verify"},
        phase="execute",
    )
    assert "error" in blocked and "not active" in blocked["error"], blocked

    # SUCCESSOR run B claims the SAME write_paths — now free — and registers cleanly.
    driver_b = Driver(root, RUN_B)
    init_b = driver_b.call(
        "uacp_state_write",
        state_machine.handle_init,
        {"workspace": str(root), "run_id": RUN_B, "source": "operator-request"},
        phase="triage",
    )
    assert init_b.get("ok") is True, init_b
    reg_b = _register(driver_b, root, RUN_B, "triage")
    assert reg_b.get("ok") is True, reg_b
    ids = _registered_ids(root)
    assert RUN_B in ids and RUN_A not in ids

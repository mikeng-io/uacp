"""Feature test for #99: the three EVIDENCE-BASED PLAN->EXECUTE gates — scope-artifact,
PLAN_VALIDATION ledger, and run-registry write-path overlap — are FORCED onto the live
``handle_transition`` path via ``_run_forced_plan_exit_gate`` (the function the governed
``uacp_run_transition`` calls), not only reachable through the agent-invoked
``validate_transition``.

Proven at the live-path wrapper under PRODUCTION config. (Under the shared temp fixture only
``plan_validation`` opts out; ``scope`` and ``run_registry`` are code defaults that fire even
there — so ``prod_uacp_root`` copies the real config to enforce all three uniformly, the
fixture-vs-production keystone pattern.) The validators read the run's real serialized state
(scope file, gate-ledger, registry), so no full lifecycle drive is needed to exercise the gate
logic; the happy-path integration through ``handle_transition`` is covered by
``test_lifecycle_production_drivability``.

The wrapper returns ``(blockers, advisories)``: blockers block the transition; advisories are
non-blocking findings surfaced on the live path (Codex #144 P2).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml
from state_machine import _run_forced_plan_exit_gate

from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import _seed_plan_validation_ledger

RUN = "uacp-fpe-001"


@pytest.fixture
def prod_uacp_root() -> Generator[Path]:
    """Sandbox UACP_ROOT wired with the PRODUCTION config tree so the plan-exit gates
    enforce (the shared temp_uacp_root fixture opts them out). Mirrors the keystone's
    per-module fixture — the codebase convention is a local copy, not a cross-module import."""
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-fpe-"))
    original_cwd = os.getcwd()
    base = test_dir / ".uacp"
    for sub in (
        "state/runs",
        "state/gate-ledger",
        "state/escalations",
        "plans",
        "proposals",
        "executions",
        "resolutions",
        "verification",
        "knowledge",
    ):
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


def _write_scope(root: Path, run_id: str, write_paths: list[str] | None = None) -> None:
    paths = list(write_paths or [])
    (root / ".uacp" / "plans" / f"{run_id}-scope.yaml").write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.scope",
                "run_id": run_id,
                "write_paths": paths,
                "no_writes_intended": not paths,
                "blast_radius": "low",
                "rollback_path": "none--test-run",
            },
            sort_keys=False,
        )
    )


def _write_registry(root: Path, entries: list[dict]) -> None:
    (root / ".uacp" / "state" / "run-registry.yaml").write_text(
        yaml.safe_dump({"active_runs": entries}, sort_keys=False)
    )


def test_live_plan_exit_forces_scope_artifact(prod_uacp_root: Path):
    """No scope artifact -> the forced gate BLOCKS the live PLAN->EXECUTE with a scope blocker
    (the scope gate is no longer skippable by driving handle_transition instead of the tool)."""
    blockers, _adv = _run_forced_plan_exit_gate(prod_uacp_root, RUN, "plan", "execute")
    assert any("scope artifact" in b for b in blockers), blockers


def test_live_plan_exit_forces_plan_validation_ledger(prod_uacp_root: Path):
    """Scope present but no PLAN_VALIDATION ledger record -> BLOCKS with a plan_validation
    blocker (scope is now satisfied, so the block is specifically the ledger gate)."""
    _write_scope(prod_uacp_root, RUN)
    blockers, _adv = _run_forced_plan_exit_gate(prod_uacp_root, RUN, "plan", "execute")
    assert any("plan_validation_gate" in b for b in blockers), blockers
    assert not any("scope artifact" in b for b in blockers), blockers


def test_live_plan_exit_forces_registry_overlap(prod_uacp_root: Path):
    """Scope + PLAN_VALIDATION satisfied, but the declared write_paths overlap another ACTIVE
    run -> BLOCKS with a run_registry overlap blocker (the overlap gate is wired live)."""
    _write_scope(prod_uacp_root, RUN, write_paths=["executions/"])
    _seed_plan_validation_ledger(prod_uacp_root, RUN)
    _write_registry(prod_uacp_root, [{"run_id": "uacp-other-001", "write_paths": ["executions/"]}])
    blockers, _adv = _run_forced_plan_exit_gate(prod_uacp_root, RUN, "plan", "execute")
    assert any("run_registry" in b and "overlap" in b for b in blockers), blockers


def test_live_plan_exit_advances_when_all_prerequisites_met(prod_uacp_root: Path):
    """Scope + PLAN_VALIDATION + no registry overlap -> the forced gate returns NO blockers
    (the faithful governed plan-exit passes)."""
    _write_scope(prod_uacp_root, RUN)
    _write_registry(prod_uacp_root, [])
    _seed_plan_validation_ledger(prod_uacp_root, RUN)
    assert _run_forced_plan_exit_gate(prod_uacp_root, RUN, "plan", "execute") == ([], [])


def test_live_plan_exit_surfaces_nonblocking_advisories(prod_uacp_root: Path):
    """Codex #144 P2: a non-blocking finding must NOT vanish on the live path. With scope +
    PLAN_VALIDATION satisfied but NO run-registry file yet, the overlap gate PASSES (no
    blocker) but emits a registry-absent WARNING — which the forced gate surfaces as a
    transition advisory rather than dropping it."""
    _write_scope(prod_uacp_root, RUN)
    _seed_plan_validation_ledger(prod_uacp_root, RUN)
    # Deliberately do NOT write state/run-registry.yaml.
    blockers, advisories = _run_forced_plan_exit_gate(prod_uacp_root, RUN, "plan", "execute")
    assert blockers == [], blockers
    assert any("run_registry" in a and "not yet present" in a for a in advisories), advisories


def test_live_plan_exit_gate_self_gates_off_non_plan_exit(prod_uacp_root: Path):
    """The forced gate only fires at the PLAN exit: an EXECUTE->VERIFY transition demands no
    scope/ledger/overlap here (each validator self-gates to plan->execute, and the wrapper
    short-circuits on from_phase)."""
    assert _run_forced_plan_exit_gate(prod_uacp_root, RUN, "execute", "verify") == ([], [])

"""Unit tests for the `graph_invariant` phase-exit-invariant kind (D35 increment 2).

Heartgate._validate_phase_exit_invariants gains a third invariant kind alongside
`artifact_glob` and `gate_ledger_entry`: `graph_invariant: <scope>`, which runs
the phase-scoped subset of the graph_projection engine for the transition being
exited and turns its block-severity violations into transition blockers.

These tests drive the method directly (isolating the new branch from the ~8 other
gates `validate_transition` runs for plan->execute); the end-to-end public path is
covered by the lifecycle e2e in increment 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Heartgate


def _run(tmp_path: Path, *, drop_si2: bool, obligation: bool = True) -> Path:
    """Build a .uacp workspace whose run 'r' has a proposal+plan (and a PIV).

    drop_si2=True leaves si-2 with no work_unit deriving from it (a dropped
    intent the plan_exit gate must catch). obligation=False removes ev-1.
    Returns the workspace root to hand to Heartgate(uacp_root=...).
    """
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "proposals").mkdir()
    (base / "plans").mkdir()
    in_scope = [{"id": "si-1", "statement": "covered"}]
    if drop_si2:
        in_scope.append({"id": "si-2", "statement": "dropped"})
    (base / "proposals" / "p.yaml").write_text(yaml.safe_dump(
        {"kind": "uacp.proposal", "scope": {"in_scope": in_scope, "out_of_scope": []}}))
    (base / "plans" / "p.yaml").write_text(yaml.safe_dump(
        {"kind": "uacp.plan", "work_units": [{"id": "wu-1", "derives_from": ["si-1"]}]}))
    arts = {"proposal": "proposals/p.yaml", "plan": "plans/p.yaml"}
    if obligation:
        (base / "plans" / "piv.yaml").write_text(yaml.safe_dump(
            {"kind": "uacp.piv", "evidence_obligations": [{"id": "ev-1", "work_unit_id": "wu-1"}]}))
        arts["piv"] = "plans/piv.yaml"
    (base / "state" / "runs" / "r.yaml").write_text(yaml.safe_dump(
        {"kind": "uacp.run_state", "run_id": "r", "artifacts": arts}))
    return tmp_path


def _hg(uacp_root: Path, invariants: list) -> Heartgate:
    """A Heartgate whose stages.plan carries the given phase_exit_invariants."""
    return Heartgate({"stages": {"plan": {"phase_exit_invariants": invariants}}},
                     uacp_root=uacp_root)


_GI = [{"graph_invariant": "plan_exit", "required": True}]


def test_graph_invariant_blocks_dropped_intent(tmp_path):
    hg = _hg(_run(tmp_path, drop_si2=True), _GI)
    blockers: list = []
    hg._validate_phase_exit_invariants({"from_phase": "plan", "run_id": "r"}, blockers)
    assert any("GP_UNCOVERED_INTENT" in b for b in blockers), blockers
    assert any("si-2" in b for b in blockers), blockers


def test_graph_invariant_clean_run_adds_no_blocker(tmp_path):
    # Non-vacuous: the SAME gate fires on the broken sibling (above); here, a fully
    # covered run with every work_unit obligated must add NO graph blocker.
    hg = _hg(_run(tmp_path, drop_si2=False, obligation=True), _GI)
    blockers: list = []
    hg._validate_phase_exit_invariants({"from_phase": "plan", "run_id": "r"}, blockers)
    assert blockers == [], blockers


def test_graph_invariant_required_false_is_skipped(tmp_path):
    # required:false must NOT enforce the gate even on a broken run.
    hg = _hg(_run(tmp_path, drop_si2=True), [{"graph_invariant": "plan_exit", "required": False}])
    blockers: list = []
    hg._validate_phase_exit_invariants({"from_phase": "plan", "run_id": "r"}, blockers)
    assert blockers == [], blockers


def test_graph_invariant_unknown_scope_is_loud(tmp_path):
    # A misconfigured scope name must surface, not silently pass.
    hg = _hg(_run(tmp_path, drop_si2=False), [{"graph_invariant": "bogus_exit", "required": True}])
    blockers: list = []
    hg._validate_phase_exit_invariants({"from_phase": "plan", "run_id": "r"}, blockers)
    assert any("GP0_UNKNOWN_SCOPE" in b for b in blockers), blockers


def test_graph_invariant_other_phase_does_not_run_plan_gate(tmp_path):
    # The invariant lives under stages.plan; exiting a different phase must not run it.
    hg = _hg(_run(tmp_path, drop_si2=True), _GI)
    blockers: list = []
    hg._validate_phase_exit_invariants({"from_phase": "execute", "run_id": "r"}, blockers)
    assert blockers == [], blockers

"""D35 increment 3 — the DEFAULT config (stages_default) enforces the phase-keyed
graph gates (production default-on).

Production `config/phase-transitions.yaml` ships no `stages` block, so the kernel
injects `stages_default()`; these tests construct `Heartgate({})` (same injection)
and drive `_validate_phase_exit_invariants` directly, proving the default plan/
execute/verify exits now carry a `graph_invariant` that fires on a broken graph
and is silent on a clean one. (The sibling artifact_glob/gate_ledger invariants in
the default may add their OWN blockers — unrelated to the graph — so the clean
assertions check specifically that NO `GP_` blocker is present, paired with the
broken case for non-vacuity.)

The conftest `temp_uacp_root` fixture ships its own stages block (no invariants)
and so is unaffected; this is the deliberate test-vs-production asymmetry.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Heartgate


def _w(path: Path, doc: dict) -> None:
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def _seed(
    root: Path,
    *,
    drop_intent: bool = False,
    drop_checkpoint: bool = False,
    drop_assessment: bool = False,
) -> Path:
    """Seed a keyed full-lifecycle run 'r' (proposal->plan->piv->execution->verify)
    and register every artifact in the manifest. Knobs drop one coverage layer."""
    base = root / ".uacp"
    for d in ("state/runs", "proposals", "plans", "executions", "verification"):
        (base / d).mkdir(parents=True, exist_ok=True)
    in_scope = [{"id": "si-1", "statement": "covered"}]
    if drop_intent:
        in_scope.append({"id": "si-2", "statement": "dropped"})
    _w(
        base / "proposals" / "p.yaml",
        {"kind": "uacp.proposal", "scope": {"in_scope": in_scope, "out_of_scope": []}},
    )
    _w(
        base / "plans" / "pl.yaml",
        {"kind": "uacp.plan", "work_units": [{"id": "wu-1", "derives_from": ["si-1"]}]},
    )
    _w(
        base / "plans" / "piv.yaml",
        {"kind": "uacp.piv", "evidence_obligations": [{"id": "ev-1", "work_unit_id": "wu-1"}]},
    )
    arts = {"proposal": "proposals/p.yaml", "plan": "plans/pl.yaml", "piv": "plans/piv.yaml"}
    if not drop_checkpoint:
        # Real execution_checkpoint (D42): ONE doc per checkpoint (checkpoint_id + work_unit_id +
        # evidence[]); cp-1's outcome rolls up from evidence[].result.
        _w(
            base / "executions" / "ex.yaml",
            {
                "kind": "uacp.execution_checkpoint",
                "checkpoint_id": "cp-1",
                "work_unit_id": "wu-1",
                "evidence": [{"obligation_id": "ev-1", "result": "pass", "summary": "x"}],
            },
        )
        arts["execution"] = "executions/ex.yaml"
    if not drop_assessment:
        _w(
            base / "verification" / "ve.yaml",
            {
                "kind": "uacp.piv_assessment",
                "assessments": [
                    {
                        "id": "as-1",
                        "work_unit_id": "wu-1",
                        "evidence_refs": ["cp-1"],
                        "state": "pass",
                    }
                ],
            },
        )
        arts["verification"] = "verification/ve.yaml"
    _w(
        base / "state" / "runs" / "r.yaml",
        {"kind": "uacp.run_state", "run_id": "r", "artifacts": arts},
    )
    return root


def _blockers(ws: Path, from_phase: str) -> list:
    hg = Heartgate({}, uacp_root=ws)  # config={} -> stages_default() injected (production default)
    b: list = []
    hg._validate_phase_exit_invariants({"from_phase": from_phase, "run_id": "r"}, b)
    return b


def _gp(blockers: list) -> list:
    return [b for b in blockers if "GP_" in b]


# --------------------------------------------------------------- plan exit
def test_default_plan_gate_blocks_dropped_intent(tmp_path):
    b = _blockers(_seed(tmp_path, drop_intent=True), "plan")
    assert any("GP_UNCOVERED_INTENT" in x and "si-2" in x for x in b), b


def test_default_plan_gate_clean_has_no_graph_block(tmp_path):
    # Non-vacuous vs the broken case above: a fully-covered keyed run produces NO
    # graph blocker at plan exit (sibling glob/ledger blockers are not GP_).
    assert _gp(_blockers(_seed(tmp_path), "plan")) == []


# ------------------------------------------------------------ execute exit
def test_default_execute_gate_blocks_missing_checkpoint(tmp_path):
    b = _blockers(_seed(tmp_path, drop_checkpoint=True), "execute")
    assert any("GP_WORK_UNIT_NO_CHECKPOINT" in x for x in b), b


def test_default_execute_gate_clean_has_no_graph_block(tmp_path):
    assert _gp(_blockers(_seed(tmp_path), "execute")) == []


# ------------------------------------------------------------- verify exit
def test_default_verify_gate_blocks_unverified(tmp_path):
    b = _blockers(_seed(tmp_path, drop_assessment=True), "verify")
    assert any("GP_UNVERIFIED" in x for x in b), b


def test_default_verify_gate_clean_has_no_graph_block(tmp_path):
    assert _gp(_blockers(_seed(tmp_path), "verify")) == []

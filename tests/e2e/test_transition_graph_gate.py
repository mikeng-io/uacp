"""E2E: prove the phase-scoped structural graph gate is wired onto the LIVE
transition path (handle_transition), not only reachable via the agent-invoked
Heartgate.validate_transition.

The structural per-transition gate `validate_graph_invariants(run_id, "<phase>_exit")`
(D35) already existed, but on the live path `handle_transition` advanced a phase
with ONLY the structural graph check (from/to allowed) — it never ran the gate.
The rich gate fired only if the agent voluntarily called `uacp_heartgate_check`.
That is the transition-side of the #503-class fail-open: the semantic gate is
skippable.

These tests drive a run to the `plan` phase, then:

  * a clean plan advances plan->execute (the gate runs AND passes);
  * a plan carrying a PHANTOM `derives_from` edge (a work_unit deriving from a
    scope_item that does not exist — a forged/dangling reference) is BLOCKED by
    `handle_transition` itself, with `GP_PHANTOM_EDGE` surfaced, and the run is
    NOT advanced.

The teeth test FAILS before the wiring (handle_transition returns ok, advancing
the phase) and passes after — non-vacuous proof the gate fires at the transition.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
import yaml

from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites


def _call(fn, args: dict) -> dict:
    return json.loads(fn(args))


def _drive_to_plan(root: Path, run_id: str) -> None:
    assert _call(
        state_machine.handle_init,
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"},
    ).get("ok")
    for frm, to in [("triage", "propose"), ("propose", "plan")]:
        assert _call(
            state_machine.handle_transition,
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to},
        ).get("ok"), f"{frm}->{to}"
    # #99: the live plan->execute path now forces the scope-artifact + PLAN_VALIDATION +
    # run-registry gates. Seed the faithful plan-exit prerequisites here so an advances-test
    # crosses; a phantom-edge test still BLOCKS on GP_PHANTOM_EDGE (scope passing does not
    # mask the graph blocker), and the plan doc each test registers supplies the rest.
    seed_plan_exit_prerequisites(root, run_id)


def _register_plan(root: Path, run_id: str, plan_doc: dict) -> None:
    rel = f"plans/{run_id}-plan.yaml"
    (root / ".uacp" / "plans").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / rel).write_text(yaml.safe_dump(plan_doc, sort_keys=False))
    assert _call(
        state_machine.handle_register_artifact,
        {"workspace": str(root), "run_id": run_id, "artifact_type": "plan", "path": rel},
    ).get("ok")


def _phase(root: Path, run_id: str) -> str:
    data = yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())
    return data["current_phase"]


# ----------------------------------------------------------------- positive path
def test_clean_plan_advances_through_the_gate(temp_uacp_root: Path, valid_run_id: str):
    _drive_to_plan(temp_uacp_root, valid_run_id)
    # A coherent plan: the one work_unit derives from a declared scope_item — no
    # phantom edge, so the plan_exit structural gate passes.
    _register_plan(
        temp_uacp_root,
        valid_run_id,
        {
            "kind": "uacp.plan",
            "scope": {"in_scope": [{"id": "si-1", "statement": "do the thing"}]},
            "work_units": [{"id": "wu-1", "derives_from": ["si-1"]}],
            "evidence_obligations": [{"id": "ob-1", "work_unit_id": "wu-1"}],
        },
    )
    out = _call(
        state_machine.handle_transition,
        {
            "workspace": str(temp_uacp_root),
            "run_id": valid_run_id,
            "from_phase": "plan",
            "to_phase": "execute",
        },
    )
    assert out.get("ok") is True, out
    assert _phase(temp_uacp_root, valid_run_id) == "execute"


# --------------------------------------------------------------------- the teeth
def test_phantom_edge_blocks_transition(temp_uacp_root: Path, valid_run_id: str):
    _drive_to_plan(temp_uacp_root, valid_run_id)
    # A work_unit deriving from a scope_item that does NOT exist: a forged/dangling
    # reference. The plan_exit structural gate must catch it (GP_PHANTOM_EDGE).
    _register_plan(
        temp_uacp_root,
        valid_run_id,
        {
            "kind": "uacp.plan",
            "scope": {"in_scope": [{"id": "si-1", "statement": "real intent"}]},
            "work_units": [
                {"id": "wu-1", "derives_from": ["si-1"]},
                {"id": "wu-2", "derives_from": ["si-GHOST"]},  # phantom
            ],
            # Both work_units carry obligations so the ONLY structural defect is
            # the phantom edge (isolates what this test is about).
            "evidence_obligations": [
                {"id": "ob-1", "work_unit_id": "wu-1"},
                {"id": "ob-2", "work_unit_id": "wu-2"},
            ],
        },
    )
    out = _call(
        state_machine.handle_transition,
        {
            "workspace": str(temp_uacp_root),
            "run_id": valid_run_id,
            "from_phase": "plan",
            "to_phase": "execute",
        },
    )
    assert "error" in out, f"expected transition to be blocked, got: {out}"
    blockers = " ".join(out.get("blockers") or [])
    assert "GP_PHANTOM_EDGE" in blockers, out
    # NOT advanced: the run is still in plan.
    assert _phase(temp_uacp_root, valid_run_id) == "plan"


def test_warn_severity_advisory_rides_the_success_response(
    temp_uacp_root: Path, valid_run_id: str, monkeypatch
):
    """PR #95 review P2: on the GOVERNED path (handle_transition), a warn-severity
    graph finding (e.g. SC_PLAN_CASCADE_FORECAST) must ride the success response as
    an advisory — the crossing proceeds, the finding stays visible — instead of
    being computed-then-discarded. Block-severity behavior is untouched (the
    phantom-edge teeth above are the regression net)."""
    from engines import graph_projection as gp
    from engines.base import Violation

    _drive_to_plan(temp_uacp_root, valid_run_id)

    monkeypatch.setattr(
        gp,
        "validate_graph_invariants",
        lambda root, run_id, scope: [
            Violation(
                code="SC_PLAN_CASCADE_FORECAST",
                severity="warn",
                message="predicted out-of-boundary cascade: ['elsewhere.py']",
            )
        ],
    )
    out = _call(
        state_machine.handle_transition,
        {
            "workspace": str(temp_uacp_root),
            "run_id": valid_run_id,
            "from_phase": "plan",
            "to_phase": "execute",
        },
    )
    assert out.get("ok") is True, out  # advisory NEVER blocks the governed crossing
    advisories = out.get("advisories")
    assert advisories and any("SC_PLAN_CASCADE_FORECAST" in a for a in advisories), out

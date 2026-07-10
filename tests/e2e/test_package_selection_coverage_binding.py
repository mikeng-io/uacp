"""E2E (D43 Option B): coverage BINDS on the package-selection path via REGISTRATION.

The governed entity-write path already binds (``test_transition_coverage_enforced``):
``uacp_entity_write`` AUTO-registers, so projection (which reads only
``manifest.artifacts``) sees the keyed ``scope_items`` + PIV ``work_units`` and the
forced ``plan_exit`` gate fires ``GP_UNCOVERED_INTENT`` on a dropped intent.

The **package-selection** representation carried its scope as a *referenced* module
and its work in a *referenced* PIV that were REFERENCED-not-REGISTERED, so projection
projected nothing and a dropped intent escaped coverage. Option B closes this by
REGISTRATION — two distinct teeth, one test each kind:

* **Enforcement (the new production teeth, RED before the gate change):** the adaptive
  proposal gate now REQUIRES the keyed scope module be REGISTERED, not merely present
  on disk + marked ``covered`` (``test_unregistered_keyed_scope_blocks_propose_to_plan``).
  Without this, a package-selection producer could leave its scope unregistered and the
  forced ``plan_exit`` gate would project nothing → the dropped-intent detector never binds.

* **Binding on the FORCED path (regression lock):** once the producer registers the keyed
  scope + a covering PIV (as the gate now compels), a dropped intent BLOCKS at
  ``state_machine.handle_transition(plan -> execute)`` — the forced path, not just the
  agent-invoked ``validate_transition`` — and a fully-covered run advances.

The binding mechanism (projection + the forced gate) already handled REGISTERED artifacts
regardless of how they were registered; what Option B adds is COMPELLING the
package-selection producer to register at the proposal gate, so a COMPLIANT run (one that
exits PROPOSE through ``validate_transition``) can no longer skip coverage.

RESIDUAL #1 (coverage half) — CLOSED on the forced path: the registration requirement also
runs on ``state_machine.handle_transition(propose->plan)`` now, via the forced precondition
``Heartgate.forced_proposal_coverage_blockers`` (see the two ``test_forced_propose_plan_*``
cases below). So an agent that skips ``validate_transition`` can no longer leave the keyed
scope module unregistered and starve the plan_exit coverage gate. Forcing the FULL adaptive
package/evidence gates onto the live path remains a separate, broader kernel item.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
import yaml
from core import Heartgate

from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites

# --- package-selection producer mechanics (write a referenced module, then register) ---


def _init(root: Path, run_id: str) -> None:
    state_machine.handle_init(
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
    )


def _write(root: Path, rel: str, doc: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _register(root: Path, run_id: str, artifact_type: str, rel: str) -> dict:
    return json.loads(
        state_machine.handle_register_artifact(
            {
                "workspace": str(root),
                "run_id": run_id,
                "artifact_type": artifact_type,
                "path": rel,
            }
        )
    )


def _scope_doc(in_scope: list[dict]) -> dict:
    return {"kind": "uacp.proposal", "scope": {"in_scope": in_scope, "out_of_scope": []}}


def _piv_doc(run_id: str, derives_from: list[str]) -> dict:
    return {
        "kind": "uacp.phase_intent_verification_contract",
        "phase": "plan",
        "run_id": run_id,
        "applies_to_phase": "execute",
        "phase_intent": {"summary": "ship x"},
        "work_units": [
            {
                "id": "wu-1",
                "intent": "do x",
                "expected_outputs": ["o"],
                "derives_from": derives_from,
            }
        ],
        "evidence_obligations": [
            {
                "id": "ob-1",
                "work_unit_id": "wu-1",
                "required": True,
                "evidence_type": "test",
                "sufficiency": "green",
                "description": "x lands",
            }
        ],
        "checkpoint_policy": {},
        "intent_drift_conditions": [],
        "next_phase_handoff": {},
    }


def _selection_doc(run_id: str, scope_rel: str) -> dict:
    """A package-selection envelope whose scope concern is COVERED by ``scope_rel``."""
    na = {
        "status": "not_applicable",
        "reason": "trivial coverage-binding fixture",
        "accepted_by": "e2e",
        "owner": "e2e",
        "residual_risk": "none",
        "revisit_phase": "resolved",
    }
    core = {
        key: dict(na)
        for key in (
            "intent",
            "authority",
            "scope",
            "containment",
            "risk",
            "verification",
            "transition",
            "artifact_map",
        )
    }
    core["scope"] = {"status": "covered", "artifact": scope_rel}
    return {
        "kind": "uacp.proposal_package_selection",
        "run_id": run_id,
        "universal_core": core,
        "selected_modules": {
            "core": {"reason": "minimal", "artifact": f"proposals/{run_id}/m.yaml"}
        },
    }


def _seed_package_envelope(root: Path, run_id: str, scope_rel: str) -> None:
    """The on-disk package-selection envelope the propose->plan gate requires."""
    (root / ".uacp" / "proposals" / run_id).mkdir(parents=True, exist_ok=True)
    _write(root, f"proposals/{run_id}/m.yaml", {"kind": "uacp.proposal_module", "body": "stub"})
    (root / ".uacp" / "proposals" / f"{run_id}-package-selection.yaml").write_text(
        yaml.safe_dump(_selection_doc(run_id, scope_rel), sort_keys=False), encoding="utf-8"
    )


def _advance_to_plan(root: Path, run_id: str) -> None:
    for frm, to in [("triage", "propose"), ("propose", "plan")]:
        out = json.loads(
            state_machine.handle_transition(
                {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
            )
        )
        assert out.get("ok"), f"{frm}->{to}: {out}"


def _try_plan_to_execute(root: Path, run_id: str) -> dict:
    return json.loads(
        state_machine.handle_transition(
            {"workspace": str(root), "run_id": run_id, "from_phase": "plan", "to_phase": "execute"}
        )
    )


def _phase(root: Path, run_id: str) -> str:
    return yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())[
        "current_phase"
    ]


# --- enforcement: the gate now COMPELS registration (RED before the gate change) ---

_REGISTER_MSG = "must be registered"


def _propose_plan_blockers(root: Path, run_id: str) -> list[str]:
    return (
        Heartgate.load(str(root))
        .validate_transition(
            {
                "from_phase": "propose",
                "to_phase": "plan",
                "run_id": run_id,
                "artifact_path": "plans/test.yaml",
            }
        )
        .blockers
    )


def test_unregistered_keyed_scope_blocks_propose_to_plan(temp_uacp_root: Path):
    """A keyed scope module present on disk + marked covered, but NOT registered in
    the run manifest, must BLOCK propose->plan — otherwise projection sees no
    scope_items and the forced coverage gate has nothing to enforce."""
    run_id = "uacp-pkgcov-enf-1"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    _write(temp_uacp_root, scope_rel, _scope_doc([{"id": "si-1", "statement": "the intent"}]))
    _seed_package_envelope(temp_uacp_root, run_id, scope_rel)
    # Deliberately do NOT register the scope module.
    blockers = _propose_plan_blockers(temp_uacp_root, run_id)
    assert any(_REGISTER_MSG in b for b in blockers), blockers


def test_registered_keyed_scope_satisfies_registration_requirement(temp_uacp_root: Path):
    """Registering the keyed scope module clears the registration blocker (the
    other unseeded gates may still block — irrelevant here)."""
    run_id = "uacp-pkgcov-enf-2"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    _write(temp_uacp_root, scope_rel, _scope_doc([{"id": "si-1", "statement": "the intent"}]))
    _seed_package_envelope(temp_uacp_root, run_id, scope_rel)
    assert _register(temp_uacp_root, run_id, "scope", scope_rel).get("ok")
    blockers = _propose_plan_blockers(temp_uacp_root, run_id)
    assert not any(_REGISTER_MSG in b for b in blockers), blockers


# --- binding on the FORCED handle_transition path (regression lock) ---


def test_registered_dropped_intent_blocks_at_forced_plan_exit(temp_uacp_root: Path):
    run_id = "uacp-pkgcov-bind-1"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    piv_rel = f"plans/{run_id}-piv.yaml"
    # Two declared intents; the PIV covers only si-1 -> si-2 is dropped.
    _write(
        temp_uacp_root,
        scope_rel,
        _scope_doc([{"id": "si-1", "statement": "a"}, {"id": "si-2", "statement": "b dropped"}]),
    )
    _write(temp_uacp_root, piv_rel, _piv_doc(run_id, ["si-1"]))
    assert _register(temp_uacp_root, run_id, "scope", scope_rel).get("ok")
    assert _register(temp_uacp_root, run_id, "piv", piv_rel).get("ok")
    _advance_to_plan(temp_uacp_root, run_id)

    out = _try_plan_to_execute(temp_uacp_root, run_id)
    assert "error" in out, f"expected dropped intent to block plan->execute, got {out}"
    assert any("GP_UNCOVERED_INTENT" in b for b in out.get("blockers", [])), out
    assert _phase(temp_uacp_root, run_id) == "plan", "blocked transition must not advance"


def test_registered_covered_run_advances_at_forced_plan_exit(temp_uacp_root: Path):
    run_id = "uacp-pkgcov-bind-2"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    piv_rel = f"plans/{run_id}-piv.yaml"
    _write(
        temp_uacp_root,
        scope_rel,
        _scope_doc([{"id": "si-1", "statement": "a"}, {"id": "si-2", "statement": "b"}]),
    )
    _write(temp_uacp_root, piv_rel, _piv_doc(run_id, ["si-1", "si-2"]))
    assert _register(temp_uacp_root, run_id, "scope", scope_rel).get("ok")
    assert _register(temp_uacp_root, run_id, "piv", piv_rel).get("ok")
    _advance_to_plan(temp_uacp_root, run_id)

    # #99: cross the forced plan-exit gates (scope artifact + PLAN_VALIDATION + run
    # registry) faithfully; the registered scope module + covering PIV supply graph coverage.
    seed_plan_exit_prerequisites(temp_uacp_root, run_id)
    out = _try_plan_to_execute(temp_uacp_root, run_id)
    assert out.get("ok") is True, out
    assert _phase(temp_uacp_root, run_id) == "execute"


# --- residual #1 (coverage half) CLOSED on the FORCED handle_transition path ---


def _transition(root: Path, run_id: str, frm: str, to: str) -> dict:
    return json.loads(
        state_machine.handle_transition(
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
        )
    )


def test_forced_propose_plan_blocks_unregistered_keyed_scope(temp_uacp_root: Path):
    """node-15 residual #1 (coverage half) CLOSED. A package-selection envelope whose
    scope concern is COVERED by a keyed module that is NOT registered is blocked at
    ``state_machine.handle_transition(propose->plan)`` — the FORCED path, with NO
    ``validate_transition`` call — because the forced registration precondition runs
    there now. Registering the scope module lets it through. This is what stops an
    agent that skips ``uacp_heartgate_check`` from starving the plan_exit coverage
    gate (leaving a dropped intent uncatchable)."""
    run_id = "uacp-pkgcov-forced-1"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    _write(temp_uacp_root, scope_rel, _scope_doc([{"id": "si-1", "statement": "the intent"}]))
    _seed_package_envelope(temp_uacp_root, run_id, scope_rel)  # scope concern covered -> scope_rel

    assert _transition(temp_uacp_root, run_id, "triage", "propose").get("ok")

    # Forced propose->plan with the keyed scope UNREGISTERED -> blocked on the live path.
    out = _transition(temp_uacp_root, run_id, "propose", "plan")
    assert "error" in out, f"expected forced block on unregistered keyed scope, got {out}"
    assert any(_REGISTER_MSG in b for b in out.get("blockers", [])), out
    assert _phase(temp_uacp_root, run_id) == "propose", "blocked transition must not advance"

    # Register the scope module -> the forced precondition is satisfied, advance.
    assert _register(temp_uacp_root, run_id, "scope", scope_rel).get("ok")
    out = _transition(temp_uacp_root, run_id, "propose", "plan")
    assert out.get("ok") is True, out
    assert _phase(temp_uacp_root, run_id) == "plan"


def test_forced_propose_plan_ignores_bare_transition(temp_uacp_root: Path):
    """Non-vacuity / no-ripple guard: the forced precondition self-gates on ENVELOPE
    PRESENCE. A run with NO package-selection envelope (a bare transition) advances
    propose->plan untouched — the forced check only fires for governed package runs."""
    run_id = "uacp-pkgcov-forced-2"
    _init(temp_uacp_root, run_id)
    assert _transition(temp_uacp_root, run_id, "triage", "propose").get("ok")
    out = _transition(temp_uacp_root, run_id, "propose", "plan")
    assert out.get("ok") is True, out
    assert _phase(temp_uacp_root, run_id) == "plan"


def _envelope_path(root: Path, run_id: str) -> Path:
    return root / ".uacp" / "proposals" / f"{run_id}-package-selection.yaml"


def test_forced_propose_plan_blocks_not_applicable_scope(temp_uacp_root: Path):
    """Council finding A (fail-open) FIXED. An agent that skips validate_transition and
    marks its package scope 'not_applicable' (declaring its real intent elsewhere) used
    to advance the FORCED path uncaught — now the forced precondition is fail-CLOSED:
    an envelope is present but its scope is not covered+keyed, so propose->plan blocks."""
    run_id = "uacp-pkgcov-na-1"
    _init(temp_uacp_root, run_id)
    scope_rel = f"proposals/{run_id}/scope-module.yaml"
    _write(temp_uacp_root, scope_rel, _scope_doc([{"id": "si-1", "statement": "the intent"}]))
    _seed_package_envelope(temp_uacp_root, run_id, scope_rel)
    # Flip the scope concern to not_applicable (the pre-fix forced-path bypass).
    env = yaml.safe_load(_envelope_path(temp_uacp_root, run_id).read_text())
    env["universal_core"]["scope"] = {
        "status": "not_applicable",
        "reason": "x",
        "accepted_by": "x",
        "owner": "x",
        "residual_risk": "none",
        "revisit_phase": "resolved",
    }
    _envelope_path(temp_uacp_root, run_id).write_text(yaml.safe_dump(env, sort_keys=False))

    assert _transition(temp_uacp_root, run_id, "triage", "propose").get("ok")
    out = _transition(temp_uacp_root, run_id, "propose", "plan")
    assert "error" in out, f"not_applicable scope must block the forced path, got {out}"
    assert any("must be 'covered'" in b for b in out.get("blockers", [])), out
    assert _phase(temp_uacp_root, run_id) == "propose"


def test_forced_propose_plan_blocks_garbled_envelope(temp_uacp_root: Path):
    """Council finding A (fail-open) FIXED. A garbled (non-mapping) package-selection
    envelope must NOT bypass the forced precondition: an envelope file is present, so
    it must parse — otherwise propose->plan blocks (fail-closed)."""
    run_id = "uacp-pkgcov-garbled-1"
    _init(temp_uacp_root, run_id)
    _envelope_path(temp_uacp_root, run_id).parent.mkdir(parents=True, exist_ok=True)
    _envelope_path(temp_uacp_root, run_id).write_text("just a bare string, not a mapping\n")

    assert _transition(temp_uacp_root, run_id, "triage", "propose").get("ok")
    out = _transition(temp_uacp_root, run_id, "propose", "plan")
    assert "error" in out, f"garbled envelope must block the forced path, got {out}"
    assert any("must parse as a mapping" in b for b in out.get("blockers", [])), out
    assert _phase(temp_uacp_root, run_id) == "propose"


def test_forced_propose_plan_accepts_inherited_scope_registration(temp_uacp_root: Path):
    """Council finding B (false-block) FIXED. A goal-chained child that REUSES a parent's
    registered keyed scope module via inherited_artifacts must NOT be false-blocked: the
    registration precondition counts inherited_artifacts too (matching projection's load
    set), so the child advances propose->plan."""
    parent_id = "uacp-pkgcov-parent"
    child_id = "uacp-pkgcov-child"
    # Parent: register a keyed scope module under the reusable 'proposal' phase key.
    state_machine.handle_init(
        {"workspace": str(temp_uacp_root), "run_id": parent_id, "source": "operator-request"}
    )
    scope_rel = f"proposals/{parent_id}/scope-module.yaml"
    _write(temp_uacp_root, scope_rel, _scope_doc([{"id": "si-1", "statement": "the intent"}]))
    assert _register(temp_uacp_root, parent_id, "proposal", scope_rel).get("ok")
    # Child inherits the parent's reusable prior-phase artifacts (incl. 'proposal').
    state_machine.handle_init(
        {
            "workspace": str(temp_uacp_root),
            "run_id": child_id,
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g-1",
            "inherits_from": parent_id,
        }
    )
    # Child's package envelope points its (covered, keyed) scope at the INHERITED module.
    _seed_package_envelope(temp_uacp_root, child_id, scope_rel)

    assert _transition(temp_uacp_root, child_id, "triage", "propose").get("ok")
    out = _transition(temp_uacp_root, child_id, "propose", "plan")
    assert out.get("ok") is True, f"inherited registered scope must not false-block: {out}"
    assert _phase(temp_uacp_root, child_id) == "plan"

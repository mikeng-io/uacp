"""E2E: a full run threaded through real Guardian/Heartgate/state machine/writers.

Drives a single run INIT -> (per phase: gate-ledger append + Heartgate-validated
transition) -> FINALIZE using the real kernel components, then asserts on the
emitted trajectory (run manifest state_history/status/finalized_at + gate-ledger
line count) rather than on file paths or config contents, so the test survives a
later config refactor.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import state_machine
import yaml
from core import Heartgate
from state import _handle_uacp_gate_ledger_append

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import (
    REAL_CONFIG,
    REAL_VALIDATOR,
    _seed_governed_run,
)

# config files the in-process offline validator (validate_configs) hard-requires
# beyond the fixture's minimal phase-transitions.yaml. Copied from the real repo
# config so validate_configs/validate_evidence_registry resolve cleanly; the
# config-consistency cross-checks against the minimal fixture stages are WARN-only
# (never BLOCK), so they cannot fail the transition.
_VALIDATOR_CONFIG_FILES = ("evidence-clusters.yaml", "state.yaml", "uacp.toml")

PHASES = [
    ("triage", "propose"),
    ("propose", "plan"),
    ("plan", "execute"),
    ("execute", "verify"),
    ("verify", "resolved"),
]

# universal_core concerns the kernel's always-on package gates enforce. We mark
# each "not_applicable" with full justification so no per-key artifact file is
# needed — the gate still verifies the package envelope exists and is coherent.
_PROPOSAL_CORE = [
    "intent",
    "authority",
    "scope",
    "containment",
    "risk",
    "verification",
    "transition",
    "artifact_map",
]
_PLAN_CORE = [
    "work_breakdown",
    "dependencies",
    "authority_and_side_effects",
    "tool_runtime_selection",
    "artifact_write_surfaces",
    "verification_strategy",
    "rollback_recovery",
    "council_review_topology",
    "transition_readiness",
]


def _na_block(*, with_trigger: bool = False) -> dict:
    block = {
        "status": "not_applicable",
        "reason": "trivial e2e run; concern not material",
        "accepted_by": "e2e-harness",
        "owner": "e2e-harness",
        "residual_risk": "none",
        "revisit_phase": "resolved",
    }
    if with_trigger:
        block["revisit_trigger"] = "scope expands beyond harness"
    return block


def _seed_intent_doc(root: Path, run_id: str) -> None:
    """Create the intent doc (proposals/{run_id}-intent.md) the triage->propose
    Heartgate gate requires. The four required sections match
    IntentSchema.required_sections (codified in engines/domain/artifact_schema.py)."""
    (root / ".uacp" / "proposals").mkdir(parents=True, exist_ok=True)
    intent_path = root / ".uacp" / "proposals" / f"{run_id}-intent.md"
    intent_path.write_text(
        f"# Intent: {run_id}\n\n"
        "## Success Definition\n\nE2E harness run reaches resolved state.\n\n"
        "## Explicit Out-of-Scope\n\nAll production changes; this is a test run.\n\n"
        "## Termination Condition\n\nRun reaches resolved phase with no open blockers.\n\n"
        "## Authority Source\n\nE2E test harness; governed under uacp-test policy.\n"
    )


def _seed_proposal_package(root: Path, run_id: str) -> None:
    """Create the proposal package + selection the propose->plan gate requires."""
    pkg_dir = root / ".uacp" / "proposals" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    module_artifact = f"proposals/{run_id}/module-core.yaml"
    (root / ".uacp" / module_artifact).write_text("kind: uacp.proposal_module\nbody: stub\n")
    selection = {
        "kind": "uacp.proposal_package_selection",
        "run_id": run_id,
        "universal_core": {key: _na_block() for key in _PROPOSAL_CORE},
        "selected_modules": {
            "core": {"reason": "minimal e2e module", "artifact": module_artifact},
        },
    }
    (root / ".uacp" / "proposals" / f"{run_id}-package-selection.yaml").write_text(
        yaml.safe_dump(selection, sort_keys=False)
    )


def _seed_plan_package(root: Path, run_id: str) -> None:
    """Create the plan package + selection + scope the plan->execute gate requires."""
    pkg_dir = root / ".uacp" / "plans" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    module_artifact = f"plans/{run_id}/module-core.yaml"
    (root / ".uacp" / module_artifact).write_text("kind: uacp.plan_module\nbody: stub\n")
    # Scope artifact: required fields are run_id, write_paths, blast_radius,
    # rollback_path (codified in ScopeSchema / IntentSchema — Slice 4a).
    # Use no_writes_intended: true to satisfy the non-empty write_paths gate
    # (this is a test run; no governed write surfaces are claimed).
    (root / ".uacp" / "plans" / f"{run_id}-scope.yaml").write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.scope",
                "run_id": run_id,
                "write_paths": [],
                "no_writes_intended": True,
                "blast_radius": "low",
                "rollback_path": "none--write-only-artifact",
            },
            sort_keys=False,
        )
    )
    # The run_registry_rule fires on plan->execute and warns when the registry
    # is absent. Seed it (empty active set) so this is a clean pass, not a warn.
    (root / ".uacp" / "state" / "run-registry.yaml").write_text(
        yaml.safe_dump({"active_runs": []}, sort_keys=False)
    )
    selection = {
        "kind": "uacp.plan_package_selection",
        "phase": "plan",
        "run_id": run_id,
        "universal_core": {key: _na_block(with_trigger=True) for key in _PLAN_CORE},
        "selected_modules": {
            "core": {"reason": "minimal e2e module", "artifact": module_artifact},
        },
        "transition_readiness": {"status": "ready_for_execute"},
    }
    (root / ".uacp" / "plans" / f"{run_id}-plan-selection.yaml").write_text(
        yaml.safe_dump(selection, sort_keys=False)
    )


def _seed_execute_evidence(root: Path, run_id: str) -> None:
    """Create the PIV + checkpoint + execution package the execute->verify gate
    requires. As of F-T3-01 the adaptive_execute_evidence_gate fails CLOSED: it
    enforces on EVERY execute->verify regardless of config, so this seeding is
    mandatory (not optional) for the happy path.

    The gate calls Heartgate._offline_validate_artifacts in-process, which loads
    <root>/scripts/validate_uacp_artifacts.py — so the real validator script must
    be present under the test root for the gate to clear.

    The artifact-seeding contract is owned by _seed_governed_run in
    test_adaptive_evidence_gate_uacp (single source of truth). This function
    handles only the lifecycle-specific setup: copying the real validator script
    and the extra config files the in-process offline validator hard-requires.
    """
    # The in-process offline validator is loaded from <root>/scripts/.
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_VALIDATOR, scripts_dir / "validate_uacp_artifacts.py")

    # validate_configs() hard-requires evidence-clusters.yaml + state.yaml (and
    # reads uacp.toml for the heartgate consistency cross-check). The fixture only
    # writes phase-transitions.yaml, so copy the rest from the real repo config.
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    for name in _VALIDATOR_CONFIG_FILES:
        shutil.copy2(REAL_CONFIG / name, cfg_dir / name)

    # Seed all governed artifacts (PIV, checkpoint, semantic package,
    # state/current.yaml, and the manifest/transition stubs it references) under
    # .uacp/ — the single authoritative seeder from test_adaptive_evidence_gate_uacp.
    # validate_configs() also runs validate_current_state(), which BLOCKs unless
    # state/current.yaml is a fully-formed governed pointer to run-bound, existing
    # manifest/transition artifacts. The state machine writes a MINIMAL current.yaml
    # (active_run_id + manifest only), so this seeder overwrites it with a conformant
    # pointer. This is consumed only by the in-process validator at the execute->verify
    # check; the state machine rewrites current.yaml on the next handle_transition,
    # so this does not perturb later lifecycle steps.
    _seed_governed_run(root / ".uacp", run_id)


# Per-(from,to) real-evidence seeding the kernel's adaptive gates REQUIRE — not
# optional. The propose->plan and plan->execute gates read config via
# `self.config.get(key) or {}`: an absent key becomes `{}`, still a Mapping, so
# the gate fires and demands its artifacts regardless of config. The
# execute->verify gate fails CLOSED as of F-T3-01 (it no longer self-disables on
# absent config), so it too demands its evidence on every run. Drop any of these
# seeders and the happy path fails (e.g. "adaptive_proposal_package_gate: missing
# proposals/<run>-package-selection.yaml" or "adaptive_execute_evidence_gate:
# artifact not found: plans/<run>-piv.yaml").
_SEEDERS = {
    # Slice 4a: schemas always codified → Heartgate now enforces triage->propose
    # (intent doc) and plan->execute (scope artifact required fields) on EVERY run.
    ("triage", "propose"): _seed_intent_doc,
    ("propose", "plan"): _seed_proposal_package,
    ("plan", "execute"): _seed_plan_package,
    # F-T3-01: execute->verify evidence gate now fails closed → seed real evidence.
    ("execute", "verify"): _seed_execute_evidence,
}


def test_full_lifecycle_reaches_resolved(temp_uacp_root: Path, valid_run_id: str):
    d = Driver(temp_uacp_root, valid_run_id)
    heartgate = Heartgate.load(str(temp_uacp_root))

    init = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_init(a),
        {
            "workspace": str(temp_uacp_root),
            "run_id": valid_run_id,
            "source": "operator-request",
        },
        phase="triage",
    )
    assert init.get("ok") is True, init

    for frm, to in PHASES:
        ledger = d.call(
            "uacp_gate_ledger_append",
            _handle_uacp_gate_ledger_append,
            {
                "uacp_run_id": valid_run_id,
                "uacp_phase": frm,
                "workspace": str(temp_uacp_root),
                "policy_version": "0.1",
                "declared_side_effects": [],
                "gate": f"{frm.upper()}->{to.upper()}",
                "record": {"result": "pass"},
                "authority_artifact": "plans/test.yaml",
            },
            phase=frm,
        )
        assert ledger.get("ok") is True, ledger

        # Seed the evidence artifacts the kernel's always-on adaptive gates
        # require for this transition (real evidence, not a loosened assertion).
        if seeder := _SEEDERS.get((frm, to)):
            seeder(temp_uacp_root, valid_run_id)

        hg = heartgate.validate_transition(
            {
                "from_phase": frm,
                "to_phase": to,
                "run_id": valid_run_id,
                "artifact_path": "plans/test.yaml",
            }
        )
        assert hg.decision == "pass", f"Heartgate blocked legit {frm}->{to}: {hg.blockers}"

        tr = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_transition(a),
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "from_phase": frm,
                "to_phase": to,
            },
            phase=frm,
        )
        assert tr.get("ok") is True, tr

    # RESOLVE: author + register the lessons (closure) artifact BEFORE finalize.
    # handle_finalize now runs the closure sweep on the live path, which requires a
    # genuinely closeable run (coherence C4 needs the lessons artifact).
    lessons_rel = f"resolutions/{valid_run_id}-lessons.yaml"
    (temp_uacp_root / ".uacp" / "resolutions").mkdir(parents=True, exist_ok=True)
    (temp_uacp_root / ".uacp" / lessons_rel).write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.lessons",
                "run_id": valid_run_id,
                "lessons": [
                    {
                        "id": "L1",
                        "category": "process",
                        "finding": "Full lifecycle e2e run.",
                        "recommendation": "None.",
                        "applies_to_future_runs": False,
                    }
                ],
            },
            sort_keys=False,
        )
    )
    reg = json.loads(
        state_machine.handle_register_artifact(
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "artifact_type": "lessons",
                "path": lessons_rel,
            }
        )
    )
    assert reg.get("ok") is True, reg

    fin = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_finalize(a),
        {"workspace": str(temp_uacp_root), "run_id": valid_run_id},
        phase="verify",
    )
    assert fin.get("ok") is True and fin["status"] == "resolved", fin

    # Assert on the emitted TRAJECTORY, not file paths / config contents.
    manifest = yaml.safe_load(
        (temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml").read_text()
    )
    assert manifest["status"] == "resolved"
    assert manifest["current_phase"] == "resolved"
    assert manifest["finalized_at"] is not None
    transitions = [h for h in manifest["state_history"] if h["event"] == "phase_transition"]
    assert [(h["from_phase"], h["to_phase"]) for h in transitions] == PHASES

    ledger_lines = (
        (temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl")
        .read_text()
        .strip()
        .split("\n")
    )
    assert len(ledger_lines) == len(PHASES)

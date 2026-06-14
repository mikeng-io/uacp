"""E2E evidence-completeness tests: prove validate_evidence_completeness returns
ZERO violations on a run that left ALL required exit evidence, and that each kind
of missing evidence is CAUGHT (teeth).

NON-VACUITY: the conftest fixture's minimal ``config/phase-transitions.yaml``
declares NO ``phase_exit_invariants``, so against it a run trivially has zero
required evidence and the engine would pass vacuously. To make the positive test
MEANINGFUL we overwrite the workspace config with one that DOES declare required
``artifact_glob`` + ``gate_ledger_entry`` invariants per phase, AND seed the exact
artifacts those invariants require, so 0 violations means "every declared
obligation was actually satisfied". Each teeth test then removes exactly one
required piece of evidence and asserts the specific EV_ code fires (while the good
run did NOT fire it).

The invariants below are deliberately a subset/shape-faithful mirror of the REAL
config/phase-transitions.yaml (artifact_glob / gate_ledger_entry / required), with
globs/gates chosen to line up with what the happy-path run from test_coherence
actually emits (ledger gates TRIAGE->PROPOSE ... VERIFY->RESOLVED; seeded
proposal/plan packages; lessons under ``resolutions``). We additionally seed an
``executions/`` and ``verification/`` artifact so the execute/verify phases have a
single, cleanly-removable required artifact for the teeth tests.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from engines.base import Violation
from engines.evidence_completeness import validate_evidence_completeness

from tests.e2e.test_coherence import seed_coherent_run

# A phase-transitions config that declares REAL required exit evidence whose
# globs/gates match what seed_coherent_run + _seed_evidence produce on disk.
_EVIDENCE_CONFIG = """
stages:
  triage:
    exits_to: [propose]
    phase_exit_invariants:
    - artifact_glob: "proposals/{run_id}*-package-selection.yaml"
      required: true
    - gate_ledger_entry: "TRIAGE->PROPOSE"
      required: true
  propose:
    exits_to: [plan]
    phase_exit_invariants:
    - artifact_glob: "proposals/{run_id}*-package-selection.yaml"
      required: true
    - artifact_glob: "proposals/{run_id}*-adaptive.yaml"
      required: false
      applies_when: adaptive_proposal_package_selected
    - gate_ledger_entry: "PROPOSE->PLAN"
      required: true
  plan:
    exits_to: [execute]
    phase_exit_invariants:
    - artifact_glob: "plans/{run_id}*-scope.yaml"
      required: true
    - gate_ledger_entry: "PLAN->EXECUTE"
      required: true
  execute:
    exits_to: [verify]
    phase_exit_invariants:
    - artifact_glob: "executions/{run_id}*"
      required: true
    - gate_ledger_entry: "EXECUTE->VERIFY"
      required: true
  verify:
    exits_to: [resolved]
    phase_exit_invariants:
    - artifact_glob: "verification/{run_id}*"
      required: true
    - gate_ledger_entry: "VERIFY->RESOLVED"
      required: true
  resolve:
    exits_to: [terminal]
    phase_exit_invariants:
    - artifact_glob: "resolutions/{run_id}*"
      required: true
  resolved:
    exits_to: []
"""


def _write_evidence_config(root: Path) -> None:
    (root / "config" / "phase-transitions.yaml").write_text(_EVIDENCE_CONFIG)


def _seed_evidence(root: Path, run_id: str) -> None:
    """Seed the execute/verify exit artifacts that _EVIDENCE_CONFIG requires but
    the base happy-path run does not create (it only seeds proposal/plan packages
    + lessons)."""
    (root / ".uacp" / "executions").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / "verification").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / "executions" / f"{run_id}-execution.yaml").write_text(
        "kind: uacp.execution\nbody: stub\n"
    )
    (root / ".uacp" / "verification" / f"{run_id}-verification.yaml").write_text(
        "kind: uacp.verification\nbody: stub\n"
    )


def seed_complete_run(root: Path, run_id: str) -> None:
    """A genuinely-complete run: real happy-path lifecycle + every required exit
    artifact present + a config that DECLARES those requirements (non-vacuous)."""
    seed_coherent_run(root, run_id)
    _seed_evidence(root, run_id)
    _write_evidence_config(root)


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


# ---------------------------------------------------------------- positive test
def test_complete_run_has_zero_violations(temp_uacp_root: Path, valid_run_id: str):
    seed_complete_run(temp_uacp_root, valid_run_id)
    violations = validate_evidence_completeness(temp_uacp_root, valid_run_id)
    assert violations == [], (
        f"expected zero violations, got: {[(v.code, v.message) for v in violations]}"
    )
    assert all(isinstance(v, Violation) for v in violations)


def test_positive_is_non_vacuous(temp_uacp_root: Path, valid_run_id: str):
    """Guard against a vacuous pass: the config the run reads MUST actually declare
    enforceable required invariants, otherwise 0 violations proves nothing."""
    seed_complete_run(temp_uacp_root, valid_run_id)
    cfg = yaml.safe_load((temp_uacp_root / "config" / "phase-transitions.yaml").read_text())
    required = [
        inv
        for stage in cfg["stages"].values()
        if isinstance(stage, dict)
        for inv in (stage.get("phase_exit_invariants") or [])
        if isinstance(inv, dict) and inv.get("required") is True and "applies_when" not in inv
    ]
    # Several enforceable required invariants across both artifact_glob + ledger.
    assert len(required) >= 6, required
    assert any("artifact_glob" in i for i in required)
    assert any("gate_ledger_entry" in i for i in required)


# --------------------------------------------------- teeth: missing exit artifact
def test_missing_exit_artifact_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_complete_run(temp_uacp_root, valid_run_id)
    assert "EV_PHASE_EXIT_ARTIFACT_MISSING" not in _codes(
        validate_evidence_completeness(temp_uacp_root, valid_run_id)
    )

    # Remove the execute phase's required exit artifact (executions/{run_id}*).
    (temp_uacp_root / ".uacp" / "executions" / f"{valid_run_id}-execution.yaml").unlink()

    codes = _codes(validate_evidence_completeness(temp_uacp_root, valid_run_id))
    assert "EV_PHASE_EXIT_ARTIFACT_MISSING" in codes, codes


# ----------------------------------------------------- teeth: missing ledger entry
def test_missing_exit_ledger_entry_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_complete_run(temp_uacp_root, valid_run_id)
    assert "EV_PHASE_EXIT_LEDGER_MISSING" not in _codes(
        validate_evidence_completeness(temp_uacp_root, valid_run_id)
    )

    # Drop the EXECUTE->VERIFY gate line from the ledger (execute's required gate).
    ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
    kept = [
        ln
        for ln in ledger_path.read_text().splitlines()
        if ln.strip() and "EXECUTE->VERIFY" not in ln
    ]
    ledger_path.write_text("\n".join(kept) + "\n")

    codes = _codes(validate_evidence_completeness(temp_uacp_root, valid_run_id))
    assert "EV_PHASE_EXIT_LEDGER_MISSING" in codes, codes


# ----------------------------------------------- teeth: resolved without evidence
def test_resolved_without_closure_evidence_fires(temp_uacp_root: Path, valid_run_id: str):
    seed_complete_run(temp_uacp_root, valid_run_id)
    assert "EV_RESOLVED_WITHOUT_EVIDENCE" not in _codes(
        validate_evidence_completeness(temp_uacp_root, valid_run_id)
    )

    # status is 'resolved'; remove the resolve-phase required exit artifact
    # (resolutions/{run_id}* -> the lessons file) so the closure is self-attesting.
    (temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml").unlink()

    codes = _codes(validate_evidence_completeness(temp_uacp_root, valid_run_id))
    assert "EV_RESOLVED_WITHOUT_EVIDENCE" in codes, codes


# -------------------------------------------------- not-vacuous on minimal config
def test_minimal_config_yields_no_required_evidence(temp_uacp_root: Path, valid_run_id: str):
    """Honest limitation: against the conftest fixture's minimal config (which
    declares NO phase_exit_invariants), a complete run has no required evidence
    and the engine reports zero violations — it computes only against declared
    invariants and never invents requirements."""
    seed_coherent_run(temp_uacp_root, valid_run_id)  # NOTE: keeps the minimal config
    violations = validate_evidence_completeness(temp_uacp_root, valid_run_id)
    assert violations == [], [(v.code, v.message) for v in violations]


# --------------------------------------------------------- defensive: never raises
def test_never_raises_on_missing_run(temp_uacp_root: Path):
    out = validate_evidence_completeness(temp_uacp_root, "no-such-run")
    assert isinstance(out, list) and out
    assert out[0].code == "EV0_MANIFEST_MISSING"


def test_never_raises_on_garbled_manifest(temp_uacp_root: Path, valid_run_id: str):
    mpath = temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml"
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text("this: : : not valid yaml: [")
    out = validate_evidence_completeness(temp_uacp_root, valid_run_id)
    assert isinstance(out, list) and out

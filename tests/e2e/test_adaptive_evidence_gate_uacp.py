"""E2E regression for council finding C-A (CRITICAL).

C-A
---
Heartgate's active adaptive evidence gates (``_validate_adaptive_execute_evidence_gate``
and friends) call the offline validator ``scripts/validate_uacp_artifacts.py``
IN-PROCESS via ``Heartgate._offline_validate_artifacts``. After Slice 2 the
runtime artifacts moved under ``.uacp/`` (``config.base_dir(root)``), but the
validator used to resolve every artifact/state path under the FLAT project root.
On a migrated repo that fail-closed-BLOCKED real EXECUTE/VERIFY/RESOLVE
transitions: the in-process validator could not find ``.uacp/state/current.yaml``
nor the linked ``.uacp/`` artifacts, so it emitted "not found" / "state/current.yaml"
blockers for artifacts that actually exist.

The fix makes the validator ``.uacp/``-aware: config is read flat under ``root``
but all state/artifact paths resolve under ``base_dir(root)``. Heartgate keeps
passing the project root.

This test builds a ``.uacp/``-migrated tmp repo (real ``config/`` so the adaptive
gate + phase-transitions are present, the real validator script present under
``<root>/scripts/`` so the in-process path is actually exercised), seeds the
run's state + linked artifacts under ``.uacp/``, and drives the in-process
validator. It asserts NO validator-sourced path blocker fires.

NON-VACUITY
-----------
``test_flat_seeding_does_block`` seeds the same artifacts at the FLAT project
root (the pre-fix layout) and proves the validator THEN emits the path blockers.
This is the experiment that proves the positive test is not vacuously green:
the resolution genuinely moved from ``root`` to ``base_dir(root)``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from core import Heartgate

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_CONFIG = REPO_ROOT / "config"
REAL_VALIDATOR = REPO_ROOT / "scripts" / "validate_uacp_artifacts.py"

RUN_ID = "uacp-cae-001"
LABEL = "adaptive_execute_evidence_gate"

# Validator-sourced signatures that indicate a wrong-path / fail-closed block —
# precisely the C-A failure mode. None of these may appear for a correctly
# .uacp/-migrated run.
_PATH_BLOCKER_SIGNATURES = (
    "validator execution failed",
    "validator script missing",
    "not found",
    "state/current.yaml",
    "unreadable",
)


def _write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj), encoding="utf-8")


def _current_state(run_id: str) -> dict:
    manifest = f"state/runs/{run_id}-triage.yaml"
    transition = f"state/runs/{run_id}-execute.yaml"
    return {
        "schema_version": "0.2",
        "kind": "uacp.current_state",
        "active_run_id": run_id,
        "active_run_manifest": manifest,
        "mutation_policy": "uacp_state_required",
        "current_transition_artifact": transition,
        "kanban_binding_artifact": manifest,
        "kanban_board_slug": "uacp",
        "bootstrap_closed": True,
        "governed_mutation_active": True,
    }


def _piv(run_id: str) -> dict:
    return {
        "kind": "uacp.phase_intent_verification_contract",
        "phase": "plan",
        "run_id": run_id,
        "applies_to_phase": "execute",
        "phase_intent": {"summary": "verify the .uacp-aware validator resolves linked artifacts"},
        "work_units": [
            {
                "id": "wu-1",
                "intent": "ship the fix",
                "expected_outputs": ["validator patch"],
                "derives_from": ["si-1"],  # D43: work_units declare coverage of a scope_item
            }
        ],
        "evidence_obligations": [
            {
                "id": "ob-1",
                "work_unit_id": "wu-1",  # D43: links the obligation to its work_unit so the
                # manifest graph carries obligation_for(ob-1 -> wu-1) — needed by the forced
                # plan_exit obligation-coverage and verify_exit unverified checks once this PIV
                # is REGISTERED (Option B coverage binding).
                "required": True,
                "description": "patch lands",
                "evidence_type": "artifact",
                "sufficiency": "patch present and tests green",
            }
        ],
        "checkpoint_policy": {
            "required_checkpoints": ["after_each_work_unit"],
            "max_uncheckpointed_units": 1,
        },
        "intent_drift_conditions": [],
        "next_phase_handoff": {
            "required_artifacts": ["plans/x-piv.yaml"],
            "pass_condition": "evidence complete",
        },
    }


def _checkpoint(run_id: str) -> dict:
    # ``evidence`` references the PIV's required obligation with result=pass and a
    # run-bound artifact (the PIV itself) that exists under .uacp/.
    return {
        "kind": "uacp.execution_checkpoint",
        "phase": "execute",
        "run_id": run_id,
        "checkpoint_id": f"{run_id}-cp-001",
        "piv_contract": f"plans/{run_id}-piv.yaml",
        "checkpoint_type": "after_work_unit",
        "work_unit_id": "wu-1",
        "work_performed": {"summary": "did the work", "produced_outputs": ["patch"]},
        "decisions": [],
        "evidence": [
            {
                "obligation_id": "ob-1",
                "result": "pass",
                "artifact": f"plans/{run_id}-piv.yaml",
                "summary": "obligation satisfied",
            }
        ],
        "intent_drift": {"detected": False, "deviations": []},
        "invariants": {
            "authority_preserved": True,
            "write_boundary_preserved": True,
            "rollback_preserved": True,
            "privacy_boundary_preserved": True,
        },
        "next_phase_readiness": {"target_phase": "verify", "status": "ready"},
    }


# Each semantic-context file must be Markdown: >=240 chars, a heading in the
# first 200 chars, and must contain its required terms (lower-cased match).
_SEMANTIC_FILES = {
    "00-index.md": (
        "# Execution Package Index\n\n"
        "This package records the intent behind the work and the evidence produced for the "
        "EXECUTE to VERIFY handoff. It maps each work unit to its evidence and explains the "
        "intent that drove the run so that a future agent can reconstruct why the run exists, "
        "what it accomplished, and how every obligation was satisfied with concrete evidence.\n"
    ),
    "work-narrative.md": (
        "# Work Narrative\n\n"
        "The intent of this work was to make the in-process validator .uacp/-aware. We "
        "describe why the work was needed and how the work proceeded, unit by unit, so the "
        "narrative is recoverable later. This is the why behind the work and the path the "
        "work took from start to finish, including the reasoning at each step.\n"
    ),
    "decision-log.md": (
        "# Decision Log\n\n"
        "Each decision taken during EXECUTE is recorded here with its rationale, so the "
        "reasoning is auditable by any future reviewer. The key decision was to resolve "
        "artifacts under base_dir with a documented rationale for the change, and to keep "
        "config reads flat at the project root. Every decision carries its rationale.\n"
    ),
    "evidence-map.md": (
        "# Evidence Map\n\n"
        "This maps every obligation to the evidence that satisfies it and the verification "
        "performed against it. The evidence demonstrates the obligations were met and "
        "supports the verification handoff downstream, linking each obligation id to the "
        "artifact and the verification result that closes it out completely.\n"
    ),
    "intent-drift-and-deviations.md": (
        "# Intent Drift And Deviations\n\n"
        "No intent drift was detected during this run. Any deviation would be recorded here "
        "with its disposition and owner. The intent stayed aligned with the plan and no drift "
        "disposition was required for any deviation, so the intent and the executed work "
        "remained consistent throughout the entire run from start to end.\n"
    ),
    "verify-handoff.md": (
        "# Verify Handoff\n\n"
        "This section states the verify handoff readiness: the evidence is complete and the "
        "run is ready for verify. It declares readiness for the verify phase and what the "
        "handoff requires, so the VERIFY phase can consume the evidence and confirm the "
        "readiness without re-deriving the context from scratch.\n"
    ),
}


def _seed_governed_run(base: Path, run_id: str) -> None:
    """Seed a COMPLETE run + linked artifacts under a governed namespace root.

    ``base`` is where the validator expects the governed tree (``.uacp/`` in the
    positive case; the flat project root in the non-vacuity case).
    """
    # state/current.yaml + the run-bound manifest/transition artifacts it references
    _write_yaml(base / "state" / "current.yaml", _current_state(run_id))
    _write_yaml(
        base / "state" / "runs" / f"{run_id}-triage.yaml",
        {"kind": "uacp.run_manifest", "run_id": run_id},
    )
    _write_yaml(
        base / "state" / "runs" / f"{run_id}-execute.yaml",
        {"kind": "uacp.phase_transition", "run_id": run_id},
    )
    # linked EXECUTE-gate artifacts the offline validator cross-references
    _write_yaml(base / "plans" / f"{run_id}-piv.yaml", _piv(run_id))
    _write_yaml(base / "executions" / f"{run_id}-checkpoint-001.yaml", _checkpoint(run_id))
    # complete EXECUTE semantic package directory
    pkg = base / "executions" / run_id
    pkg.mkdir(parents=True, exist_ok=True)
    for name, body in _SEMANTIC_FILES.items():
        (pkg / name).write_text(body, encoding="utf-8")


def _make_migrated_repo(tmp_path: Path) -> Path:
    """A .uacp/-migrated tmp repo: real config/, real validator present, .uacp/ tree."""
    root = tmp_path / "repo"
    root.mkdir()
    # Real config so the adaptive gate + phase-transitions + evidence-clusters are present.
    shutil.copytree(REAL_CONFIG, root / "config")
    # Real validator present under <root>/scripts so the IN-PROCESS path is exercised
    # (Heartgate loads self.uacp_root / "scripts" / "validate_uacp_artifacts.py").
    (root / "scripts").mkdir()
    shutil.copy2(REAL_VALIDATOR, root / "scripts" / "validate_uacp_artifacts.py")
    # Governed namespace.
    (root / ".uacp").mkdir()
    return root


@pytest.fixture
def migrated_root(tmp_path: Path) -> Path:
    return _make_migrated_repo(tmp_path)


def _path_blockers(blockers: list[str]) -> list[str]:
    return [b for b in blockers if any(sig in b for sig in _PATH_BLOCKER_SIGNATURES)]


# ---------------------------------------------------------------------------
# POSITIVE: with the run seeded under .uacp/, the in-process validator resolves
# everything correctly and emits NO path/state blocker.
# ---------------------------------------------------------------------------
def test_offline_validator_resolves_under_uacp(migrated_root: Path):
    _seed_governed_run(migrated_root / ".uacp", RUN_ID)
    hg = Heartgate.load(migrated_root)

    # Sanity: the in-process path is genuinely reachable (validator script exists).
    assert (hg.uacp_root / "scripts" / "validate_uacp_artifacts.py").exists()

    blockers: list[str] = []
    hg._offline_validate_artifacts(
        [f"plans/{RUN_ID}-piv.yaml", f"executions/{RUN_ID}-checkpoint-001.yaml"],
        blockers,
        LABEL,
    )

    # With a complete run seeded under .uacp/, the in-process validator finds and
    # validates every cross-referenced artifact + state/current.yaml -> clean.
    assert not blockers, (
        "validator blocked a complete .uacp/-migrated run (C-A regression). "
        f"path-sourced blockers: {_path_blockers(blockers)}; all: {blockers}"
    )


# ---------------------------------------------------------------------------
# POSITIVE (end-to-end): drive a real EXECUTE->VERIFY transition through the
# ACTIVE adaptive execute evidence gate. The gate (selected via the real config's
# domains/risk predicate) calls _offline_validate_artifacts in-process. Assert the
# decision is not a validator-path BLOCK.
# ---------------------------------------------------------------------------
def test_adaptive_execute_gate_does_not_path_block(migrated_root: Path):
    _seed_governed_run(migrated_root / ".uacp", RUN_ID)
    hg = Heartgate.load(migrated_root)
    assert isinstance(hg.config.get("adaptive_execute_evidence_gate"), dict), (
        "real config must carry the adaptive_execute_evidence_gate for this test to mean anything"
    )

    blockers: list[str] = []
    hg._validate_adaptive_execute_evidence_gate(
        {"from_phase": "execute", "to_phase": "verify", "run_id": RUN_ID},
        blockers,
    )

    assert not blockers, (
        "active adaptive EXECUTE gate fail-closed-BLOCKED a complete migrated run via "
        f"the in-process validator (C-A regression): {blockers}"
    )


# ---------------------------------------------------------------------------
# NON-VACUITY: seed the SAME run at the FLAT project root (pre-Slice-2 layout).
# Because the fix moved resolution to base_dir(root), the validator now looks
# under .uacp/ — which is empty — so it MUST emit the path/state blockers. This
# proves the positive tests above are not vacuously green.
# ---------------------------------------------------------------------------
def test_flat_seeding_does_block(migrated_root: Path):
    # Seed at the flat root (NOT under .uacp/). .uacp/ stays empty.
    _seed_governed_run(migrated_root, RUN_ID)
    hg = Heartgate.load(migrated_root)

    blockers: list[str] = []
    hg._offline_validate_artifacts([f"plans/{RUN_ID}-piv.yaml"], blockers, LABEL)

    # The validator resolves under .uacp/ (empty), so state/current.yaml is missing
    # and the cross-refs are not found -> path blockers fire.
    assert _path_blockers(blockers), (
        "expected the validator to emit path/state blockers when the run is seeded "
        "FLAT (proves resolution moved to base_dir(root)); got none: " + repr(blockers)
    )

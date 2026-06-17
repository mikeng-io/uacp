"""Heartgate invariant integration test: brainstorm exit invariant is non-vacuous (T10)."""
from __future__ import annotations

import sys
from pathlib import Path


_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Heartgate
from engines.io import load_phase_transitions

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_heartgate(uacp_root: Path) -> Heartgate:
    """Construct Heartgate with the real signature: Heartgate(config, *, uacp_root=None).
    governed_root is derived internally as uacp_root/.uacp — do NOT pass governed_root=.

    Disables piv_rule.ledger_required so the test focuses on the brainstorm
    exit-invariant (scope-package glob) rather than PIV ledger presence.
    The piv_rule is a separate concern; its non-vacuousness is tested in
    test_gate_rules_model.py::test_piv_rule_fires_when_block_absent.
    """
    loaded = load_phase_transitions(REPO_ROOT)
    assert loaded.error is None
    config = dict(loaded.value or {})
    # Opt out of piv_rule enforcement for this test (mirrors the conftest fixture approach).
    config["piv_rule"] = {"ledger_required": False}
    return Heartgate(config, uacp_root=uacp_root)


def _minimal_brainstorm_triage_artifact(run_id: str) -> dict:
    """Minimal valid brainstorm->triage transition artifact."""
    return {
        "transition_id": f"{run_id}-brainstorm-triage",
        "run_id": run_id,
        "from_phase": "brainstorm",
        "to_phase": "triage",
        "decision": "pass",
        "invariant_summary": [],
        "cluster_summary": [],
        "blockers": [],
        "warnings": [],
        "deferred_items": [],
        "authority": {"source": "operator-request"},
        "artifact_paths": [],
        "phase_local_granularity": 5,
        "composite_granularity": 5,
        "human_involvement": {"required": False},
    }


def test_brainstorm_exit_passes_when_scope_package_present(tmp_path: Path) -> None:
    """brainstorm->triage PASSES when the scope-package artifact exists."""
    # governed_root = tmp_path/.uacp; artifact lives at governed_root/brainstorm/<session>/07-scope-package.yaml
    session_id = "test-session-001"
    scope_pkg_dir = tmp_path / ".uacp" / "brainstorm" / session_id
    scope_pkg_dir.mkdir(parents=True)
    scope_pkg_path = scope_pkg_dir / "07-scope-package.yaml"
    scope_pkg_path.write_text("kind: uacp.brainstorm_scope_package\n", encoding="utf-8")

    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-pass-001")
    decision = hg.validate_transition(artifact)

    assert decision.decision != "block", (
        f"Expected PASS or WARN, got BLOCK. blockers={decision.blockers}"
    )


def test_brainstorm_exit_blocks_when_scope_package_missing(tmp_path: Path) -> None:
    """brainstorm->triage BLOCKS when no scope-package artifact exists."""
    # Do NOT create .uacp/brainstorm/*/07-scope-package.yaml
    (tmp_path / ".uacp").mkdir()

    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-block-001")
    decision = hg.validate_transition(artifact)

    assert decision.decision == "block", (
        f"Expected BLOCK (no scope-package), got {decision.decision}. "
        f"blockers={decision.blockers}"
    )
    assert any("07-scope-package.yaml" in b for b in decision.blockers), (
        f"Expected blocker mentioning scope-package path. blockers={decision.blockers}"
    )


def test_illegal_transition_blocked_by_heartgate(tmp_path: Path) -> None:
    """brainstorm->plan is rejected as a disallowed transition by Heartgate."""
    (tmp_path / ".uacp").mkdir()
    hg = _make_heartgate(tmp_path)
    artifact = _minimal_brainstorm_triage_artifact("bs-hg-illegal-001")
    artifact["from_phase"] = "brainstorm"
    artifact["to_phase"] = "plan"
    decision = hg.validate_transition(artifact)
    assert decision.decision == "block"
    assert any("not allowed" in b for b in decision.blockers)

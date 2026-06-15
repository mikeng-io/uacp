"""Regression for F-T3-01 (SECURITY): adaptive evidence gates fail CLOSED.

F-T3-01
-------
Three Heartgate adaptive-evidence gates used to SELF-DISABLE when their config
key was absent/empty::

    if not isinstance(self.config.get("adaptive_execute_evidence_gate"), Mapping):
        return

This is fail-OPEN: a missing/misconfigured ``adaptive_*_evidence_gate`` key
silently turned OFF enforcement of the EXECUTE/VERIFY/RESOLVE evidence
obligations. The fix removes the self-disable so each gate ENFORCES whenever its
phase-guard matches, regardless of whether the config key is present.

These tests pin the fail-CLOSED behavior: with the gate's config key ABSENT (the
``temp_uacp_root`` fixture's phase-transitions.yaml defines NONE of the three
adaptive_*_evidence_gate keys) and the required evidence NOT seeded, the gate
MUST emit its gate-specific blockers rather than passing silently.

Before the fix these tests FAIL (the gates return early -> no blockers). After
the fix they pass.

The gate bodies read NOTHING from the config block beyond the (removed)
presence check — they enforce structure using hardcoded relative artifact paths
— so flipping to fail-closed does not change behavior when the key IS present
(see test_full_lifecycle + test_adaptive_evidence_gate_uacp for the present-key
happy paths).
"""

from __future__ import annotations

from pathlib import Path

from core import Heartgate


def _gate_blockers(blockers: list[str], label: str) -> list[str]:
    return [b for b in blockers if label in b]


def test_execute_gate_fails_closed_on_absent_config(
    temp_uacp_root: Path, valid_run_id: str
):
    """execute->verify: config key absent + no PIV/checkpoint seeded -> BLOCKS.

    Driven through the public validate_transition (the fixture graph allows
    execute->verify, so there is no graph blocker to mask the result) — the gate
    is the only thing that can block this transition, proving fail-closed end to
    end.
    """
    hg = Heartgate.load(str(temp_uacp_root))
    assert hg.config.get("adaptive_execute_evidence_gate") is None, (
        "fixture must omit the gate config key for this regression to mean anything"
    )

    decision = hg.validate_transition(
        {
            "from_phase": "execute",
            "to_phase": "verify",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        }
    )

    assert decision.decision == "block", (
        "execute->verify with absent config + no evidence must FAIL CLOSED "
        f"(F-T3-01); got {decision.decision}: {decision.blockers}"
    )
    assert _gate_blockers(decision.blockers, "adaptive_execute_evidence_gate"), (
        "expected an adaptive_execute_evidence_gate blocker proving the gate "
        f"enforced (did not self-disable); got: {decision.blockers}"
    )


def test_verify_gate_fails_closed_on_absent_config(
    temp_uacp_root: Path, valid_run_id: str
):
    """verify->resolve: config key absent + no evidence -> gate emits blockers.

    Invoked directly (the fixture graph uses verify->resolved, so
    validate_transition would add a graph blocker for verify->resolve); the
    direct call isolates the OBSERVABLE gate behavior.
    """
    hg = Heartgate.load(str(temp_uacp_root))
    assert hg.config.get("adaptive_verify_evidence_gate") is None

    blockers: list[str] = []
    hg._validate_adaptive_verify_evidence_gate(
        {"from_phase": "verify", "to_phase": "resolve", "run_id": valid_run_id},
        blockers,
    )

    assert _gate_blockers(blockers, "adaptive_verify_evidence_gate"), (
        "verify->resolve gate must enforce (fail closed) on absent config "
        f"(F-T3-01); got: {blockers}"
    )


def test_resolve_gate_fails_closed_on_absent_config(
    temp_uacp_root: Path, valid_run_id: str
):
    """resolve->*: config key absent + no evidence -> gate emits blockers."""
    hg = Heartgate.load(str(temp_uacp_root))
    assert hg.config.get("adaptive_resolve_closure_gate") is None

    blockers: list[str] = []
    hg._validate_adaptive_resolve_closure_gate(
        {"from_phase": "resolve", "to_phase": "resolved", "run_id": valid_run_id},
        blockers,
    )

    assert _gate_blockers(blockers, "adaptive_resolve_closure_gate"), (
        "resolve closure gate must enforce (fail closed) on absent config "
        f"(F-T3-01); got: {blockers}"
    )

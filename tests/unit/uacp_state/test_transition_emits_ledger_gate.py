"""BREAK-3 teeth: the governed transition tool EMITS the canonical gate-ledger
record so the operator is not required to hand-mirror it (and cannot drift it
from state_history).

``handle_transition`` appends, atomically with the phase mutation, the canonical
``FROM->TO`` gate (plus ``TRIAGE_COMPLETE`` on triage exit) — exactly the ledger
entries the closure sweep (evidence_completeness + coherence C2) requires. The
emission is IDEMPOTENT: a gate already present in the ledger (e.g. an operator's
hand-authored ``uacp_gate_ledger_append``) is not duplicated, so back-compat runs
that DO hand-author the gate coexist without a spurious duplicate (which coherence
C2 would otherwise flag — the duplicate-detection tooth in test_coherence stays
intact precisely because no duplicate is ever created).
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
from state import _handle_uacp_gate_ledger_append


def _init(root: Path, run_id: str) -> None:
    out = json.loads(
        state_machine.handle_init(
            {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
        )
    )
    assert out.get("ok") is True, out


def _transition(root: Path, run_id: str, frm: str, to: str) -> dict:
    return json.loads(
        state_machine.handle_transition(
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
        )
    )


def _ledger_gates(root: Path, run_id: str) -> list[str]:
    path = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln)["gate"] for ln in path.read_text().splitlines() if ln.strip()]


def test_triage_exit_emits_transition_gate_and_triage_complete(
    temp_uacp_root: Path, valid_run_id: str
):
    _init(temp_uacp_root, valid_run_id)
    out = _transition(temp_uacp_root, valid_run_id, "triage", "propose")
    assert out.get("ok") is True, out

    gates = _ledger_gates(temp_uacp_root, valid_run_id)
    assert gates.count("TRIAGE->PROPOSE") == 1, gates
    assert gates.count("TRIAGE_COMPLETE") == 1, gates


def test_non_triage_exit_emits_only_transition_gate(temp_uacp_root: Path, valid_run_id: str):
    _init(temp_uacp_root, valid_run_id)
    assert _transition(temp_uacp_root, valid_run_id, "triage", "propose").get("ok")
    assert _transition(temp_uacp_root, valid_run_id, "propose", "plan").get("ok")

    gates = _ledger_gates(temp_uacp_root, valid_run_id)
    assert gates.count("PROPOSE->PLAN") == 1, gates
    # TRIAGE_COMPLETE is emitted only on triage exit, not on later edges.
    assert gates.count("TRIAGE_COMPLETE") == 1, gates


def test_emission_is_idempotent_with_hand_authored_gate(
    temp_uacp_root: Path, valid_run_id: str
):
    """An operator that hand-authors the canonical gate BEFORE transitioning must
    not end up with a duplicate (which coherence C2 would flag)."""
    _init(temp_uacp_root, valid_run_id)
    # Hand-author the transition gate first (the pre-F3 operator contract).
    ha = json.loads(
        _handle_uacp_gate_ledger_append(
            {
                "uacp_run_id": valid_run_id,
                "uacp_phase": "triage",
                "workspace": str(temp_uacp_root),
                "policy_version": "0.1",
                "declared_side_effects": [],
                "gate": "TRIAGE->PROPOSE",
                "record": {"result": "pass"},
                "authority_artifact": "plans/test.yaml",
            }
        )
    )
    assert ha.get("ok") is True, ha

    assert _transition(temp_uacp_root, valid_run_id, "triage", "propose").get("ok")

    gates = _ledger_gates(temp_uacp_root, valid_run_id)
    assert gates.count("TRIAGE->PROPOSE") == 1, f"duplicate transition gate emitted: {gates}"
    assert gates.count("TRIAGE_COMPLETE") == 1, gates

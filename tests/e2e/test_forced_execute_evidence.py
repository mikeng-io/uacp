"""E2E (force-gate follow-on): the forced EXECUTE->VERIFY PIV precondition.

Extends the "force one ripple-free precondition" pattern (cf. forced_proposal_coverage) to the
EXECUTE exit: a governed standard-track execute (checkpoint-001 registered) must carry a PIV before
EXECUTE->VERIFY, forced on ``state_machine.handle_transition`` — not only the agent-invoked
``validate_transition``. Self-gated on the governed-execute marker (no ripple on bare transitions);
goal-driven runs are relaxed to the coherent checkpoint manifest.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from core import Heartgate
from state_machine import _run_forced_execute_evidence_gate, handle_init


def _init(root: Path, run_id: str) -> None:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})


def _write(root: Path, rel: str, doc) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _blockers(root: Path, run_id: str) -> list[str]:
    return Heartgate.load(str(root)).forced_execute_evidence_blockers(run_id)


def _seed_checkpoint(root: Path, run_id: str) -> None:
    # the governed-execute marker the forced precondition self-gates on (standard-track checkpoint).
    _write(root, f"executions/{run_id}-checkpoint-001.yaml", {"kind": "uacp.execution_checkpoint"})


def test_bare_execute_without_checkpoint_skips(temp_uacp_root: Path):
    # self-gate: no governed-execute marker -> bare/ungoverned EXECUTE->VERIFY -> no ripple.
    _init(temp_uacp_root, "r")
    assert _blockers(temp_uacp_root, "r") == []


def test_governed_execute_without_piv_blocks(temp_uacp_root: Path):
    # checkpoint registered but NO PIV -> the bypass the forced execute_exit coverage gate misses.
    _init(temp_uacp_root, "r")
    _seed_checkpoint(temp_uacp_root, "r")
    blockers = _blockers(temp_uacp_root, "r")
    assert blockers and any("PIV" in b for b in blockers), blockers


def test_governed_execute_with_piv_passes(temp_uacp_root: Path):
    _init(temp_uacp_root, "r")
    _seed_checkpoint(temp_uacp_root, "r")
    _write(temp_uacp_root, "plans/r-piv.yaml", {"kind": "uacp.phase_intent_verification"})
    assert _blockers(temp_uacp_root, "r") == []


def test_unparseable_piv_blocks(temp_uacp_root: Path):
    # fail-closed: a present-but-non-mapping PIV does not satisfy the precondition.
    _init(temp_uacp_root, "r")
    _seed_checkpoint(temp_uacp_root, "r")
    _write(temp_uacp_root, "plans/r-piv.yaml", ["not", "a", "mapping"])
    blockers = _blockers(temp_uacp_root, "r")
    assert blockers and any("parse as a mapping" in b for b in blockers), blockers


def test_goal_driven_run_is_relaxed_to_manifest_not_piv(temp_uacp_root: Path):
    # track relaxation (ADR-0016): a goal-driven run is satisfied by a coherent checkpoint manifest
    # in lieu of the PIV — it must NOT be held to the standard PIV demand. (It may still block on
    # manifest coherence via the delegated goal-driven gate, but never with the PIV message.)
    handle_init({"workspace": str(temp_uacp_root), "run_id": "g", "source": "operator-request",
                 "track": "goal-driven"})
    _seed_checkpoint(temp_uacp_root, "g")
    blockers = _blockers(temp_uacp_root, "g")
    assert not any("a PIV (" in b for b in blockers), blockers


def test_forced_runner_only_fires_at_execute_exit(temp_uacp_root: Path):
    # the state-machine runner self-gates by phase: it is a no-op for non-execute exits even when a
    # checkpoint+no-PIV state exists (only EXECUTE->VERIFY carries this precondition).
    _init(temp_uacp_root, "r")
    _seed_checkpoint(temp_uacp_root, "r")
    assert _run_forced_execute_evidence_gate(temp_uacp_root, "r", "verify") == []
    assert _run_forced_execute_evidence_gate(temp_uacp_root, "r", "plan") == []
    assert _run_forced_execute_evidence_gate(temp_uacp_root, "r", "execute")  # fires here (no PIV)

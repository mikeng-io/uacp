"""BREAK-2 teeth: the evidence-disposition VERIFY evidence path is both writeable
and gated on the REAL governed edge.

Before the fix:
  * ``uacp_entity_write`` (``create_entity``) REFUSED the ``verified-facts`` half —
    the entity-writer's ctx sanitizer rejects any value containing ``-``, so only
    one of the two required halves was producible (the documented deadlock);
  * the disposition gate keyed on ``verify->resolve`` while the governed transition
    records ``verify->resolved``, so it silently skipped the real edge.

After the fix:
  * BOTH halves ("verified-facts", "assumptions") write cleanly;
  * an out-of-vocabulary half (the old paper doc's "left"/"right") is REJECTED;
  * the gate FIRES on ``verify->resolved`` (catches a missing verified-facts half),
    and no longer on the phantom ``verify->resolve`` edge.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
from core import Heartgate
from engines.manifest.entity_writer import create_entity


def _init_run(root: Path, run_id: str) -> None:
    """Seed a run manifest so create_entity's REGISTER step succeeds — otherwise a
    write would fail on the missing manifest and mask the sanitizer/vocabulary
    behavior these teeth isolate."""
    out = json.loads(
        state_machine.handle_init(
            {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
        )
    )
    assert out.get("ok") is True, out


# --------------------------------------------------------------- (a) writeability
def test_both_disposition_halves_write_cleanly(temp_uacp_root: Path, valid_run_id: str):
    _init_run(temp_uacp_root, valid_run_id)
    for half in ("verified-facts", "assumptions"):
        out = create_entity(
            str(temp_uacp_root),
            valid_run_id,
            "uacp.evidence_disposition",
            {"body": f"# {half}\n\nrow\n"},
            cluster="scope",
            half=half,
        )
        assert out.get("ok") is True, (half, out)
        assert out["path"] == f"verification/{valid_run_id}-scope-{half}.md", out
        assert (temp_uacp_root / ".uacp" / out["path"]).is_file()


def test_out_of_vocabulary_half_is_rejected(temp_uacp_root: Path, valid_run_id: str):
    """The half vocabulary is CLOSED (verified-facts | assumptions). The old paper
    doc's ``left``/``right`` (and any typo) must be refused — not silently written
    to a file nothing reads."""
    _init_run(temp_uacp_root, valid_run_id)
    for bad in ("left", "right", "facts"):
        out = create_entity(
            str(temp_uacp_root),
            valid_run_id,
            "uacp.evidence_disposition",
            {"body": "# x\n"},
            cluster="scope",
            half=bad,
        )
        assert "error" in out, (bad, out)


# --------------------------------------------------------------- (b) gate has teeth
def _disposition_blockers(root: Path, run_id: str, to_phase: str) -> list[str]:
    """Invoke the disposition validator DIRECTLY (the repo idiom for edge-schism
    gates; the full agent path's transition-allowed graph uses the lifecycle
    vocabulary and would mask the gate's own observable behavior)."""
    hg = Heartgate.load(str(root))
    blockers: list[str] = []
    hg._validate_evidence_dispositions(
        {
            "from_phase": "verify",
            "to_phase": to_phase,
            "run_id": run_id,
            "cluster_summary": [{"cluster_id": "scope", "state": "pass"}],
        },
        blockers,
    )
    return blockers


def test_gate_fires_on_governed_resolved_edge(temp_uacp_root: Path, valid_run_id: str):
    """On the REAL governed edge (verify->resolved) with a real cluster and the
    verified-facts half ABSENT, the gate BLOCKS — proving it has teeth on the edge
    the state machine actually records."""
    blockers = _disposition_blockers(temp_uacp_root, valid_run_id, "resolved")
    assert any("verified-facts" in b for b in blockers), blockers


def test_gate_does_not_fire_on_phantom_resolve_edge(temp_uacp_root: Path, valid_run_id: str):
    """The lifecycle-vocabulary ``verify->resolve`` is NOT the governed edge; the
    gate must key on the state-machine edge, so it does not fire here."""
    blockers = _disposition_blockers(temp_uacp_root, valid_run_id, "resolve")
    assert blockers == [], blockers

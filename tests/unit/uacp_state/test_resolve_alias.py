"""TDD tests for #114: the resolve/resolved schism — accept `verify -> resolve` as an
alias for the projected `verify -> resolved`.

Docs/skills/config `allowed_transitions`/the agent-path all speak the lifecycle phase
name `resolve`; the state-machine projection collapses that phase into the `resolved`
STATUS, so the governed `VALID_TRANSITIONS` only lists `resolved`. An agent following
the docs and driving `verify -> resolve` was rejected. This aliases the INPUT only —
the recorded/canonical edge stays VERIFY->RESOLVED.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from engines.domain.phase_graph import canonical_transition_target
from state_machine import Authority, RunManifest, _save_manifest, handle_transition


def _seed_at_verify(root: Path, run_id: str) -> None:
    _save_manifest(
        root,
        RunManifest(
            run_id=run_id,
            authority=Authority(source="operator-request"),
            track="standard",
            current_phase="verify",
        ),
    )


def _manifest(root: Path, run_id: str) -> dict:
    return yaml.safe_load(
        (root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )


def _transition(root: Path, run_id: str, frm: str, to: str) -> dict:
    return json.loads(
        handle_transition(
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
        )
    )


# --------------------------------------------------------------- the canonicalizer
def test_canonical_transition_target_aliases_resolve_only():
    assert canonical_transition_target("resolve") == "resolved"
    # Every other target passes through unchanged (no accidental rewrites).
    for p in ("resolved", "triage", "propose", "plan", "execute", "verify", "brainstorm"):
        assert canonical_transition_target(p) == p


# --------------------------------------------------------------- the #114 fix
def test_verify_to_resolve_is_accepted_not_rejected(temp_uacp_root: Path):
    """The exact #114 symptom: `verify -> resolve` must NOT be rejected with
    'transition not allowed ... (allowed: ['resolved'])'."""
    root = temp_uacp_root
    _seed_at_verify(root, "run-r")
    out = _transition(root, "run-r", "verify", "resolve")
    assert "transition not allowed" not in out.get("error", ""), out


def test_verify_to_resolve_records_canonical_resolved(temp_uacp_root: Path):
    """When the alias transition succeeds it records the CANONICAL 'resolved' — the
    state machine's internal vocabulary — so coherence/ledger stay consistent."""
    root = temp_uacp_root
    _seed_at_verify(root, "run-r")
    out = _transition(root, "run-r", "verify", "resolve")
    assert out.get("ok") is True, out
    assert out["to_phase"] == "resolved"  # aliased, not echoed back as 'resolve'
    m = _manifest(root, "run-r")
    assert m["current_phase"] == "resolved"
    assert m["status"] == "resolved"
    # The history edge + auto-emitted ledger gate use the canonical VERIFY->RESOLVED.
    edges = [(h["from_phase"], h["to_phase"]) for h in m["state_history"]]
    assert ("verify", "resolved") in edges
    ledger = (root / ".uacp" / "state" / "gate-ledger" / "run-r.jsonl").read_text()
    assert "VERIFY->RESOLVED" in ledger


def test_verify_resolve_and_verify_resolved_are_equivalent(temp_uacp_root: Path):
    """The alias is transparent: driving 'resolve' and 'resolved' from verify produce
    identical outcomes (a twin comparison — no divergence)."""
    root = temp_uacp_root
    _seed_at_verify(root, "twin-a")
    _seed_at_verify(root, "twin-b")
    a = _transition(root, "twin-a", "verify", "resolve")
    b = _transition(root, "twin-b", "verify", "resolved")
    assert a.get("ok") == b.get("ok")
    assert _manifest(root, "twin-a")["current_phase"] == _manifest(root, "twin-b")["current_phase"]
    assert _manifest(root, "twin-a")["status"] == _manifest(root, "twin-b")["status"]


# --------------------------------------------------------------- non-regression
def test_alias_does_not_make_triage_to_resolve_valid(temp_uacp_root: Path):
    """The alias canonicalizes 'resolve'->'resolved'; it must NOT open an illegal edge.
    triage -> resolve becomes triage -> resolved, which is still not an allowed edge."""
    root = temp_uacp_root
    _save_manifest(
        root,
        RunManifest(
            run_id="run-t",
            authority=Authority(source="operator-request"),
            track="standard",
            current_phase="triage",
        ),
    )
    out = _transition(root, "run-t", "triage", "resolve")
    assert "error" in out
    assert "transition not allowed" in out["error"]
    assert "resolved" in out["error"]  # canonicalized in the message too


def test_verify_to_resolved_still_works(temp_uacp_root: Path):
    """Backward compatibility: the canonical 'resolved' target is unaffected."""
    root = temp_uacp_root
    _seed_at_verify(root, "run-c")
    out = _transition(root, "run-c", "verify", "resolved")
    assert out.get("ok") is True, out
    assert _manifest(root, "run-c")["current_phase"] == "resolved"

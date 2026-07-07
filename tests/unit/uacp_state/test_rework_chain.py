"""TDD tests for #109: standard-track rework chaining (`reworks`).

Per ADR-0016 P2, a VERIFY-found defect is reworked by a NEW FORWARD RUN — NOT a
`verify->execute` back-edge. `reworks=<parent>` is the standard-track findings->fix
loop: the rework run RE-AUTHORS its own upstream and drives the lifecycle forward
normally; only a provenance link, the parent's carried VERIFY findings, and a VISIBLE
rework_depth cross the chain boundary. It is distinct from the goal-driven rewind
(`inherits_from`+`goal_id`).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from engines.domain import phase_graph
from state_machine import (
    Authority,
    RunManifest,
    _save_manifest,
    handle_init,
    handle_read,
)

LIFECYCLE_GRAPH = phase_graph.LIFECYCLE_GRAPH


def _seed_parent_at_verify(workspace: Path, run_id: str, *, rework_depth: int = 0) -> RunManifest:
    """A parent run that reached VERIFY with reusable prior-phase outputs AND verify
    findings registered."""
    manifest = RunManifest(
        run_id=run_id,
        authority=Authority(source="operator-request"),
        track="standard",
        current_phase="verify",
        rework_depth=rework_depth,
        # Keys match what the STANDARD verify flow actually registers (Codex #134):
        # verification_package / resolve_readiness / assessment — NOT the schema-KIND names.
        artifacts={
            "triage": f"proposals/{run_id}-triage.yaml",
            "proposal": f"proposals/{run_id}.yaml",
            "plan": f"plans/{run_id}.yaml",
            "execution_checkpoint": f"executions/{run_id}-checkpoint-001.yaml",
            "verification_package": f"verification/{run_id}-verify-selection.yaml",
            "resolve_readiness": f"verification/{run_id}-resolve-readiness.yaml",
            "assessment": f"verification/{run_id}-piv-assessment.yaml",
        },
    )
    _save_manifest(workspace, manifest)
    return manifest


def _init_rework(root: Path, run_id: str, parent: str, **extra) -> dict:
    args = {
        "workspace": str(root),
        "run_id": run_id,
        "source": "operator-request",
        "reworks": parent,
    }
    args.update(extra)
    return json.loads(handle_init(args))


def _manifest(root: Path, run_id: str) -> dict:
    return yaml.safe_load(
        (root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )


# --------------------------------------------------------------- carry semantics
def test_rework_records_provenance_and_carries_findings(temp_uacp_root: Path):
    """The rework run RE-AUTHORS its own upstream (so inherits_from / inherited_artifacts
    stay empty); only the provenance link, carried findings, and visible depth cross
    the chain boundary."""
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    out = _init_rework(root, "run-B", "run-A")
    assert out.get("ok") is True, out
    assert out["rework_depth"] == 1
    assert out["reworks"] == "run-A"

    m = _manifest(root, "run-B")
    assert m["track"] == "standard"
    assert m["reworks"] == "run-A"  # provenance link to the parent
    assert m["rework_depth"] == 1
    # Re-author model: NO gate-level reuse — the rework drives its own upstream.
    assert m["inherits_from"] is None
    assert m["inherited_artifacts"] == {}
    # Carried findings = PARENT-RELATIVE references to the parent's VERIFY artifacts
    # (the defects the rework should address), recorded on the manifest — keyed by the
    # REAL artifact_type keys the standard verify flow registers.
    assert m["carried_findings"] == {
        "verification_package": "verification/run-A-verify-selection.yaml",
        "resolve_readiness": "verification/run-A-resolve-readiness.yaml",
        "assessment": "verification/run-A-piv-assessment.yaml",
    }
    # A rework run's own execution state starts clean.
    assert m["artifacts"] == {}
    assert m["state_history"] == []


def test_rework_depth_increments_along_the_chain(temp_uacp_root: Path):
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    b = _init_rework(root, "run-B", "run-A")
    assert b["rework_depth"] == 1
    # run-B fails verify too; make it a verify-stage parent carrying its depth.
    _seed_parent_at_verify(root, "run-B2", rework_depth=1)
    c = _init_rework(root, "run-C", "run-B2")
    assert c["rework_depth"] == 2
    assert _manifest(root, "run-C")["rework_depth"] == 2


def test_rework_depth_is_visible_bound(temp_uacp_root: Path):
    """The #109 bound: an escalating rework_depth is VISIBLE (manifest + response),
    not silently looping — and not hard-blocked."""
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A", rework_depth=4)
    out = _init_rework(root, "run-B", "run-A")
    assert out.get("ok") is True  # not blocked
    assert out["rework_depth"] == 5  # but the depth is surfaced/escalating


# --------------------------------------------------------------- distinctness / guards
def test_rework_and_goal_id_mutually_exclusive(temp_uacp_root: Path):
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    out = _init_rework(root, "run-B", "run-A", goal_id="g1", track="goal-driven")
    assert "error" in out
    assert "mutually exclusive" in out["error"]


def test_rework_requires_standard_track(temp_uacp_root: Path):
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    out = _init_rework(root, "run-B", "run-A", track="goal-driven")
    assert "error" in out
    assert "track='standard'" in out["error"]


def test_rework_conflicting_inherits_from_rejected(temp_uacp_root: Path):
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    _seed_parent_at_verify(root, "run-X")
    out = _init_rework(root, "run-B", "run-A", inherits_from="run-X")
    assert "error" in out
    assert "mutually exclusive" in out["error"]


def test_rework_missing_parent_fails_closed(temp_uacp_root: Path):
    root = temp_uacp_root
    out = _init_rework(root, "run-B", "does-not-exist")
    assert "error" in out
    assert "not found" in out["error"]


def test_rework_self_reference_rejected(temp_uacp_root: Path):
    # A fresh run cannot name itself as the parent it reworks.
    root = temp_uacp_root
    out = _init_rework(root, "run-self", "run-self")
    assert "error" in out
    assert "cannot rework itself" in out["error"]


def test_rework_unsafe_parent_id_rejected(temp_uacp_root: Path):
    root = temp_uacp_root
    for bad in ("../../../etc/passwd", "sub/run-A"):
        out = _init_rework(root, "run-B", bad)
        assert "error" in out and "unsafe parent run_id" in out["error"], (bad, out)


def test_rework_empty_parent_id_rejected(temp_uacp_root: Path):
    """A fat-fingered empty reworks must error, not silently become a fresh run."""
    root = temp_uacp_root
    out = json.loads(
        handle_init(
            {
                "workspace": str(root),
                "run_id": "run-B",
                "source": "operator-request",
                "reworks": "   ",
            }
        )
    )
    assert "error" in out
    assert "empty" in out["error"]


def test_rework_requires_standard_track_parent(temp_uacp_root: Path):
    """M4: keep the loops distinct — a standard rework cannot rework a goal-driven parent."""
    root = temp_uacp_root
    parent = RunManifest(
        run_id="gd-parent",
        authority=Authority(source="operator-request"),
        track="goal-driven",
        goal_id="g1",
        current_phase="verify",
        artifacts={"verification": "verification/gd-parent-package.yaml"},
    )
    _save_manifest(root, parent)
    out = _init_rework(root, "run-B", "gd-parent")
    assert "error" in out
    assert "not standard" in out["error"]


def test_carried_findings_readable_via_run_read(temp_uacp_root: Path):
    """carried_findings is not inert: it is serialized manifest state surfaced by the
    governed run-read, so a rework agent has a governed way to see the defects
    (enforcement that it addresses them is a follow-up)."""
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    _init_rework(root, "run-B", "run-A")
    read = json.loads(handle_read({"workspace": str(root), "run_id": "run-B"}))
    assert read.get("ok") is True, read
    m = read["manifest"]
    assert m["reworks"] == "run-A"
    assert m["rework_depth"] == 1
    assert m["carried_findings"] == {
        "verification_package": "verification/run-A-verify-selection.yaml",
        "resolve_readiness": "verification/run-A-resolve-readiness.yaml",
        "assessment": "verification/run-A-piv-assessment.yaml",
    }


def test_standard_run_without_reworks_is_unaffected(temp_uacp_root: Path):
    """No reworks => rework_depth 0, no carried findings, no response noise."""
    root = temp_uacp_root
    out = json.loads(
        handle_init({"workspace": str(root), "run_id": "run-plain", "source": "operator-request"})
    )
    assert out.get("ok") is True
    assert "rework_depth" not in out  # only surfaced for rework runs
    m = _manifest(root, "run-plain")
    assert m["rework_depth"] == 0
    assert m["carried_findings"] == {}
    assert m["inherits_from"] is None


# --------------------------------------------------------------- ADR-0016 P2 invariant
def test_no_verify_to_execute_backedge_in_the_graph(temp_uacp_root: Path):
    """The load-bearing invariant of option B: rework adds NO phase-graph back-edge.
    The lifecycle graph stays a forward DAG (verify only exits to resolve)."""
    assert LIFECYCLE_GRAPH["verify"] == {"resolve"}
    assert "execute" not in LIFECYCLE_GRAPH["verify"]
    # No phase points back to an earlier phase.
    order = ["brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve"]
    rank = {p: i for i, p in enumerate(order)}
    for src, targets in LIFECYCLE_GRAPH.items():
        for dst in targets:
            if dst == "terminal":
                continue
            assert rank[dst] > rank[src], f"back-edge {src}->{dst} would violate ADR-0016 P2"

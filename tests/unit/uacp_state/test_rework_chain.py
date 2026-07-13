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


def test_rework_rejected_when_parent_has_no_verify_findings(temp_uacp_root: Path):
    """Codex #134: a rework must have defects to fix — a parent that hasn't registered
    any VERIFY findings (e.g. still at plan) is rejected, not silently carried empty."""
    root = temp_uacp_root
    parent = RunManifest(
        run_id="pre-verify",
        authority=Authority(source="operator-request"),
        track="standard",
        current_phase="plan",
        artifacts={"triage": "proposals/pre-verify-triage.yaml", "plan": "plans/pre-verify.yaml"},
    )
    _save_manifest(root, parent)
    out = _init_rework(root, "run-B", "pre-verify")
    assert "error" in out
    assert "no registered VERIFY findings" in out["error"]


def test_rework_carries_composite_investigation_entry_key(temp_uacp_root: Path):
    """Typed uacp.investigation_entry registers as 'investigation_entry' or a composite
    'investigation_entry:seq=1' — both must be carried (matched by base key)."""
    root = temp_uacp_root
    parent = RunManifest(
        run_id="inv-parent",
        authority=Authority(source="operator-request"),
        track="standard",
        current_phase="verify",
        artifacts={
            "verification_package": "verification/inv-parent-verify-selection.yaml",
            "investigation_entry:seq=1": "verification/inv-parent-investigation-1.yaml",
        },
    )
    _save_manifest(root, parent)
    out = _init_rework(root, "run-B", "inv-parent")
    assert out.get("ok") is True, out
    assert _manifest(root, "run-B")["carried_findings"] == {
        "verification_package": "verification/inv-parent-verify-selection.yaml",
        "investigation_entry:seq=1": "verification/inv-parent-investigation-1.yaml",
    }


def test_rework_carries_governed_writer_verify_keys(temp_uacp_root: Path):
    """A parent that authored its verify artifacts via uacp_entity_write registers them
    under the GOVERNED-WRITER keys 'verify_resolve_readiness' / 'piv_assessment'
    (kind.removeprefix('uacp.')). These MUST be carried too — a production rework's readiness
    and assessment findings must not be silently dropped just because the manual-alias keys
    differ (Codex #135)."""
    root = temp_uacp_root
    parent = RunManifest(
        run_id="gov-parent",
        authority=Authority(source="operator-request"),
        track="standard",
        current_phase="verify",
        artifacts={
            "verification_package": "verification/gov-parent-verify-selection.yaml",
            "verify_resolve_readiness": "verification/gov-parent-resolve-readiness.yaml",
            "piv_assessment": "verification/gov-parent-piv-assessment.yaml",
        },
    )
    _save_manifest(root, parent)
    out = _init_rework(root, "run-B", "gov-parent")
    assert out.get("ok") is True, out
    assert _manifest(root, "run-B")["carried_findings"] == {
        "verification_package": "verification/gov-parent-verify-selection.yaml",
        "verify_resolve_readiness": "verification/gov-parent-resolve-readiness.yaml",
        "piv_assessment": "verification/gov-parent-piv-assessment.yaml",
    }


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


# ------------------------------------ #135 P1: carried findings SURFACE into EXECUTE
def test_execute_entry_surfaces_carried_findings_for_rework(temp_uacp_root: Path):
    """On PLAN->EXECUTE a rework run echoes its carried findings + a briefing into the
    transition response, so the fix agent cannot enter EXECUTE unaware of what it reworks."""
    from state_machine import handle_transition
    from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites

    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    _init_rework(root, "run-B", "run-A")
    # advance the rework to PLAN (the surface fires on entry to EXECUTE); seed the faithful
    # plan-exit prerequisites so the #99 forced gates let the transition cross.
    m = _manifest(root, "run-B")
    m["current_phase"] = "plan"
    (root / ".uacp" / "state" / "runs" / "run-B.yaml").write_text(
        yaml.safe_dump(m, sort_keys=False), encoding="utf-8"
    )
    seed_plan_exit_prerequisites(root, "run-B")

    out = json.loads(
        handle_transition(
            {"workspace": str(root), "run_id": "run-B", "from_phase": "plan", "to_phase": "execute"}
        )
    )
    assert out.get("ok") is True, out
    assert out["reworks"] == "run-A"
    assert out["carried_findings"] == {
        "verification_package": "verification/run-A-verify-selection.yaml",
        "resolve_readiness": "verification/run-A-resolve-readiness.yaml",
        "assessment": "verification/run-A-piv-assessment.yaml",
    }
    assert "handled_findings_chain" in out["rework_briefing"]  # tells the agent the obligation


def test_execute_entry_no_rework_noise_for_plain_run(temp_uacp_root: Path):
    """A non-rework run entering EXECUTE gets NO carried_findings/rework_briefing keys."""
    from state_machine import handle_init, handle_transition
    from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites

    root = temp_uacp_root
    handle_init({"workspace": str(root), "run_id": "run-plain", "source": "operator-request"})
    m = _manifest(root, "run-plain")
    m["current_phase"] = "plan"
    (root / ".uacp" / "state" / "runs" / "run-plain.yaml").write_text(
        yaml.safe_dump(m, sort_keys=False), encoding="utf-8"
    )
    seed_plan_exit_prerequisites(root, "run-plain")
    out = json.loads(
        handle_transition(
            {
                "workspace": str(root),
                "run_id": "run-plain",
                "from_phase": "plan",
                "to_phase": "execute",
            }
        )
    )
    assert out.get("ok") is True, out
    assert "carried_findings" not in out and "rework_briefing" not in out


# ---------------------------------------------- #135 P3: keys DERIVED from schema
def test_verify_finding_keys_cover_both_registration_conventions():
    """The carry set is derived from the schema registry (not a frozen literal) and covers
    BOTH manifest registration conventions per verify kind (Codex #135): the governed-writer
    key (kind.removeprefix('uacp.'), the production uacp_entity_write path) AND the manual
    alias the skill/seeders register (resolve_readiness / assessment). If it only had the
    manual aliases, a real governed run's readiness/assessment findings would not be carried."""
    from engines.domain.schema import verify_finding_artifact_keys

    keys = verify_finding_artifact_keys()
    # governed-writer keys (production) — MUST be present
    assert {
        "verify_resolve_readiness",
        "piv_assessment",
        "verification_package",
        "investigation_entry",
    } <= keys
    # manual/seeder aliases — also present
    assert {"resolve_readiness", "assessment"} <= keys
    assert keys == frozenset(
        {
            "verification_package",
            "verify_resolve_readiness",
            "resolve_readiness",
            "piv_assessment",
            "assessment",
            "investigation_entry",
        }
    )


def test_new_verify_phase_kind_is_carried_automatically(monkeypatch, temp_uacp_root: Path):
    """The POINT of P3: register a NEW schema kind pinned phase=verify and it flows into
    the carry set WITHOUT editing the carry code — the miss the #135 review flagged (a new
    verify artifact kind silently not carried) can no longer happen."""
    from engines.domain import schema as S

    patched = dict(S._SCHEMAS)
    patched["uacp.verify_new_probe"] = {"properties": {"phase": {"const": "verify"}}}
    monkeypatch.setattr(S, "_SCHEMAS", patched)

    # unmapped kind falls back to its base name (strip uacp.), never silently dropped
    assert "verify_new_probe" in S.verify_finding_artifact_keys()

    # and a rework parent that registers it carries it forward
    root = temp_uacp_root
    _seed_parent_at_verify(root, "run-A")
    m0 = _manifest(root, "run-A")
    m0["artifacts"]["verify_new_probe"] = "verification/run-A-new-probe.yaml"
    (root / ".uacp" / "state" / "runs" / "run-A.yaml").write_text(
        yaml.safe_dump(m0, sort_keys=False), encoding="utf-8"
    )
    out = _init_rework(root, "run-B", "run-A")
    assert "verify_new_probe" in _manifest(root, "run-B")["carried_findings"], out


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

"""Task 7: goal-driven RESOLVE closure on manifest coherence.

ADR-0016 (the goal-driven track), open item O5. A goal-driven run's checkpoints
are disposable until one satisfies the goal; that satisfying checkpoint is
"promoted to result" and the run closes (VERIFY->RESOLVE / RESOLVE closure).

This module pins the CLOSURE gate. A goal-driven run may close ONLY when its
checkpoint manifest is COHERENT *AND* the standard closure invariants still pass:

  (a) the FINAL checkpoint's verdict == keep,
  (b) no dangling roll_back/restart left unresolved (== the final verdict, so (a)
      and (b) are the same convergence requirement),
  (c) the FINAL checkpoint's evidence EXISTS and is BOUND TO THE GOAL (its goal_id
      equals the run manifest's goal_id), AND
  (d) the standard closure invariants (no-fabrication / containment / the computed
      engines) STILL pass.

"Manifest coherence" is NOT a lower bar: it ADDS to the shared standard closure
invariants. A coherent manifest does NOT paper over a real closure violation.

And the STANDARD track is byte-identical to before: a standard verify->resolve
still demands its verify-selection / resolve-readiness artifacts and is NOT
satisfied by a manifest. EVERY new branch is behind
``_run_track(run_id) == "goal-driven"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from core import Heartgate
from state_machine import Authority, RunManifest, _save_manifest

# ---------------------------------------------------------------------------
# helpers (mirror test_goal_driven_gates.py's seeding so the manifest/ledger/
# budget/registry match the live writer envelopes the gate reads)
# ---------------------------------------------------------------------------


def _seed_manifest(
    root: Path,
    run_id: str,
    *,
    track: str = "goal-driven",
    goal_id: str | None = "g1",
) -> None:
    manifest = RunManifest(
        run_id=run_id,
        authority=Authority(source="operator-request"),
        track=track,
        goal_id=goal_id,
        current_phase="verify",
    )
    _save_manifest(root, manifest)


def _seed_budget(root: Path, run_id: str, budget: dict) -> None:
    rel = f"proposals/{run_id}-convergence-budget.yaml"
    path = root / ".uacp" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"kind": "uacp.convergence_budget", "convergence_budget": budget}
    path.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")


def _register_run_for_goal(root: Path, run_id: str, goal_id: str) -> None:
    reg = root / ".uacp" / "state" / "run-registry.yaml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if reg.exists():
        data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}
    active = data.get("active_runs") or []
    active.append({"run_id": run_id, "goal_id": goal_id, "phase": "verify"})
    data["active_runs"] = active
    reg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _seed_evidence(root: Path, rel: str) -> str:
    path = root / ".uacp" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("evidence artifact\n", encoding="utf-8")
    return rel


def _append_checkpoint(
    root: Path,
    run_id: str,
    *,
    goal_id: str,
    checkpoint_id: str,
    evidence: str,
    verdict: str = "keep",
    extra: dict | None = None,
) -> None:
    rel = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    rel.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "gate": "CHECKPOINT",
        "run_id": run_id,
        "ts": 1700000000,
        "checkpoint_id": checkpoint_id,
        "goal_id": goal_id,
        "phase": "execute",
        "what_changed": "probed the goal",
        "why": "iterating toward the goal",
        "evidence": evidence,
        "verdict": verdict,
        "invariant": "goal stays constant",
    }
    if extra:
        rec.update(extra)
    with rel.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def _resolve_transition(run_id: str) -> dict:
    return {
        "from_phase": "verify",
        "to_phase": "resolve",
        "run_id": run_id,
        "artifact_path": "resolutions/test.yaml",
    }


def _gate_blockers(root: Path, run_id: str) -> list[str]:
    """Invoke the verify->resolve evidence gate DIRECTLY and return its blockers.

    The conftest fixture graph terminates at ``verify->resolved`` (legacy naming),
    so a full ``validate_transition({... "resolve"})`` would add a graph
    "transition not allowed" blocker that masks the gate's own observable
    behavior. The adaptive-gate suite (test_adaptive_gate_fail_closed.py) isolates
    the gate by calling it directly; we follow that idiom for the manifest-
    coherence layer assertions, then exercise the FULL validate_transition for the
    cross-cutting standard-invariant checks (which fire independent of the edge).
    """
    blockers: list[str] = []
    Heartgate.load(str(root))._validate_adaptive_verify_evidence_gate(
        _resolve_transition(run_id), blockers
    )
    return blockers


def _closure_blockers(blockers: list[str]) -> list[str]:
    """Blockers sourced from the goal-driven closure / checkpoint manifest layer."""
    return [
        b
        for b in blockers
        if "checkpoint" in b.lower()
        or "manifest" in b.lower()
        or "goal-driven" in b.lower()
    ]


def _verify_evidence_blockers(blockers: list[str]) -> list[str]:
    """Blockers sourced from the deterministic standard verify->resolve gate."""
    return [b for b in blockers if "adaptive_verify_evidence_gate" in b]


# ---------------------------------------------------------------------------
# (a) coherent manifest + standard invariants pass -> closure allowed
# ---------------------------------------------------------------------------


class TestCoherentManifestAllowsClose:
    def test_coherent_manifest_no_closure_blocker(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/c2.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-002", evidence=ev2, verdict="keep",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)

        # The goal-driven closure layer must NOT block: a coherent manifest whose
        # final keep checkpoint is bound to the goal substitutes for the
        # verify-selection / resolve-readiness artifacts.
        assert not _closure_blockers(blockers), blockers
        # And the standard verify->resolve evidence gate must NOT fire (the
        # manifest substitutes for its artifacts on the goal-driven track).
        assert not _verify_evidence_blockers(blockers), blockers


# ---------------------------------------------------------------------------
# (b) dangling roll_back / restart final verdict -> BLOCKED from RESOLVE
# ---------------------------------------------------------------------------


class TestDanglingVerdictBlocksClose:
    def test_final_rollback_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/c2.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-002", evidence=ev2, verdict="roll_back",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _closure_blockers(blockers), blockers

    def test_final_restart_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="restart",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _closure_blockers(blockers), blockers


# ---------------------------------------------------------------------------
# (c) final checkpoint evidence missing -> BLOCKED
# ---------------------------------------------------------------------------


class TestMissingEvidenceBlocksClose:
    def test_final_evidence_missing_blocks(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )
        # final checkpoint's evidence path does NOT resolve to a real artifact
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-002",
            evidence="executions/does-not-exist.txt", verdict="keep",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _closure_blockers(blockers), blockers

    def test_final_evidence_not_bound_to_goal_blocks(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """O5: the promoted (final) checkpoint's evidence must be bound to the
        run's goal. A final keep whose goal_id is a DIFFERENT goal is not a
        result for THIS goal and must not close the run."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        # final keep has real evidence but is bound to a DIFFERENT goal
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id="some-other-goal",
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _closure_blockers(blockers), blockers


# ---------------------------------------------------------------------------
# (d) standard closure invariant violated -> STILL BLOCKED (coherence does NOT
#     paper over it)
# ---------------------------------------------------------------------------


class TestStandardInvariantsStillFireOnClose:
    def test_escaping_final_evidence_still_blocks(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """no-fabrication / containment: final-checkpoint evidence that escapes
        the governed root is not a real artifact and must block close even with
        an otherwise-coherent (final keep) manifest."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001",
            evidence="../../../etc/passwd", verdict="keep",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _closure_blockers(blockers), blockers

    def test_unowned_warning_still_blocks_with_coherent_manifest(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """A real closure violation (an unowned warning) must STILL block a
        goal-driven close even when the checkpoint manifest is fully coherent.
        Manifest coherence ADDS to the standard invariants; it never relaxes
        them."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )

        hg = Heartgate.load(str(temp_uacp_root))
        artifact = _resolve_transition(valid_run_id)
        # An unowned warning is a standard closure invariant violation (the
        # transition gate requires owner + residual risk on every warning).
        artifact["warnings"] = ["something looked off"]
        decision = hg.validate_transition(artifact)

        assert decision.decision == "block"
        assert any("warnings require owner" in b for b in decision.blockers), (
            decision.blockers
        )

    def test_invariant_summary_failure_still_blocks(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """A failed invariant_summary entry (a computed/declared invariant) still
        blocks close — the coherent manifest does not paper over it."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id=goal_id,
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )

        hg = Heartgate.load(str(temp_uacp_root))
        artifact = _resolve_transition(valid_run_id)
        artifact["invariant_summary"] = [{"id": "INV-9", "status": "fail"}]
        decision = hg.validate_transition(artifact)

        assert decision.decision == "block"
        assert any("INV-9" in b for b in decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (e) STANDARD track close is unchanged: still demands verify-selection /
#     resolve-readiness; a manifest does NOT satisfy it
# ---------------------------------------------------------------------------


class TestStandardTrackCloseUnchanged:
    def test_standard_close_still_demands_verify_evidence(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        _seed_manifest(temp_uacp_root, valid_run_id, track="standard", goal_id=None)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        # Even a coherent-looking manifest must be IGNORED on the standard track.
        _append_checkpoint(
            temp_uacp_root, valid_run_id, goal_id="g1",
            checkpoint_id="ckpt-001", evidence=ev1, verdict="keep",
        )

        blockers = _gate_blockers(temp_uacp_root, valid_run_id)

        # The standard verify->resolve gate still demands its artifacts (absent)
        # -> it must block on them, NOT on the manifest.
        assert _verify_evidence_blockers(blockers), blockers
        # The manifest must NOT be consulted on the standard track: no checkpoint/
        # manifest/goal-driven blocker may appear.
        assert not [
            b
            for b in blockers
            if "checkpoint" in b.lower() or "goal-driven" in b.lower()
        ], blockers

    def test_standard_no_manifest_still_demands_verify_evidence(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        # No manifest at all -> track resolves to standard -> gate unchanged.
        blockers = _gate_blockers(temp_uacp_root, valid_run_id)
        assert _verify_evidence_blockers(blockers), blockers

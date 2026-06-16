"""Task 6: wire the live goal-driven checkpoint flow + track-aware gate relaxation.

ADR-0016 (the goal-driven track). On the goal-driven EXECUTE->VERIFY transition,
the deterministic findings-clearing / PIV-style evidence gate (which, on the
STANDARD track, demands a ``plans/{run_id}-piv.yaml`` PIV contract +
``executions/{run_id}-checkpoint-001.yaml`` execution checkpoint) is SATISFIED BY
a COHERENT checkpoint manifest in lieu of the PIV artifact, where "coherent" =

  * every gate: CHECKPOINT ledger entry validates (envelope-stripped, parses as a
    CheckpointEntry, and its evidence references a real governed-root artifact —
    the structural no-self-attestation rule), AND
  * the manifest's FINAL verdict is ``keep`` (no dangling roll_back / restart), AND
  * no ``keep`` checkpoint is over the convergence cap (the cap is LIVE here).

It is BLOCKED if the manifest is incoherent / missing.

The authority / write-containment / no-fabrication invariants STILL fire for a
goal-driven run — only the deterministic PIV/findings-clearing gate relaxes into
the manifest. And the STANDARD track is byte-identical to before: a standard
execute->verify still demands its PIV/checkpoint artifacts and is NOT satisfied
by a manifest. EVERY new branch is behind ``_run_track(run_id) == "goal-driven"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from core import Heartgate
from state_machine import Authority, RunManifest, _save_manifest

# ---------------------------------------------------------------------------
# helpers
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
        current_phase="execute",
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
    active.append({"run_id": run_id, "goal_id": goal_id, "phase": "execute"})
    data["active_runs"] = active
    reg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _seed_evidence(root: Path, rel: str) -> str:
    """Create a real governed-root artifact and return its governed-relative path."""
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
    """Append a gate: CHECKPOINT record, envelope-stamped exactly as the writer does
    (gate / run_id / ts), with a full CheckpointEntry payload."""
    rel = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    rel.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        # envelope fields the writer stamps:
        "gate": "CHECKPOINT",
        "run_id": run_id,
        "ts": 1700000000,
        # CheckpointEntry payload:
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


def _transition(run_id: str) -> dict:
    return {
        "from_phase": "execute",
        "to_phase": "verify",
        "run_id": run_id,
        "artifact_path": "verification/test.yaml",
    }


def _piv_blockers(blockers: list[str]) -> list[str]:
    """Blockers sourced from the deterministic PIV/execute-evidence gate."""
    return [
        b
        for b in blockers
        if "adaptive_execute_evidence_gate" in b or "piv" in b.lower()
    ]


def _checkpoint_blockers(blockers: list[str]) -> list[str]:
    return [b for b in blockers if "checkpoint" in b.lower() or "manifest" in b.lower()]


# ---------------------------------------------------------------------------
# (a) goal-driven execute->verify with a COHERENT manifest satisfies the gate
# ---------------------------------------------------------------------------


class TestCoherentManifestSatisfiesGate:
    def test_coherent_manifest_no_piv_blocker(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/c2.txt")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-002", evidence=ev2, verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        # The deterministic PIV / execute-evidence gate must NOT block: a coherent
        # manifest substitutes for the missing PIV/checkpoint artifacts.
        assert not _piv_blockers(decision.blockers), decision.blockers
        assert not _checkpoint_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (b) an INCOHERENT manifest BLOCKS
# ---------------------------------------------------------------------------


class TestIncoherentManifestBlocks:
    def test_missing_evidence_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        # evidence path that does not resolve to a real artifact
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001",
                           evidence="executions/does-not-exist.txt", verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _checkpoint_blockers(decision.blockers), decision.blockers

    def test_dangling_rollback_final_verdict_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/c2.txt")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")
        # final verdict is roll_back -> not converged -> incoherent for promotion
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-002", evidence=ev2, verdict="roll_back")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _checkpoint_blockers(decision.blockers), decision.blockers

    def test_malformed_entry_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        # malformed: missing required CheckpointEntry fields (what_changed/why/...)
        rel = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
        rec = {
            "gate": "CHECKPOINT",
            "run_id": valid_run_id,
            "ts": 1700000000,
            "checkpoint_id": "ckpt-001",
            "goal_id": goal_id,
            "evidence": ev1,
            "verdict": "keep",
        }
        with rel.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _checkpoint_blockers(decision.blockers), decision.blockers

    def test_missing_manifest_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        # goal-driven run, no CHECKPOINT records at all, and no PIV/checkpoint
        # artifacts -> nothing to substitute for the relaxed gate -> blocked.
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _checkpoint_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (c) an over-budget keep checkpoint BLOCKS (cap is LIVE in this path)
# ---------------------------------------------------------------------------


class TestOverBudgetKeepBlocks:
    def test_over_cap_keep_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 1})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/c2.txt")
        # 2 keep checkpoints recorded, cap is 1 -> the manifest is over budget.
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-002", evidence=ev2, verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        cap_blockers = [
            b for b in decision.blockers if "budget" in b.lower() or "cap" in b.lower()
        ]
        assert cap_blockers, decision.blockers


# ---------------------------------------------------------------------------
# (c-boundary) at-budget manifest passes; max_checkpoints+1 blocks
# ---------------------------------------------------------------------------


class TestConvergenceCapBoundary:
    """Boundary tests for the post-loop strict-'>' cap check.

    The bug was that a manifest with EXACTLY max_checkpoints keep checkpoints
    was wrongly blocked (count >= max → block, but count == max is at-budget,
    not over-budget).  After the fix:

      * exactly max_checkpoints → NOT blocked for the cap reason
      * max_checkpoints + 1    → BLOCKED for the cap reason
    """

    def test_exactly_at_cap_passes(self, temp_uacp_root: Path, valid_run_id: str):
        """A manifest with exactly max_checkpoints checkpoints must NOT be
        blocked by the convergence cap (the bug case)."""
        max_cp = 3
        goal_id = "g-boundary"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": max_cp})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)

        for i in range(1, max_cp + 1):
            ev = _seed_evidence(temp_uacp_root, f"executions/boundary-ev-{i}.txt")
            _append_checkpoint(
                temp_uacp_root,
                valid_run_id,
                goal_id=goal_id,
                checkpoint_id=f"ckpt-{i:03d}",
                evidence=ev,
                verdict="keep",
            )

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        cap_blockers = [
            b for b in decision.blockers if "budget" in b.lower() or "cap" in b.lower()
        ]
        assert not cap_blockers, (
            f"expected no cap blocker for exactly max_checkpoints={max_cp} entries, "
            f"got: {cap_blockers}"
        )

    def test_one_over_cap_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """A manifest with max_checkpoints + 1 checkpoints MUST be blocked
        by the convergence cap."""
        max_cp = 3
        goal_id = "g-boundary"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": max_cp})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)

        for i in range(1, max_cp + 2):  # max_cp + 1 entries
            ev = _seed_evidence(temp_uacp_root, f"executions/boundary-over-{i}.txt")
            _append_checkpoint(
                temp_uacp_root,
                valid_run_id,
                goal_id=goal_id,
                checkpoint_id=f"ckpt-{i:03d}",
                evidence=ev,
                verdict="keep",
            )

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        cap_blockers = [
            b for b in decision.blockers if "budget" in b.lower() or "cap" in b.lower()
        ]
        assert cap_blockers, (
            f"expected a cap blocker for max_checkpoints+1={max_cp + 1} entries, "
            f"got: {decision.blockers}"
        )


# ---------------------------------------------------------------------------
# (d) authority / containment / no-fabrication STILL fire for goal-driven
# ---------------------------------------------------------------------------


class TestInvariantsStillFireGoalDriven:
    def test_escaping_evidence_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """no-fabrication / containment: evidence that escapes the governed root
        is not a real artifact and must block even on the goal-driven track."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001",
                           evidence="../../../etc/passwd", verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _checkpoint_blockers(decision.blockers), decision.blockers

    def test_invariant_summary_failure_still_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """authority/invariant gate: a failed invariant_summary entry still blocks
        a goal-driven transition (the relaxation does not touch this)."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        artifact = _transition(valid_run_id)
        artifact["invariant_summary"] = [{"id": "INV-1", "status": "fail"}]
        decision = hg.validate_transition(artifact)

        assert decision.decision == "block"
        assert any("INV-1" in b for b in decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (e) STANDARD track is unchanged: still demands PIV/evidence, manifest does not
#     satisfy it
# ---------------------------------------------------------------------------


class TestStandardTrackUnchanged:
    def test_standard_execute_verify_still_demands_piv(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        # standard run; a checkpoint manifest, if present, must NOT satisfy the gate.
        _seed_manifest(temp_uacp_root, valid_run_id, track="standard", goal_id=None)
        ev1 = _seed_evidence(temp_uacp_root, "executions/c1.txt")
        # Even seed a coherent-looking manifest — it must be ignored on standard.
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id="g1",
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        # The standard execute->verify gate still demands the PIV/checkpoint
        # artifacts (which are absent) -> it must block on them.
        assert decision.decision == "block"
        assert _piv_blockers(decision.blockers), decision.blockers

    def test_standard_no_manifest_still_demands_piv(self, temp_uacp_root: Path, valid_run_id: str):
        # No manifest at all -> track resolves to standard -> gate unchanged.
        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        assert decision.decision == "block"
        assert _piv_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (M-1) cross-chain cap evasion is closed: the cap counts the run-chain by
#       MANIFEST goal_id, not the run registry. A forward run that does NOT
#       register (or registers under a different goal_id) is still counted.
# ---------------------------------------------------------------------------


class TestCrossChainCapEvasionClosed:
    """Council M-1 (autonomous-safety hole).

    The convergence budget counts a goal's CHECKPOINT entries across its whole
    run-chain. The chain is now enumerated by scanning run MANIFESTS on disk
    (``state/runs/*.yaml``) and counting every run whose manifest ``goal_id``
    equals the goal — NOT the run registry. So an executor cannot reset the
    budget by spawning forward runs that never register (or register under a
    different goal_id): those runs are still counted via their manifest.
    """

    def test_unregistered_forward_run_is_still_counted(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """The exploit: goal g1, cap=2. r1 has 2 keep checkpoints (at budget).
        r2 (manifest goal_id=g1) adds 1 more checkpoint but is NOT registered
        under g1. A registry-based count would see only r2's 1 checkpoint and
        let it through; the manifest scan counts r1's 2 + r2's 1 = 3 > 2 -> the
        over-budget keep is BLOCKED at r2's execute->verify."""
        goal_id = "g1"
        r1 = valid_run_id
        r2 = "uacp-test-002"
        # r1: 2 keep checkpoints (the budget is max_checkpoints=2 -> at budget).
        _seed_manifest(temp_uacp_root, r1, goal_id=goal_id)
        _seed_budget(temp_uacp_root, r1, {"max_checkpoints": 2})
        ev1 = _seed_evidence(temp_uacp_root, "executions/r1-c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/r1-c2.txt")
        _append_checkpoint(temp_uacp_root, r1, goal_id=goal_id,
                           checkpoint_id="r1-ckpt-001", evidence=ev1, verdict="keep")
        _append_checkpoint(temp_uacp_root, r1, goal_id=goal_id,
                           checkpoint_id="r1-ckpt-002", evidence=ev2, verdict="keep")

        # r2: forward run bound to g1 by MANIFEST, with its own budget, 1 more
        # keep checkpoint -- but deliberately NOT registered under g1 (the
        # evasion: only r2 is registered for itself, NOT into the g1 chain).
        _seed_manifest(temp_uacp_root, r2, goal_id=goal_id)
        _seed_budget(temp_uacp_root, r2, {"max_checkpoints": 2})
        ev3 = _seed_evidence(temp_uacp_root, "executions/r2-c1.txt")
        _append_checkpoint(temp_uacp_root, r2, goal_id=goal_id,
                           checkpoint_id="r2-ckpt-001", evidence=ev3, verdict="keep")
        # NOTE: no _register_run_for_goal call at all -> registry has NO g1 entry.

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(r2))

        # The manifest scan counts r1(2) + r2(1) = 3 > cap 2 -> over budget.
        assert decision.decision == "block"
        cap_blockers = [
            b for b in decision.blockers if "budget" in b.lower() or "cap" in b.lower()
        ]
        assert cap_blockers, decision.blockers
        # And the count attributed to the goal is the full chain total (3).
        assert hg._goal_checkpoint_count(goal_id) == 3

    def test_misregistered_forward_run_is_still_counted(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """A forward run registered under a DIFFERENT goal_id is still counted by
        its MANIFEST goal_id. r1(g1)=2 at cap; r2 manifest goal_id=g1 but its
        registry entry claims goal_id=g-other -> a registry count for g1 would
        miss r2, but the manifest scan still counts it -> BLOCKED."""
        goal_id = "g1"
        r1 = valid_run_id
        r2 = "uacp-test-002"
        _seed_manifest(temp_uacp_root, r1, goal_id=goal_id)
        _seed_budget(temp_uacp_root, r1, {"max_checkpoints": 2})
        ev1 = _seed_evidence(temp_uacp_root, "executions/r1-c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/r1-c2.txt")
        _append_checkpoint(temp_uacp_root, r1, goal_id=goal_id,
                           checkpoint_id="r1-ckpt-001", evidence=ev1, verdict="keep")
        _append_checkpoint(temp_uacp_root, r1, goal_id=goal_id,
                           checkpoint_id="r1-ckpt-002", evidence=ev2, verdict="keep")

        _seed_manifest(temp_uacp_root, r2, goal_id=goal_id)
        _seed_budget(temp_uacp_root, r2, {"max_checkpoints": 2})
        ev3 = _seed_evidence(temp_uacp_root, "executions/r2-c1.txt")
        _append_checkpoint(temp_uacp_root, r2, goal_id=goal_id,
                           checkpoint_id="r2-ckpt-001", evidence=ev3, verdict="keep")
        # Registry mis-attribution: r2 registered under g-other, NOT g1.
        _register_run_for_goal(temp_uacp_root, r2, "g-other")

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(r2))

        assert decision.decision == "block"
        cap_blockers = [
            b for b in decision.blockers if "budget" in b.lower() or "cap" in b.lower()
        ]
        assert cap_blockers, decision.blockers
        assert hg._goal_checkpoint_count(goal_id) == 3


# ---------------------------------------------------------------------------
# (MINOR) goal-driven under PRODUCTION-DEFAULT gates: the checkpoint relaxation
#         layers ON TOP of the PIV ledger gate; it does NOT dodge it.
# ---------------------------------------------------------------------------


def _enable_production_piv_ledger(root: Path) -> None:
    """Flip the test fixture's piv_rule opt-out (ledger_required: false) to the
    PRODUCTION DEFAULT (ledger_required: true), so the PIV ledger gate is ON.

    The conftest fixture deliberately opts OUT of piv_rule to preserve prior
    test laxity; this restores the production posture for the one test that
    pins goal-driven != governance-skip under production config."""
    cfg = root / "config" / "phase-transitions.yaml"
    text = cfg.read_text(encoding="utf-8")
    new_text = text.replace(
        "piv_rule:\n  ledger_required: false", "piv_rule:\n  ledger_required: true"
    )
    # Fail loudly (not vacuously) if the conftest stub formatting drifts so the
    # replace silently no-ops: the production posture this test depends on would
    # otherwise quietly never be set. Pin the precondition explicitly.
    assert new_text != text, (
        "conftest piv_rule opt-out stub not found to flip — _enable_production_piv_ledger "
        "must actually set ledger_required: true (check tests/conftest.py stub formatting)"
    )
    cfg.write_text(new_text, encoding="utf-8")


class TestGoalDrivenUnderProductionPivLedger:
    """Council MINOR: the goal-driven e2e fixtures opt OUT of piv_rule. Pin that,
    UNDER the production-default piv_rule (ledger_required: true), a goal-driven
    execute->verify with an otherwise-COHERENT checkpoint manifest STILL owes the
    PIV ledger record — the checkpoint relaxation substitutes for the
    PIV/findings-clearing ARTIFACTS, not for the PIV LEDGER gate."""

    def test_goal_driven_still_owes_piv_ledger_record(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        # A coherent manifest: real evidence, final verdict keep, within budget.
        ev1 = _seed_evidence(temp_uacp_root, "executions/prod-c1.txt")
        ev2 = _seed_evidence(temp_uacp_root, "executions/prod-c2.txt")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-001", evidence=ev1, verdict="keep")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id=goal_id,
                           checkpoint_id="ckpt-002", evidence=ev2, verdict="keep")

        # Production-default PIV ledger gate ON (no PIV pass record is seeded —
        # only CHECKPOINT records exist, which are NOT PIV pass records).
        _enable_production_piv_ledger(temp_uacp_root)

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition(_transition(valid_run_id))

        # The coherent manifest satisfies the adaptive PIV-ARTIFACT gate (no
        # adaptive_execute_evidence_gate blocker) ...
        assert not _checkpoint_blockers(decision.blockers), decision.blockers
        # ... but the production PIV LEDGER gate STILL fires: the run owes a PIV
        # pass ledger record, which the checkpoint relaxation does NOT provide.
        piv_ledger_blockers = [b for b in decision.blockers if "piv_rule" in b.lower()]
        assert decision.decision == "block"
        assert piv_ledger_blockers, decision.blockers

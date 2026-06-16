"""Task 5: goal-driven runs require + enforce a convergence budget.

ADR-0016 (R2): a goal-driven run iterates by taking checkpoints toward a
persistent goal. "Operator sign-off" is the *interactive* exit, but an
autonomous run (``claude -p``, cron) has no operator — so without a declared,
enforced bound it loops forever. This task makes a convergence budget:

  (i)  REQUIRED on the goal-driven PROPOSE artifact at PROPOSE->PLAN, and
  (ii) ENFORCED — a further ``keep``/continue checkpoint is BLOCKED once the
       goal's CHECKPOINT count (across its whole run-chain) reaches
       ``max_checkpoints``.

EVERY new behavior is gated on ``track == "goal-driven"`` read from the run
manifest. Standard runs are byte-identical to before — these tests pin that
(case c) and the standard-track suite (test_full_lifecycle etc.) stays green.

The budget lives at ``proposals/{run_id}-convergence-budget.yaml`` (a sibling
PROPOSE artifact, mirroring the ``-package-selection.yaml`` / ``-scope.yaml``
conventions): a machine-readable YAML carrying ``convergence_budget``.
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


def _seed_triage(root: Path, run_id: str, track: str = "goal-driven") -> None:
    """Write a TRIAGE artifact declaring the track (council M-2: TRIAGE is the
    authority for the track decision; the manifest track must match it)."""
    rel = f"proposals/{run_id}-triage.yaml"
    path = root / ".uacp" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"kind": "triage", "run_id": run_id, "track": track}
    path.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")


def _seed_manifest(
    root: Path,
    run_id: str,
    *,
    track: str = "goal-driven",
    goal_id: str | None = "g1",
    seed_triage: bool = True,
) -> None:
    """Write a run manifest at state/runs/{run_id}.yaml with the given track.

    By default also seeds a matching TRIAGE artifact so the council M-2
    track-vs-triage cross-check binds (a goal-driven manifest needs a
    goal-driven triage decision). Tests exercising the mismatch pass
    ``seed_triage=False`` (or seed a divergent triage artifact themselves)."""
    manifest = RunManifest(
        run_id=run_id,
        authority=Authority(source="operator-request"),
        track=track,
        goal_id=goal_id,
        current_phase="propose",
    )
    _save_manifest(root, manifest)
    if seed_triage:
        _seed_triage(root, run_id, track=track)


def _seed_budget(root: Path, run_id: str, budget: dict | None) -> None:
    """Write the PROPOSE convergence-budget artifact (or, if budget is None, a
    well-formed YAML that simply omits the convergence_budget key)."""
    rel = f"proposals/{run_id}-convergence-budget.yaml"
    path = root / ".uacp" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    body: dict = {"kind": "uacp.convergence_budget"}
    if budget is not None:
        body["convergence_budget"] = budget
    path.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")


def _append_checkpoint(root: Path, run_id: str, goal_id: str, ckpt_id: str,
                       verdict: str = "keep") -> None:
    """Append a gate: CHECKPOINT record to the run's gate ledger directly
    (the writer is exercised elsewhere; here we just need the count)."""
    rel = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    rel.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "gate": "CHECKPOINT",
        "run_id": run_id,
        "goal_id": goal_id,
        "checkpoint_id": ckpt_id,
        "verdict": verdict,
    }
    with rel.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")


def _register_run_for_goal(root: Path, run_id: str, goal_id: str) -> None:
    """Add an active_runs[] entry carrying goal_id so list_runs_for_goal finds
    it (the chain is enumerated via the registry)."""
    reg = root / ".uacp" / "state" / "run-registry.yaml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if reg.exists():
        data = yaml.safe_load(reg.read_text(encoding="utf-8")) or {}
    active = data.get("active_runs") or []
    active.append({"run_id": run_id, "goal_id": goal_id, "phase": "execute"})
    data["active_runs"] = active
    reg.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _budget_blockers(blockers: list[str]) -> list[str]:
    return [b for b in blockers if "convergence_budget" in b or "budget" in b.lower()]


# ---------------------------------------------------------------------------
# (a) goal-driven PROPOSE->PLAN with NO / invalid budget is BLOCKED
# ---------------------------------------------------------------------------


class TestBudgetRequiredAtProposeToPlan:
    def test_missing_budget_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        _seed_manifest(temp_uacp_root, valid_run_id)
        _seed_budget(temp_uacp_root, valid_run_id, None)  # artifact present, key absent

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        assert decision.decision == "block"
        assert _budget_blockers(decision.blockers), decision.blockers

    def test_no_budget_artifact_at_all_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        _seed_manifest(temp_uacp_root, valid_run_id)
        # No -convergence-budget.yaml written at all.

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        assert decision.decision == "block"
        assert _budget_blockers(decision.blockers), decision.blockers

    def test_zero_max_checkpoints_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        _seed_manifest(temp_uacp_root, valid_run_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 0})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        assert decision.decision == "block"
        assert _budget_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (b) goal-driven PROPOSE->PLAN WITH a valid budget is not blocked for budget
# ---------------------------------------------------------------------------


class TestValidBudgetPasses:
    def test_valid_budget_not_blocked_for_budget_reason(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        _seed_manifest(temp_uacp_root, valid_run_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        # The budget must not be the thing that blocks. (The adaptive proposal-
        # package gate fails closed in this fixture and may block on its own
        # missing selection artifact — unrelated to the budget; we only assert
        # the budget is NOT a blocker.)
        assert not _budget_blockers(decision.blockers), decision.blockers

    def test_optional_fields_accepted(self, temp_uacp_root: Path, valid_run_id: str):
        _seed_manifest(temp_uacp_root, valid_run_id)
        _seed_budget(
            temp_uacp_root,
            valid_run_id,
            {"max_checkpoints": 3, "max_spend": 12.5, "max_wall_clock": "PT2H"},
        )

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        assert not _budget_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (c) standard run with no budget is NOT blocked — track-gated
# ---------------------------------------------------------------------------


class TestStandardTrackUnaffected:
    def test_standard_run_no_budget_not_blocked(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        _seed_manifest(temp_uacp_root, valid_run_id, track="standard", goal_id=None)
        # No budget artifact at all.

        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        # A standard run never enters the budget gate (track-gated), so the
        # budget is never a blocker — regardless of any other gate's verdict.
        assert not _budget_blockers(decision.blockers), decision.blockers

    def test_standard_run_with_no_manifest_not_blocked(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        # No manifest at all -> track unknown -> treated as standard -> no budget gate.
        hg = Heartgate.load(str(temp_uacp_root))
        decision = hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": valid_run_id,
            "artifact_path": "plans/test.yaml",
        })

        assert not _budget_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (M-2) the manifest track must match the TRIAGE decision (un-forge the track)
# ---------------------------------------------------------------------------


def _track_mismatch_blockers(blockers: list[str]) -> list[str]:
    return [b for b in blockers if "track mismatch" in b.lower()]


class TestTrackBoundToTriage:
    """Council M-2: ``track`` on the manifest is worker-set; a worker could
    self-select ``goal-driven`` to swap the deterministic PIV-artifact gate for
    the relaxed checkpoint-manifest gate. The TRIAGE artifact is the authority
    for the track decision, so at PROPOSE->PLAN a goal-driven manifest whose
    TRIAGE artifact did NOT decide goal-driven is blocked fail-closed."""

    def _propose_to_plan(self, hg: Heartgate, run_id: str):
        return hg.validate_transition({
            "from_phase": "propose",
            "to_phase": "plan",
            "run_id": run_id,
            "artifact_path": "plans/test.yaml",
        })

    def test_forged_goal_driven_track_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """Manifest track=goal-driven but TRIAGE track=standard -> BLOCKED with a
        track-mismatch blocker (the forge is refused)."""
        _seed_manifest(temp_uacp_root, valid_run_id, seed_triage=False)
        _seed_triage(temp_uacp_root, valid_run_id, track="standard")
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = self._propose_to_plan(hg, valid_run_id)

        assert decision.decision == "block"
        assert _track_mismatch_blockers(decision.blockers), decision.blockers

    def test_no_triage_track_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """Manifest track=goal-driven but the TRIAGE artifact declares NO track
        (defaults to standard) -> BLOCKED."""
        _seed_manifest(temp_uacp_root, valid_run_id, seed_triage=False)
        # triage artifact present but with no track key -> defaults to standard.
        rel = f"proposals/{valid_run_id}-triage.yaml"
        path = temp_uacp_root / ".uacp" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump({"kind": "triage", "run_id": valid_run_id}, sort_keys=False)
        path.write_text(body, encoding="utf-8")
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = self._propose_to_plan(hg, valid_run_id)

        assert decision.decision == "block"
        assert _track_mismatch_blockers(decision.blockers), decision.blockers

    def test_no_triage_artifact_at_all_blocks(self, temp_uacp_root: Path, valid_run_id: str):
        """Manifest track=goal-driven but NO triage artifact at all (absent ->
        standard) -> BLOCKED."""
        _seed_manifest(temp_uacp_root, valid_run_id, seed_triage=False)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = self._propose_to_plan(hg, valid_run_id)

        assert decision.decision == "block"
        assert _track_mismatch_blockers(decision.blockers), decision.blockers

    def test_matching_goal_driven_triage_not_blocked_for_track(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """Manifest track=goal-driven AND TRIAGE track=goal-driven -> NOT blocked
        for the track-mismatch reason (the track is legitimately goal-driven)."""
        _seed_manifest(temp_uacp_root, valid_run_id, seed_triage=False)
        _seed_triage(temp_uacp_root, valid_run_id, track="goal-driven")
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 5})

        hg = Heartgate.load(str(temp_uacp_root))
        decision = self._propose_to_plan(hg, valid_run_id)

        assert not _track_mismatch_blockers(decision.blockers), decision.blockers

    def test_standard_run_unaffected_by_track_check(
        self, temp_uacp_root: Path, valid_run_id: str
    ):
        """A standard-track manifest never reaches the track-vs-triage check
        (it's behind the goal-driven branch) -> no track-mismatch blocker even
        with no triage artifact."""
        _seed_manifest(
            temp_uacp_root, valid_run_id, track="standard", goal_id=None, seed_triage=False
        )

        hg = Heartgate.load(str(temp_uacp_root))
        decision = self._propose_to_plan(hg, valid_run_id)

        assert not _track_mismatch_blockers(decision.blockers), decision.blockers


# ---------------------------------------------------------------------------
# (d) cap enforcement: a further keep/continue checkpoint at/over the cap blocks
# ---------------------------------------------------------------------------


class TestCheckpointCapEnforcement:
    def test_at_cap_blocks_further_keep(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 2})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        # Two checkpoints already recorded for the goal -> cap reached.
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id, "ckpt-001")
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id, "ckpt-002")

        hg = Heartgate.load(str(temp_uacp_root))
        blockers: list[str] = []
        proposed = {
            "checkpoint_id": "ckpt-003",
            "run_id": valid_run_id,
            "goal_id": goal_id,
            "verdict": "keep",
        }
        hg._validate_convergence_cap(proposed, blockers)

        assert blockers, "a keep checkpoint at the cap must block"
        assert _budget_blockers(blockers), blockers

    def test_below_cap_allows_keep(self, temp_uacp_root: Path, valid_run_id: str):
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 3})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id, "ckpt-001")

        hg = Heartgate.load(str(temp_uacp_root))
        blockers: list[str] = []
        proposed = {
            "checkpoint_id": "ckpt-002",
            "run_id": valid_run_id,
            "goal_id": goal_id,
            "verdict": "keep",
        }
        hg._validate_convergence_cap(proposed, blockers)

        assert not blockers, blockers

    def test_cap_counts_across_run_chain(self, temp_uacp_root: Path, valid_run_id: str):
        """The cap counts CHECKPOINT entries across ALL runs sharing the goal_id
        (a goal can span a chain of runs, Task 3)."""
        goal_id = "g1"
        run_a = valid_run_id
        run_b = "uacp-test-002"
        # Council M-1: the chain is counted by MANIFEST goal_id, so both runs
        # need a manifest binding them to the goal.
        _seed_manifest(temp_uacp_root, run_a, goal_id=goal_id)
        _seed_manifest(temp_uacp_root, run_b, goal_id=goal_id)
        _seed_budget(temp_uacp_root, run_b, {"max_checkpoints": 2})
        _register_run_for_goal(temp_uacp_root, run_a, goal_id)
        _register_run_for_goal(temp_uacp_root, run_b, goal_id)
        # One checkpoint on each of two chained runs -> 2 total -> cap reached.
        _append_checkpoint(temp_uacp_root, run_a, goal_id, "ckpt-001")
        _append_checkpoint(temp_uacp_root, run_b, goal_id, "ckpt-002")

        hg = Heartgate.load(str(temp_uacp_root))
        blockers: list[str] = []
        proposed = {
            "checkpoint_id": "ckpt-003",
            "run_id": run_b,
            "goal_id": goal_id,
            "verdict": "keep",
        }
        hg._validate_convergence_cap(proposed, blockers)

        assert blockers, "cap must count across the whole run-chain"
        assert _budget_blockers(blockers), blockers

    def test_converge_verdict_not_capped(self, temp_uacp_root: Path, valid_run_id: str):
        """A non-continue verdict (roll_back/restart) is the *escape* the cap
        forces — it must NOT itself be blocked by the cap."""
        goal_id = "g1"
        _seed_manifest(temp_uacp_root, valid_run_id, goal_id=goal_id)
        _seed_budget(temp_uacp_root, valid_run_id, {"max_checkpoints": 1})
        _register_run_for_goal(temp_uacp_root, valid_run_id, goal_id)
        _append_checkpoint(temp_uacp_root, valid_run_id, goal_id, "ckpt-001")

        hg = Heartgate.load(str(temp_uacp_root))
        blockers: list[str] = []
        proposed = {
            "checkpoint_id": "ckpt-002",
            "run_id": valid_run_id,
            "goal_id": goal_id,
            "verdict": "restart",
        }
        hg._validate_convergence_cap(proposed, blockers)

        assert not blockers, blockers

"""Permanent regression tripwire: standard-track production-equivalence + phase graph unchanged.

Goal-driven track (Tasks 1-7) added behavior ENTIRELY gated on ``track == "goal-driven"``.
This test suite pins four invariants that must hold in perpetuity:

1. **Phase graph un-mutated** — ``phase_graph.LIFECYCLE_GRAPH`` is exactly the canonical
   6-node lifecycle edge set; ``state_machine.VALID_TRANSITIONS`` is the unchanged
   5-edge runtime projection.  No goal-driven feature added graph edges.

2. **Standard run defaults** — a ``RunManifest`` / ``handle_init`` with no track args
   yields ``track == "standard"``, ``goal_id is None``, ``inherits_from is None``, and
   ``inherited_artifacts == {}``.

3. **Standard gates untouched** — for a standard-track run (no goal manifest), the
   track-aware execute->verify gate and verify->resolve gate run their standard bodies:
   ``_run_track`` returns ``"standard"``, no ``checkpoint``/``manifest``/
   ``convergence_budget``-flavoured blocker fires, and the gates emit only the standard
   PIV/evidence blockers they would have emitted pre-feature.

4. **``_run_track`` fail-safe** — with a missing or garbled run manifest, ``_run_track``
   returns ``"standard"`` (never raises), so an unreadable manifest cannot flip a run
   into goal-driven behaviour.

These tests are PIN tests: they document and lock current behaviour.  A failing
assertion is a real finding — do NOT weaken assertions to make them pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
from engines.domain import phase_graph
from state_machine import Authority, RunManifest, _save_manifest


# ---------------------------------------------------------------------------
# Group 1: Phase graph un-mutated
# ---------------------------------------------------------------------------


class TestPhaseGraphUnmutated:
    """Pin the full LIFECYCLE_GRAPH and VALID_TRANSITIONS to their canonical values.

    Updated in Brainstorm-phase slice: brainstorm->triage is a new edge.
    The brainstorm node is an optional entry phase prepended to the lifecycle graph.
    """

    EXPECTED_LIFECYCLE_GRAPH: dict[str, set[str]] = {
        "brainstorm": {"triage"},
        "triage": {"propose", "terminal"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolve"},
        "resolve": {"terminal"},
    }

    EXPECTED_VALID_TRANSITIONS: dict[str, set[str]] = {
        "brainstorm": {"triage"},
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }

    def test_lifecycle_graph_node_count_unchanged(self) -> None:
        """LIFECYCLE_GRAPH must have exactly 7 nodes (brainstorm added as optional entry phase)."""
        assert len(phase_graph.LIFECYCLE_GRAPH) == 7, (
            f"expected 7 nodes, got {len(phase_graph.LIFECYCLE_GRAPH)}: "
            f"{sorted(phase_graph.LIFECYCLE_GRAPH)}"
        )

    def test_lifecycle_graph_edge_set_unchanged(self) -> None:
        """LIFECYCLE_GRAPH edge set is byte-identical to the canonical set including brainstorm."""
        assert phase_graph.LIFECYCLE_GRAPH == self.EXPECTED_LIFECYCLE_GRAPH, (
            "LIFECYCLE_GRAPH was mutated — goal-driven track must NOT add new lifecycle edges"
        )

    def test_valid_transitions_is_exactly_five_edges(self) -> None:
        """VALID_TRANSITIONS runtime projection must have exactly 6 source nodes (brainstorm added)."""
        assert len(state_machine.VALID_TRANSITIONS) == 6, (
            f"expected 6 source nodes in VALID_TRANSITIONS, got "
            f"{len(state_machine.VALID_TRANSITIONS)}: {sorted(state_machine.VALID_TRANSITIONS)}"
        )

    def test_valid_transitions_unchanged(self) -> None:
        """VALID_TRANSITIONS is the canonical 6-edge runtime projection including brainstorm."""
        assert state_machine.VALID_TRANSITIONS == self.EXPECTED_VALID_TRANSITIONS, (
            "VALID_TRANSITIONS was mutated — goal-driven track must NOT add new runtime transitions"
        )

    def test_lifecycle_graph_has_no_extra_nodes(self) -> None:
        """No unexpected phase node beyond the canonical brainstorm-phase set."""
        expected_nodes = frozenset(self.EXPECTED_LIFECYCLE_GRAPH)
        actual_nodes = frozenset(phase_graph.LIFECYCLE_GRAPH)
        assert actual_nodes == expected_nodes, (
            f"extra nodes in LIFECYCLE_GRAPH: {actual_nodes - expected_nodes}; "
            f"missing nodes: {expected_nodes - actual_nodes}"
        )

    def test_terminal_phases_unchanged(self) -> None:
        """TERMINAL_PHASES must still be exactly {'resolved', 'aborted'}."""
        assert state_machine.TERMINAL_PHASES == {"resolved", "aborted"}, (
            f"TERMINAL_PHASES was mutated: {state_machine.TERMINAL_PHASES}"
        )


# ---------------------------------------------------------------------------
# Group 2: Standard run defaults
# ---------------------------------------------------------------------------


class TestStandardRunDefaults:
    """A RunManifest or handle_init with no track args must yield standard-track defaults."""

    def test_run_manifest_default_track(self) -> None:
        """RunManifest constructed without track= must default to 'standard'."""
        m = RunManifest(run_id="pin-001", authority=Authority(source="test"))
        assert m.track == "standard", f"expected track='standard', got {m.track!r}"

    def test_run_manifest_default_goal_id(self) -> None:
        """RunManifest constructed without goal_id= must have goal_id is None."""
        m = RunManifest(run_id="pin-002", authority=Authority(source="test"))
        assert m.goal_id is None, f"expected goal_id=None, got {m.goal_id!r}"

    def test_run_manifest_default_inherits_from(self) -> None:
        """RunManifest constructed without inherits_from= must have inherits_from is None."""
        m = RunManifest(run_id="pin-003", authority=Authority(source="test"))
        assert m.inherits_from is None, (
            f"expected inherits_from=None, got {m.inherits_from!r}"
        )

    def test_run_manifest_default_inherited_artifacts(self) -> None:
        """RunManifest constructed without inherited_artifacts= must have empty dict."""
        m = RunManifest(run_id="pin-004", authority=Authority(source="test"))
        assert m.inherited_artifacts == {}, (
            f"expected inherited_artifacts={{}}, got {m.inherited_artifacts!r}"
        )

    def test_handle_init_default_track(self, temp_uacp_root: Path) -> None:
        """handle_init with no track arg must create a manifest with track='standard'."""
        result_json = state_machine.handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "handle-pin-001",
            "source": "operator-request",
        })
        result = json.loads(result_json)
        assert result.get("ok") is True, f"handle_init failed: {result}"

        # Read the manifest back and check
        m = state_machine._load_manifest(temp_uacp_root, "handle-pin-001")
        assert m.track == "standard", f"expected track='standard', got {m.track!r}"
        assert m.goal_id is None, f"expected goal_id=None, got {m.goal_id!r}"
        assert m.inherits_from is None, (
            f"expected inherits_from=None, got {m.inherits_from!r}"
        )
        assert m.inherited_artifacts == {}, (
            f"expected inherited_artifacts={{}}, got {m.inherited_artifacts!r}"
        )

    def test_handle_init_explicit_standard_track(self, temp_uacp_root: Path) -> None:
        """handle_init with track='standard' must also yield a standard-track manifest."""
        result_json = state_machine.handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "handle-pin-002",
            "source": "operator-request",
            "track": "standard",
        })
        result = json.loads(result_json)
        assert result.get("ok") is True, f"handle_init failed: {result}"

        m = state_machine._load_manifest(temp_uacp_root, "handle-pin-002")
        assert m.track == "standard", f"expected track='standard', got {m.track!r}"
        assert m.goal_id is None
        assert m.inherited_artifacts == {}


# ---------------------------------------------------------------------------
# Group 3: Standard gates untouched
# ---------------------------------------------------------------------------


def _seed_standard_manifest(root: Path, run_id: str) -> None:
    """Write a standard-track run manifest under .uacp/state/runs/."""
    m = RunManifest(
        run_id=run_id,
        authority=Authority(source="operator-request"),
        track="standard",
        current_phase="execute",
    )
    _save_manifest(root, m)


class TestStandardGatesUntouched:
    """Standard-track execute->verify and verify->resolve gates run standard bodies.

    Key invariants:
    - ``_run_track`` returns ``"standard"`` for a standard manifest.
    - No checkpoint/manifest/convergence_budget-flavoured blocker fires.
    - The gates produce only the standard PIV/evidence blockers they produced
      pre-feature (missing artifacts, not goal-driven extras).
    """

    def test_run_track_returns_standard_for_standard_manifest(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """_run_track must return 'standard' when the manifest carries track='standard'."""
        from core import Heartgate

        _seed_standard_manifest(temp_uacp_root, valid_run_id)
        hg = Heartgate.load(str(temp_uacp_root))
        track = hg._run_track(valid_run_id)
        assert track == "standard", (
            f"expected _run_track to return 'standard' for a standard manifest, got {track!r}"
        )

    def test_execute_verify_gate_no_checkpoint_blocker_for_standard(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """Standard execute->verify: NO goal-driven checkpoint/manifest/convergence_budget blocker fires.

        The gate must only emit the standard PIV/evidence blockers (missing piv.yaml,
        missing checkpoint artifact, missing execution package dir) — none of the
        goal-driven checkpoint manifest / convergence_budget flavoured messages.
        """
        from core import Heartgate

        _seed_standard_manifest(temp_uacp_root, valid_run_id)
        hg = Heartgate.load(str(temp_uacp_root))

        artifact = {
            "from_phase": "execute",
            "to_phase": "verify",
            "run_id": valid_run_id,
        }
        blockers: list[str] = []
        hg._validate_adaptive_execute_evidence_gate(artifact, blockers)

        # Goal-driven-only blocker signatures must NOT appear
        goal_driven_signatures = (
            "goal-driven",
            "checkpoint manifest",
            "checkpoint_manifest",
            "convergence_budget",
            "convergence budget",
            "gate: CHECKPOINT",
            "max_checkpoints",
        )
        for sig in goal_driven_signatures:
            goal_driven_hits = [b for b in blockers if sig.lower() in b.lower()]
            assert not goal_driven_hits, (
                f"Standard execute->verify gate emitted goal-driven blocker "
                f"(signature {sig!r}): {goal_driven_hits}"
            )

        # The standard gate MUST fire its standard PIV/evidence checks — it must NOT
        # silently pass.  Confirm standard blockers are present (the artifacts don't
        # exist in this temp root, so the standard gate will block on their absence).
        assert blockers, (
            "Standard execute->verify gate produced NO blockers at all — "
            "the standard evidence gate was silently bypassed (wrong branch taken)"
        )
        standard_signatures = ("piv", "checkpoint", "execution package", "adaptive_execute_evidence_gate")
        assert any(
            any(sig.lower() in b.lower() for sig in standard_signatures) for b in blockers
        ), (
            f"Expected standard PIV/evidence blocker signatures in blockers but found none: {blockers}"
        )

    def test_verify_resolve_gate_no_checkpoint_blocker_for_standard(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """Standard verify->resolve: NO goal-driven checkpoint/manifest/convergence_budget blocker fires.

        The gate must only emit the standard verify-selection / resolve-readiness
        blockers — none of the goal-driven checkpoint manifest / convergence_budget
        flavoured messages.
        """
        from core import Heartgate

        _seed_standard_manifest(temp_uacp_root, valid_run_id)
        hg = Heartgate.load(str(temp_uacp_root))

        artifact = {
            "from_phase": "verify",
            "to_phase": "resolve",
            "run_id": valid_run_id,
        }
        blockers: list[str] = []
        hg._validate_adaptive_verify_evidence_gate(artifact, blockers)

        # Goal-driven-only blocker signatures must NOT appear
        goal_driven_signatures = (
            "goal-driven",
            "checkpoint manifest",
            "checkpoint_manifest",
            "convergence_budget",
            "convergence budget",
            "goal_id",
            "goal binding",
            "max_checkpoints",
        )
        for sig in goal_driven_signatures:
            goal_driven_hits = [b for b in blockers if sig.lower() in b.lower()]
            assert not goal_driven_hits, (
                f"Standard verify->resolve gate emitted goal-driven blocker "
                f"(signature {sig!r}): {goal_driven_hits}"
            )

        # The standard gate MUST fire its standard verify-evidence checks.
        assert blockers, (
            "Standard verify->resolve gate produced NO blockers at all — "
            "the standard evidence gate was silently bypassed (wrong branch taken)"
        )
        standard_signatures = (
            "verify-selection",
            "resolve-readiness",
            "adaptive_verify_evidence_gate",
            "verification package",
        )
        assert any(
            any(sig.lower() in b.lower() for sig in standard_signatures) for b in blockers
        ), (
            f"Expected standard verify-evidence blocker signatures but found none: {blockers}"
        )

    def test_no_goal_id_in_standard_manifest(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """_run_track resolves to 'standard' and goal_id stays None on a standard manifest."""
        from core import Heartgate

        _seed_standard_manifest(temp_uacp_root, valid_run_id)
        hg = Heartgate.load(str(temp_uacp_root))
        assert hg._run_track(valid_run_id) == "standard"
        # Also confirm _run_goal_id returns '' (no goal binding)
        assert hg._run_goal_id(valid_run_id) == "", (
            f"_run_goal_id should return '' for a standard run, got {hg._run_goal_id(valid_run_id)!r}"
        )


# ---------------------------------------------------------------------------
# Group 4: _run_track fail-safe
# ---------------------------------------------------------------------------


class TestRunTrackFailSafe:
    """_run_track must return 'standard' and never raise on bad/missing manifests."""

    def test_missing_manifest_returns_standard(
        self, temp_uacp_root: Path
    ) -> None:
        """_run_track returns 'standard' when the manifest file does not exist."""
        from core import Heartgate

        hg = Heartgate.load(str(temp_uacp_root))
        result = hg._run_track("run-that-does-not-exist")
        assert result == "standard", (
            f"_run_track with missing manifest must return 'standard', got {result!r}"
        )

    def test_garbled_yaml_manifest_returns_standard(
        self, temp_uacp_root: Path
    ) -> None:
        """_run_track returns 'standard' when the manifest YAML is unparseable."""
        from core import Heartgate

        run_id = "garbled-run-001"
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{run_id}.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            ":\t::: not valid yaml {{{{ ]]]", encoding="utf-8"
        )

        hg = Heartgate.load(str(temp_uacp_root))
        result = hg._run_track(run_id)
        assert result == "standard", (
            f"_run_track with garbled manifest must return 'standard', got {result!r}"
        )

    def test_manifest_missing_track_field_returns_standard(
        self, temp_uacp_root: Path
    ) -> None:
        """_run_track returns 'standard' when the manifest exists but has no track field."""
        from core import Heartgate

        run_id = "no-track-field-run-001"
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{run_id}.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        # Write a minimal valid YAML mapping but deliberately omit the 'track' key
        import yaml as _yaml
        manifest_path.write_text(
            _yaml.safe_dump({"run_id": run_id, "status": "active", "current_phase": "execute"}),
            encoding="utf-8",
        )

        hg = Heartgate.load(str(temp_uacp_root))
        result = hg._run_track(run_id)
        assert result == "standard", (
            f"_run_track with no track field must return 'standard', got {result!r}"
        )

    def test_manifest_track_null_returns_standard(
        self, temp_uacp_root: Path
    ) -> None:
        """_run_track returns 'standard' when the manifest has track: null."""
        from core import Heartgate

        run_id = "null-track-run-001"
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{run_id}.yaml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        import yaml as _yaml
        manifest_path.write_text(
            _yaml.safe_dump({
                "run_id": run_id,
                "status": "active",
                "current_phase": "execute",
                "track": None,
            }),
            encoding="utf-8",
        )

        hg = Heartgate.load(str(temp_uacp_root))
        result = hg._run_track(run_id)
        assert result == "standard", (
            f"_run_track with track: null must return 'standard', got {result!r}"
        )

    def test_unsafe_run_id_returns_standard(self, temp_uacp_root: Path) -> None:
        """_run_track returns 'standard' for a path-unsafe run_id (never raises)."""
        from core import Heartgate

        hg = Heartgate.load(str(temp_uacp_root))
        # Path traversal attempt — _is_safe_run_id should reject it
        result = hg._run_track("../../../etc/passwd")
        assert result == "standard", (
            f"_run_track with unsafe run_id must return 'standard', got {result!r}"
        )

    def test_empty_run_id_returns_standard(self, temp_uacp_root: Path) -> None:
        """_run_track returns 'standard' for an empty run_id (never raises)."""
        from core import Heartgate

        hg = Heartgate.load(str(temp_uacp_root))
        result = hg._run_track("")
        assert result == "standard", (
            f"_run_track with empty run_id must return 'standard', got {result!r}"
        )

"""TDD tests for Phase 1 state machine (init, read, transition, register-artifact, finalize)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from state_machine import (
    VALID_TRANSITIONS,
    Authority,
    RunManifest,
    Status,
    _gates_for_exit,
    _run_forced_brainstorm_exit_gate,
    _run_forced_execute_evidence_gate,
    _run_forced_plan_exit_gate,
    _run_forced_proposal_coverage_gate,
    _run_forced_propose_grounding_gate,
    _run_forced_triage_grounding_gate,
    _run_forced_verify_evidence_gate,
    handle_finalize,
    handle_init,
    handle_read,
    handle_register_artifact,
    handle_transition,
    resolve_gates,
)


class TestRunManifestSchema:
    """Pydantic schema validation for RunManifest."""

    def test_valid_manifest(self):
        manifest = RunManifest(
            run_id="uacp-test-001",
            status=Status.active,
            current_phase="triage",
            created_at="2026-06-07T12:00:00Z",
            authority={"source": "operator-request", "status": "pass"},
        )
        assert manifest.run_id == "uacp-test-001"
        assert manifest.status == Status.active
        assert manifest.current_phase == "triage"

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="uacp-test-001",
                status="invalid_status",
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_rejects_run_id_with_traversal(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="../../../etc/passwd",
                status=Status.active,
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_rejects_run_id_with_whitespace(self):
        with pytest.raises(ValueError):
            RunManifest(
                run_id="uacp test 001",
                status=Status.active,
                current_phase="triage",
                created_at="2026-06-07T12:00:00Z",
            )

    def test_default_empty_artifacts(self):
        manifest = RunManifest(
            run_id="uacp-test-001",
            status=Status.active,
            current_phase="triage",
            created_at="2026-06-07T12:00:00Z",
            authority=Authority(source="test"),
        )
        assert manifest.artifacts == {}
        assert manifest.state_history == []


class TestStateMachineInit:
    """Tests for handle_init."""

    def test_creates_run_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
            "scope": "software",
            "granularity": "medium",
            "risk": "medium",
        }))
        assert result["ok"] is True
        assert result["run_id"] == "uacp-test-001"

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        assert manifest_path.exists()
        # C-1: manifest lands under .uacp/, never the flat root.
        assert not (temp_uacp_root / "state" / "runs" / "uacp-test-001.yaml").exists()
        data = yaml.safe_load(manifest_path.read_text())
        assert data["run_id"] == "uacp-test-001"
        assert data["status"] == "active"
        assert data["current_phase"] == "triage"
        assert data["authority"]["source"] == "operator-request"
        assert data["authority"]["status"] == "pass"

    def test_rejects_duplicate_run_id(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        }))
        assert "error" in result
        assert "already exists" in result["error"]

    def test_creates_current_pointer_on_first_run(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        current_path = temp_uacp_root / ".uacp" / "state" / "current.yaml"
        assert current_path.exists()
        # C-1: pointer lands under .uacp/, never the flat root.
        assert not (temp_uacp_root / "state" / "current.yaml").exists()
        data = yaml.safe_load(current_path.read_text())
        assert data["active_run_id"] == "uacp-test-001"
        # Base-relative manifest ref (resolved under .uacp/), not .uacp/-prefixed.
        assert data["active_run_manifest"] == "state/runs/uacp-test-001.yaml"

    def test_does_not_overwrite_current_pointer(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-002",
            "source": "operator-request",
        })
        current_path = temp_uacp_root / ".uacp" / "state" / "current.yaml"
        data = yaml.safe_load(current_path.read_text())
        # First run stays active
        assert data["active_run_id"] == "uacp-test-001"


class TestStateMachineRead:
    """Tests for handle_read."""

    def test_reads_existing_manifest(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_read({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert result["ok"] is True
        assert result["manifest"]["run_id"] == "uacp-test-001"

    def test_rejects_missing_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_read({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert "error" in result
        assert "not found" in result["error"]


class TestStateMachineTransition:
    """Tests for handle_transition."""

    def test_valid_transition(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "triage",
            "to_phase": "propose",
        }))
        assert result["ok"] is True
        assert result["from_phase"] == "triage"
        assert result["to_phase"] == "propose"

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["current_phase"] == "propose"
        assert len(data["state_history"]) == 1
        assert data["state_history"][0]["event"] == "phase_transition"

    def test_rejects_invalid_transition(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "triage",
            "to_phase": "execute",  # Invalid: triage -> execute not allowed
        }))
        assert "error" in result
        assert "not allowed" in result["error"]

    def test_rejects_wrong_current_phase(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "propose",  # Wrong: current is triage
            "to_phase": "plan",
        }))
        assert "error" in result
        assert "current phase" in result["error"]

    def test_rejects_transition_from_terminal_state(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        # Mark as resolved
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        data["status"] = "resolved"
        data["current_phase"] = "resolved"
        manifest_path.write_text(yaml.safe_dump(data))

        result = json.loads(handle_transition({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "from_phase": "resolved",
            "to_phase": "triage",
        }))
        assert "error" in result
        # #107: the guard now refuses ANY non-active run (resolved included) with a
        # status-anchored message, not only the current_phase-terminal wording.
        assert "not active" in result["error"]


class TestStateMachineRegisterArtifact:
    """Tests for handle_register_artifact."""

    def test_registers_artifact(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "proposals/uacp-test-001-triage.yaml",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["artifacts"]["triage"] == "proposals/uacp-test-001-triage.yaml"

    def test_rejects_missing_manifest(self, temp_uacp_root: Path):
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "proposals/test.yaml",
        }))
        assert "error" in result
        assert "not found" in result["error"]

    def test_rejects_path_traversal_in_artifact_path(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_register_artifact({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "artifact_type": "triage",
            "path": "../../../etc/passwd",
        }))
        assert "error" in result
        assert "escapes" in result["error"]


class TestStateMachineFinalize:
    """Tests for handle_finalize."""

    def test_finalize_blocked_when_run_not_closeable(self, temp_uacp_root: Path):
        """A run driven to the terminal phase but NOT actually closeable (no
        lessons/closure artifact, etc.) must be REFUSED by handle_finalize: the
        closure sweep is now wired onto the live finalize path. The block must
        also REVERT — the run is left un-finalized to be fixed and retried.

        The closeable-run positive (finalize succeeds + stamps finalized_at) is
        covered end-to-end in tests/e2e/test_finalize_closure_gate.py, which drives
        a genuinely closeable run through the real kernel.
        """
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        # #99: the forced plan-exit gates now block a bare plan->execute; seed the faithful
        # scope + PLAN_VALIDATION prerequisites so the run can REACH resolved and the test can
        # assert finalize blocks on the missing CLOSURE artifact (its actual subject), not on
        # a stuck plan phase. The lessons/closure artifact stays deliberately unauthored.
        from tests.e2e.test_full_lifecycle import seed_plan_exit_prerequisites

        seed_plan_exit_prerequisites(temp_uacp_root, "uacp-test-001")
        # Move through phases to resolved (structural transitions only — no
        # lessons artifact authored, so the run is NOT closeable).
        for frm, to in [
            ("triage", "propose"),
            ("propose", "plan"),
            ("plan", "execute"),
            ("execute", "verify"),
            ("verify", "resolved"),
        ]:
            handle_transition({
                "workspace": str(temp_uacp_root),
                "run_id": "uacp-test-001",
                "from_phase": frm,
                "to_phase": to,
            })

        result = json.loads(handle_finalize({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        # Refused by the closure sweep, with the engine blocker(s) surfaced.
        assert "error" in result, result
        assert result.get("decision") == "block", result
        assert any("C4_CLOSURE_ARTIFACT_MISSING" in b for b in result.get("blockers", [])), result

        # Reverted: the run is NOT finalized.
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-test-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["finalized_at"] is None

    def test_rejects_finalize_from_non_terminal_phase(self, temp_uacp_root: Path):
        handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
            "source": "operator-request",
        })
        result = json.loads(handle_finalize({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-test-001",
        }))
        assert "error" in result
        assert "not in terminal phase" in result["error"]


class TestRunManifestTrackFields:
    """Tests for the new track/goal_id/inherits_from fields on RunManifest."""

    def test_defaults_when_not_set(self):
        """RunManifest with none of the new fields set has standard defaults."""
        manifest = RunManifest(
            run_id="uacp-test-defaults",
            authority=Authority(source="test"),
        )
        assert manifest.track == "standard"
        assert manifest.goal_id is None
        assert manifest.inherits_from is None

    def test_goal_driven_track_fields_accepted(self):
        """RunManifest accepts goal-driven track with goal_id and inherits_from."""
        manifest = RunManifest(
            run_id="uacp-test-gd",
            authority=Authority(source="test"),
            track="goal-driven",
            goal_id="g1",
            inherits_from="run-A",
        )
        assert manifest.track == "goal-driven"
        assert manifest.goal_id == "g1"
        assert manifest.inherits_from == "run-A"

    def test_standard_track_explicit(self):
        """RunManifest with explicit track='standard' is identical to default."""
        manifest = RunManifest(
            run_id="uacp-test-explicit",
            authority=Authority(source="test"),
            track="standard",
        )
        assert manifest.track == "standard"
        assert manifest.goal_id is None
        assert manifest.inherits_from is None


class TestHandleInitTrackFields:
    """Tests that handle_init threads track/goal_id/inherits_from into the manifest."""

    def test_goal_driven_fields_persisted(self, temp_uacp_root: Path):
        """handle_init with goal-driven args writes them into the manifest YAML.

        Task 3 makes ``inherits_from`` a resolved link (fail-closed if the
        parent manifest is absent), so a real parent run-A must exist.
        """
        json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "run-A",
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g1",
        }))
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-gd-001",
            "source": "operator-request",
            "track": "goal-driven",
            "goal_id": "g1",
            "inherits_from": "run-A",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-gd-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["track"] == "goal-driven"
        assert data["goal_id"] == "g1"
        assert data["inherits_from"] == "run-A"

    def test_standard_run_defaults_in_manifest(self, temp_uacp_root: Path):
        """handle_init without new args produces a manifest with standard defaults."""
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-std-001",
            "source": "operator-request",
        }))
        assert result["ok"] is True

        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-std-001.yaml"
        data = yaml.safe_load(manifest_path.read_text())
        assert data["track"] == "standard"
        assert data["goal_id"] is None
        assert data["inherits_from"] is None
        # Existing fields must still be present
        assert data["run_id"] == "uacp-std-001"
        assert data["status"] == "active"
        assert data["current_phase"] == "triage"

    def test_invalid_track_returns_error(self, temp_uacp_root: Path):
        """handle_init with an unknown track returns a JSON error, no manifest written."""
        result = json.loads(handle_init({
            "workspace": str(temp_uacp_root),
            "run_id": "uacp-bad-track",
            "source": "operator-request",
            "track": "turbo-mode",
        }))
        assert "error" in result
        assert "track" in result["error"].lower()
        # No manifest should have been created
        manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / "uacp-bad-track.yaml"
        assert not manifest_path.exists()


class TestStructuralGateResolverInvariant:
    """M1 (D-01 / D-02): the phase-keyed structural gate identities live in ONE place
    now — ``resolve_gates`` / ``_PHASE_GATE_TABLE``. These equality-invariant tests pin
    that the read-only naming (``_gates_for_exit`` / ``next.will_be_gated_on``) and the
    live forced-gate dispatch BOTH derive from the resolver, so a gate added in one
    place but not the resolver can no longer hide. Grounded against an INDEPENDENT spec
    (the design intent) so re-hardcoding a gate elsewhere is caught, not rubber-stamped.
    """

    # The design-intent mapping, authored here independently of the implementation so
    # the assertions are non-vacuous: the SET of tokens uniquely identifying each phase's
    # forced gate(s) — M2 generalized ``forced`` to a TUPLE, so a phase may carry more than
    # one — and the set of phases whose exit is structural-graph-gated (D35). ``triage`` gains
    # its grounding gate here (was absent before M2); graph-gating is UNCHANGED (triage is NOT
    # graph-gated), pinning that PART A did not alter the graph-gate set. ``propose`` carries TWO
    # forced gates (grounded-governance node 06): its original coverage gate PLUS the new grounding
    # gate — a non-vacuous TWO-token set, pinning both are present (one gate per token).
    _EXPECTED_FORCED_TOKENS = {
        "brainstorm": {"forced_brainstorm_exit"},
        "triage": {"forced_triage_grounding"},
        "propose": {"forced_proposal_coverage", "forced_propose_grounding"},
        "plan": {"forced_plan_exit"},
        "execute": {"forced_execute_evidence"},
        "verify": {"forced_verify_evidence"},
    }
    _EXPECTED_GRAPH_GATED = {"plan", "execute", "verify"}

    def test_table_matches_independent_spec(self):
        """The resolver table agrees with the independent design-intent spec for every
        from_phase: graph-gating exactly on {plan, execute, verify}; a forced-gate TUPLE whose
        labels carry exactly the expected token set on each gated phase (one gate per token);
        an EMPTY tuple elsewhere."""
        for phase in VALID_TRANSITIONS:
            spec = resolve_gates(phase)
            assert spec.graph_gated == (phase in self._EXPECTED_GRAPH_GATED), phase
            labels = [g.label for g in spec.forced]
            if phase in self._EXPECTED_FORCED_TOKENS:
                expected_tokens = self._EXPECTED_FORCED_TOKENS[phase]
                # one forced gate per expected token, each label carrying its token.
                assert len(labels) == len(expected_tokens), (phase, labels)
                for token in expected_tokens:
                    assert any(token in lbl for lbl in labels), (phase, token, labels)
            else:
                assert spec.forced == (), phase

    def test_gates_for_exit_derives_from_resolver(self):
        """The read-only naming is exactly the resolver's projection: canonical FROM->TO
        records (incl. TRIAGE_COMPLETE at triage), then the ``{phase}_exit`` graph-gate
        label iff graph_gated, then EVERY forced gate's label in tuple order. Terminal
        phases (no onward crossing) name nothing."""
        for phase in list(VALID_TRANSITIONS) + ["resolved"]:
            spec = resolve_gates(phase)
            if not spec.canonical:
                assert _gates_for_exit(phase) is None, phase
                continue
            expected = list(spec.canonical)
            if spec.graph_gated:
                expected.append(f"{phase}_exit structural graph gate")
            for g in spec.forced:
                expected.append(g.label)
            assert _gates_for_exit(phase) == expected, phase

    def test_canonical_records_match_valid_transitions(self):
        """``canonical`` is the FROM->TO record for every onward target in
        VALID_TRANSITIONS (plus TRIAGE_COMPLETE at triage exit) — not a hand-list."""
        for phase, targets in VALID_TRANSITIONS.items():
            expected = [f"{phase.upper()}->{t.upper()}" for t in sorted(targets)]
            if phase == "triage" and expected:
                expected.append("TRIAGE_COMPLETE")
            assert resolve_gates(phase).canonical == expected, phase

    def test_resolver_forced_executor_self_selects_to_its_phase(self, tmp_path: Path):
        """The live dispatch == the resolver: EVERY forced executor the resolver selects
        for phase P is a self-selecting wrapper for P. Proven without IO — handing any of
        that phase's executors ANY other from_phase makes it a no-op (the wrapper's
        from_phase guard short-circuits before touching state), so each is genuinely keyed
        to P and the tuple-iterating dispatch reproduces the old 'run all, own fires' chain."""
        gated_phases = list(self._EXPECTED_FORCED_TOKENS)
        for own_phase in gated_phases:
            forced_tuple = resolve_gates(own_phase).forced
            assert forced_tuple, own_phase  # non-empty tuple
            for g in forced_tuple:
                for other in gated_phases:
                    if other == own_phase:
                        continue
                    # Non-matching from_phase -> the selected executor short-circuits to a
                    # no-op (no run/workspace needed), proving it self-selects to own_phase.
                    # Arity-agnostic: simple wrappers no-op to ([], []); grounding gates to
                    # ([], [], []). Either way every list is empty when it self-selects away.
                    assert not any(g.run(tmp_path, "no-such-run", other, other)), (
                        own_phase,
                        other,
                    )

    def test_each_wrapper_is_noop_for_other_phases(self, tmp_path: Path):
        """Direct proof of self-selection at the wrapper level (what makes the old chain
        and the new tuple-iterating dispatch equivalent): every ``_run_forced_*`` wrapper
        returns an empty result for every phase but its own, short-circuiting before any IO."""
        simple = {
            "brainstorm": _run_forced_brainstorm_exit_gate,
            "propose": _run_forced_proposal_coverage_gate,
            "execute": _run_forced_execute_evidence_gate,
            "verify": _run_forced_verify_evidence_gate,
        }
        phases = list(VALID_TRANSITIONS)
        for own_phase, fn in simple.items():
            for other in phases:
                if other == own_phase:
                    continue
                assert fn(tmp_path, "no-such-run", other) == [], (own_phase, other)
        # plan_exit + triage_grounding + propose_grounding self-select too. plan_exit no-ops to
        # (blockers, advisories); the grounding gates ALWAYS return 3-tuples ((blockers, advisories,
        # findings)) so their no-op is ([], [], []).
        for other in phases:
            if other != "plan":
                assert _run_forced_plan_exit_gate(tmp_path, "no-such-run", other, "x") == (
                    [],
                    [],
                ), other
            if other != "triage":
                assert _run_forced_triage_grounding_gate(
                    tmp_path, "no-such-run", other, "x"
                ) == ([], [], []), other
            if other != "propose":
                assert _run_forced_propose_grounding_gate(
                    tmp_path, "no-such-run", other, "x"
                ) == ([], [], []), other

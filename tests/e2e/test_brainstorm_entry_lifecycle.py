"""E2E: a run that starts at brainstorm, gates the real brainstorm→triage invariant,
then advances to triage through real handlers.

Drives:
  - state_machine.handle_init  with initial_phase="brainstorm"  (REAL handler)
  - heartgate.validate_transition  brainstorm→triage  (REAL handler)
      * BLOCK when 07-scope-package.yaml is absent (invariant gate open)
      * PASS  when 07-scope-package.yaml is present (invariant gate closed)
  - state_machine.handle_transition  brainstorm→triage  (REAL handler)
  - assert manifest.current_phase == "triage"

Seam used: the scope-package artifact is written DIRECTLY to the resolved
governed path (.uacp/brainstorm/<run_id>/07-scope-package.yaml) because
`uacp_artifact_write` does not support the `brainstorm/` root (its allowed
set is plans/proposals/executions/verification/resolutions/knowledge).  This
is intentional test scaffolding — the real handler boundary is Heartgate's
`_validate_phase_exit_invariants` which globs the file; we prove it gates the
real transition by showing BLOCK without the file and PASS with it.

Config note: the conftest's minimal phase-transitions.yaml provides a `stages`
block that only covers triage→resolved, so the code-default brainstorm stage
(with its 07-scope-package.yaml exit invariant) would be absent.  This test
therefore rewrites the config file to OMIT the `stages` key entirely, which
triggers load_phase_transitions to inject stages_default() — the full codified
grammar including the brainstorm invariant.  All other opt-out keys (piv_rule,
plan_validation_gate, etc.) are preserved so no other lifecycle test is
affected.
"""

from __future__ import annotations

from pathlib import Path

import state_machine
import yaml
from core import Heartgate
from state import _handle_uacp_gate_ledger_append

from tests.e2e.driver import Driver

# ── Config helpers ──────────────────────────────────────────────────────────

def _write_brainstorm_config(root: Path) -> None:
    """Rewrite config/phase-transitions.yaml WITHOUT a 'stages' key so that
    load_phase_transitions injects stages_default() (which includes brainstorm
    with the 07-scope-package.yaml exit invariant).

    The opt-out knobs that test_full_lifecycle relies on (piv_rule,
    plan_validation_gate, heartgate_coherence_required_when, artifact_schema)
    are reproduced verbatim so this rewrite does not perturb any other test.
    """
    cfg = {
        # No 'stages' key → code default injected by load_phase_transitions.
        # Opt-out knobs preserved from conftest to keep other lifecycle tests green.
        "heartgate_coherence_required_when": {},
        "plan_validation_gate": {},
        "piv_rule": {"ledger_required": False},
        "artifact_schema": {"required_fields": []},
    }
    phase_path = root / "config" / "phase-transitions.yaml"
    phase_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


# ── Artifact seeders ─────────────────────────────────────────────────────────

def _seed_scope_package(root: Path, run_id: str) -> Path:
    """Write a minimal but valid 07-scope-package.yaml to the governed path that
    the brainstorm exit invariant globs: brainstorm/<run_id>/07-scope-package.yaml.

    Written DIRECTLY to the resolved path because uacp_artifact_write does not
    support the brainstorm/ root (allowed: plans/proposals/executions/verification
    /resolutions/knowledge).  This is the resolved-path seam documented in the
    module docstring.
    """
    pkg_dir = root / ".uacp" / "brainstorm" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    scope_pkg = pkg_dir / "07-scope-package.yaml"
    scope_pkg.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.brainstorm.scope_package",
                "run_id": run_id,
                "title": "E2E brainstorm scope package",
                "description": "Minimal scope package for the brainstorm entry e2e test.",
                "in_scope": ["verify brainstorm→triage gate with real handler"],
                "declared_side_effects": [],
                "authority": {"source": "e2e-test-harness"},
                "routing_advisory": "standard",
            },
            sort_keys=False,
        )
    )
    return scope_pkg


# ── Tests ────────────────────────────────────────────────────────────────────

class TestBrainstormEntryLifecycle:
    """A run starting at brainstorm advances to triage through real handlers."""

    def test_init_at_brainstorm(self, temp_uacp_root: Path, valid_run_id: str) -> None:
        """handle_init with initial_phase='brainstorm' creates a manifest in
        brainstorm phase."""
        _write_brainstorm_config(temp_uacp_root)
        d = Driver(temp_uacp_root, valid_run_id)
        result = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_init(a),
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "source": "operator-request",
                "initial_phase": "brainstorm",
            },
            phase="brainstorm",
        )
        assert result.get("ok") is True, result
        # Verify manifest starts in brainstorm
        manifest = yaml.safe_load(
            (temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml").read_text()
        )
        assert manifest["current_phase"] == "brainstorm"

    def test_brainstorm_to_triage_blocks_without_scope_package(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """Heartgate blocks brainstorm→triage when the scope-package is absent.

        This proves the real exit invariant gates the real transition — not a
        stub or mock.
        """
        _write_brainstorm_config(temp_uacp_root)
        # Init at brainstorm
        state_machine.handle_init(
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "source": "operator-request",
                "initial_phase": "brainstorm",
            }
        )
        heartgate = Heartgate.load(str(temp_uacp_root))
        # The scope-package is ABSENT — the invariant must block
        decision = heartgate.validate_transition(
            {
                "from_phase": "brainstorm",
                "to_phase": "triage",
                "run_id": valid_run_id,
                "artifact_path": "brainstorm/test.yaml",
            }
        )
        assert decision.decision == "block", (
            f"Expected Heartgate to BLOCK brainstorm→triage without scope-package, "
            f"got: {decision.decision!r} / blockers: {decision.blockers}"
        )
        assert any("07-scope-package" in b or "scope" in b.lower() for b in decision.blockers), (
            f"Expected a scope-package blocker, got: {decision.blockers}"
        )

    def test_brainstorm_to_triage_passes_with_scope_package(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """Heartgate passes brainstorm→triage when the scope-package is present."""
        _write_brainstorm_config(temp_uacp_root)
        state_machine.handle_init(
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "source": "operator-request",
                "initial_phase": "brainstorm",
            }
        )
        _seed_scope_package(temp_uacp_root, valid_run_id)
        heartgate = Heartgate.load(str(temp_uacp_root))
        decision = heartgate.validate_transition(
            {
                "from_phase": "brainstorm",
                "to_phase": "triage",
                "run_id": valid_run_id,
                "artifact_path": "brainstorm/test.yaml",
            }
        )
        assert decision.decision == "pass", (
            f"Expected Heartgate to PASS brainstorm→triage with scope-package present, "
            f"got: {decision.decision!r} / blockers: {decision.blockers}"
        )

    def test_full_brainstorm_to_triage_advance(
        self, temp_uacp_root: Path, valid_run_id: str
    ) -> None:
        """Full e2e: init at brainstorm, gate passes, transition advances to triage."""
        _write_brainstorm_config(temp_uacp_root)
        d = Driver(temp_uacp_root, valid_run_id)
        heartgate = Heartgate.load(str(temp_uacp_root))

        # 1. Init at brainstorm
        init = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_init(a),
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "source": "operator-request",
                "initial_phase": "brainstorm",
            },
            phase="brainstorm",
        )
        assert init.get("ok") is True, init

        # 2. Append a gate-ledger entry for the brainstorm phase
        ledger = d.call(
            "uacp_gate_ledger_append",
            _handle_uacp_gate_ledger_append,
            {
                "uacp_run_id": valid_run_id,
                "uacp_phase": "brainstorm",
                "workspace": str(temp_uacp_root),
                "policy_version": "0.1",
                "declared_side_effects": [],
                "gate": "BRAINSTORM->TRIAGE",
                "record": {"result": "pass"},
                "authority_artifact": "brainstorm/test.yaml",
            },
            phase="brainstorm",
        )
        assert ledger.get("ok") is True, ledger

        # 3. Seed the scope-package — the real invariant requires it
        _seed_scope_package(temp_uacp_root, valid_run_id)

        # 4. Validate the transition through the real Heartgate
        hg = heartgate.validate_transition(
            {
                "from_phase": "brainstorm",
                "to_phase": "triage",
                "run_id": valid_run_id,
                "artifact_path": "brainstorm/test.yaml",
            }
        )
        assert hg.decision == "pass", (
            f"Heartgate blocked legit brainstorm→triage: {hg.blockers}"
        )

        # 5. Advance to triage through the real state machine
        tr = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_transition(a),
            {
                "workspace": str(temp_uacp_root),
                "run_id": valid_run_id,
                "from_phase": "brainstorm",
                "to_phase": "triage",
            },
            phase="brainstorm",
        )
        assert tr.get("ok") is True, tr

        # 6. Assert the manifest advanced to triage
        manifest = yaml.safe_load(
            (temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml").read_text()
        )
        assert manifest["current_phase"] == "triage", (
            f"Expected current_phase=='triage', got {manifest['current_phase']!r}"
        )
        transitions = [h for h in manifest["state_history"] if h["event"] == "phase_transition"]
        assert len(transitions) == 1
        assert transitions[0]["from_phase"] == "brainstorm"
        assert transitions[0]["to_phase"] == "triage"

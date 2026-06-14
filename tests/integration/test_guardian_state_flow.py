"""Integration tests for Guardian policy enforcement + state mutations."""

from __future__ import annotations

import json
from pathlib import Path


from core import DECISION_ALLOW_WITH_AUDIT, Guardian, GuardianEvent, GuardianPolicy, Heartgate
from state import (
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_registry_update,
    _handle_uacp_state_write,
)


def _make_event(
    tool_name: str,
    tool_args: dict,
    uacp_run_id: str = "uacp-test-001",
    uacp_phase: str = "triage",
    workspace: str = "/tmp",
    policy_version: str = "0.1",
    declared_authority: str = "plans/test.yaml",
    declared_side_effects: list | None = None,
    **kwargs,
) -> GuardianEvent:
    return GuardianEvent(
        runtime="test",
        adapter="test-adapter",
        event_type="tool_call",
        tool_provider="core",
        tool_name=tool_name,
        tool_args=tool_args,
        uacp_run_id=uacp_run_id,
        uacp_phase=uacp_phase,
        workspace=workspace,
        policy_version=policy_version,
        declared_authority=declared_authority,
        declared_side_effects=declared_side_effects or [],
        **kwargs,
    )


class TestGuardianToolClassification:
    """Verify Guardian correctly classifies state-mutation tools."""

    def test_state_write_is_classified_as_state_uacp(self, temp_uacp_root: Path, valid_run_id: str):
        policy = GuardianPolicy.load(str(temp_uacp_root))
        guardian = Guardian(policy)
        event = _make_event(
            "uacp_state_write",
            {"target_path": "state/test.yaml"},
            workspace=str(temp_uacp_root),
            uacp_run_id=valid_run_id,
        )
        decision = guardian.evaluate(event)
        assert decision.category == "state.uacp"
        assert decision.decision == DECISION_ALLOW_WITH_AUDIT

    def test_gate_ledger_is_classified_as_state_uacp(self, temp_uacp_root: Path, valid_run_id: str):
        policy = GuardianPolicy.load(str(temp_uacp_root))
        guardian = Guardian(policy)
        event = _make_event(
            "uacp_gate_ledger_append",
            {"gate": "TEST"},
            workspace=str(temp_uacp_root),
            uacp_run_id=valid_run_id,
        )
        decision = guardian.evaluate(event)
        assert decision.category == "state.uacp"
        assert decision.decision == DECISION_ALLOW_WITH_AUDIT

    def test_unknown_tool_classified_as_external_mutator(self, temp_uacp_root: Path):
        """Tools not in classification map with provider='core' are external.unknown_mutator."""
        policy = GuardianPolicy.load(str(temp_uacp_root))
        guardian = Guardian(policy)
        event = _make_event("some_random_tool", {})
        decision = guardian.evaluate(event)
        # Provider 'core' falls through to external.unknown_mutator (not unclassified)
        assert decision.category == "external.unknown_mutator"


class TestGateLedgerWithGuardian:
    """Verify gate ledger records include authority and are policy-aware."""

    def test_full_gate_ledger_flow(self, temp_uacp_root: Path, valid_run_id: str):
        policy = GuardianPolicy.load(str(temp_uacp_root))

        # Step 1: Guardian evaluates the tool call
        guardian = Guardian(policy)
        event = _make_event(
            "uacp_gate_ledger_append",
            {"gate": "PLAN->EXECUTE", "record": {"result": "pass"}},
            workspace=str(temp_uacp_root),
            uacp_run_id=valid_run_id,
            uacp_phase="triage",
        )
        decision = guardian.evaluate(event)
        assert decision.decision == DECISION_ALLOW_WITH_AUDIT

        # Step 2: State handler executes the mutation
        result = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "PLAN->EXECUTE",
            "record": {"result": "pass", "piv": "piv_1"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["gate"] == "PLAN->EXECUTE"

        # Step 3: Verify the ledger is append-only
        result2 = json.loads(_handle_uacp_gate_ledger_append({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "gate": "EXECUTE->VERIFY",
            "record": {"result": "pass", "piv": "piv_2"},
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result2["ok"] is True

        ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
        lines = ledger_path.read_text().strip().split("\n")
        assert len(lines) == 2
        records = [json.loads(line) for line in lines]
        assert records[0]["gate"] == "PLAN->EXECUTE"
        assert records[1]["gate"] == "EXECUTE->VERIFY"


class TestRunRegistryWithGuardian:
    """Verify run registry integrates with Guardian caller-binding."""

    def test_registry_prevents_cross_run_squatting(self, temp_uacp_root: Path):
        """A run cannot register another run's ID in the registry."""
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": "uacp-test-001",
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": "uacp-test-002",  # Different from caller
                "phase": "plan",
                "write_paths": ["plans/"],
                "scope_artifact_path": "plans/test-scope.yaml",
                "started_at": 1234567890,
            },
            "reason": "test cross-run squatting",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert "error" in result
        assert "registry mutations must be caller-owned" in result["error"]

    def test_full_register_deregister_flow(self, temp_uacp_root: Path, valid_run_id: str):
        # Register
        result = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "register",
            "entry": {
                "run_id": valid_run_id,
                "phase": "plan",
                "write_paths": ["plans/", "proposals/"],
                "scope_artifact_path": "plans/test-scope.yaml",
                "started_at": 1234567890,
            },
            "reason": "test register",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result["ok"] is True
        assert result["active_count"] == 1

        # Deregister
        result2 = json.loads(_handle_uacp_run_registry_update({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "verify",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "op": "deregister",
            "entry": {"run_id": valid_run_id},
            "reason": "test deregister",
            "authority_artifact": "plans/test-plan.yaml",
        }))
        assert result2["ok"] is True
        assert result2["active_count"] == 0


class TestStateWriteRestrictions:
    """Verify state write restrictions are enforced correctly."""

    def test_cannot_write_docs_via_state_write(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "docs/hacked.md",
            "content": "hacked",
            "reason": "test",
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result
        assert "may only write under state/" in result["error"]

    def test_cannot_overwrite_gate_ledger(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "state/gate-ledger/test.jsonl",
            "content": "fake",
            "reason": "test",
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result
        assert "use uacp_gate_ledger_append" in result["error"]

    def test_cannot_overwrite_run_registry(self, temp_uacp_root: Path, valid_run_id: str):
        result = json.loads(_handle_uacp_state_write({
            "uacp_run_id": valid_run_id,
            "uacp_phase": "plan",
            "workspace": str(temp_uacp_root),
            "policy_version": "0.1",
            "declared_side_effects": [],
            "target_path": "state/run-registry.yaml",
            "content": "hacked: true",
            "reason": "test",
            "authority_artifact": "plans/test.yaml",
        }))
        assert "error" in result
        assert "use uacp_run_registry_update" in result["error"]


class TestHeartgateIntegration:
    """Verify Heartgate loads and validates transitions."""

    def test_heartgate_loads_from_workspace(self, temp_uacp_root: Path):
        heartgate = Heartgate.load(str(temp_uacp_root))
        assert "triage" in heartgate.stages
        assert "propose" in heartgate.stages

    def test_heartgate_allows_valid_transition(self, temp_uacp_root: Path):
        heartgate = Heartgate.load(str(temp_uacp_root))
        decision = heartgate.validate_transition({
            "from_phase": "triage",
            "to_phase": "propose",
            "run_id": "uacp-test-001",
            "artifact_path": "plans/test.yaml",
        })
        assert decision.decision == "pass"
        assert decision.blockers == []

    def test_heartgate_blocks_invalid_transition(self, temp_uacp_root: Path):
        heartgate = Heartgate.load(str(temp_uacp_root))
        # propose -> triage is not in exits_to
        decision = heartgate.validate_transition({
            "from_phase": "propose",
            "to_phase": "triage",
            "run_id": "uacp-test-001",
            "artifact_path": "plans/test.yaml",
        })
        assert decision.decision == "block"
        assert any("not allowed" in b.lower() for b in decision.blockers)

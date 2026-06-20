"""Production-equivalence pins for codified ``stages`` grammar (Slice 4b T4d-1).

The ``stages.<phase>`` block was moved out of config/phase-transitions.yaml into
code (engines/domain/phase_transitions.py ``stages_default()``), with ``exits_to``
DERIVED from engines/domain/phase_graph.py. These tests PIN the code default to
the EXACT values that were in the production YAML before the T4d-1 slim
(captured from ``git show 1c281bc:config/phase-transitions.yaml``), guaranteeing
behavior-preservation. Any divergence == silent production change.

They also prove the two fail-open hazards the slim would otherwise introduce are
closed:
  * load_phase_transitions injects the default when the loaded config omits
    ``stages`` (so Heartgate / evidence-completeness / Guardian Layer-B all keep
    pre-slim behavior), and
  * Guardian Layer-B, fed the code-default stages, still BLOCKS a protected tool
    not in the phase allowlist and still BLOCKS an unknown phase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core import DECISION_BLOCK, Guardian, GuardianEvent, GuardianPolicy
from engines.domain import phase_graph
from engines.domain.phase_transitions import stages_default
from engines.io import load_phase_transitions

REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Pre-slim production stages values (literals from 1c281bc).
# ---------------------------------------------------------------------------
_PRESLIM_ALLOWED_TOOLS = {
    "brainstorm": [
        "Read",
        "Glob",
        "Grep",
        "Task",
        "Write",
        "uacp_state_write",
        "uacp_artifact_write",
        "uacp_heartgate_check",
    ],
    "triage": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_doc_write",
        "uacp_config_write",
    ],
    "propose": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_doc_write",
    ],
    "plan": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
    ],
    "execute": [
        "uacp_doc_write",
        "uacp_config_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_artifact_write",
        "uacp_gate_ledger_append",
        "uacp_contained_shell",
        "uacp_sandbox_check",
        "uacp_heartgate_check",
        "terminal",
        "execute_code",
    ],
    "verify": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
        "uacp_sandbox_check",
        "uacp_contained_shell",
    ],
    "resolve": [
        "uacp_artifact_write",
        "uacp_state_write",
        "uacp_run_registry_update",
        "uacp_escalation_event",
        "uacp_gate_ledger_append",
        "uacp_heartgate_check",
    ],
}

_PRESLIM_FORBIDDEN_TOOLS = {
    "brainstorm": ["terminal", "execute_code"],
    "triage": ["terminal", "execute_code"],
    "propose": ["terminal", "execute_code"],
    "plan": ["terminal", "execute_code"],
    "execute": [],
    "verify": ["terminal", "execute_code"],
    "resolve": ["terminal", "execute_code"],
}

_PRESLIM_EXITS_TO = {
    "brainstorm": ["triage"],  # this slice only; explore-and-bail is a follow-up
    "triage": ["propose", "terminal"],  # sorted; YAML had [propose, terminal]
    "propose": ["plan"],
    "plan": ["execute"],
    "execute": ["verify"],
    "verify": ["resolve"],
    "resolve": ["terminal"],
}

_PRESLIM_PHASE_EXIT_INVARIANTS = {
    "brainstorm": [
        {
            "artifact_glob": "brainstorm/*/07-scope-package.yaml",
            "required": True,
            "description": (
                "Brainstorm admission contract: a selected scope-package artifact must "
                "exist with non-empty title/description/in_scope, declared_side_effects "
                "present, authority.source documented, and a valid routing_advisory. "
                "Promoted from references/phase-8-admission.md."
            ),
        },
    ],
    "triage": [
        {"artifact_glob": "proposals/{run_id}-triage*.yaml", "required": True},
        {"gate_ledger_entry": "TRIAGE_COMPLETE", "required": True},
    ],
    "propose": [
        {"artifact_glob": "proposals/{run_id}*.yaml", "required": True},
        {"artifact_glob": "proposals/{run_id}*-gate-selection.yaml", "required": False},
        {
            "artifact_glob": "proposals/{run_id}*-package-selection.yaml",
            "required": False,
            "applies_when": "adaptive_proposal_package_selected",
            "description": (
                "Machine bridge for adaptive proposal documentation selection; "
                "required for selected medium/high consequence work before "
                "PROPOSE->PLAN."
            ),
        },
        {
            "package_directory": "proposals/{run_id}/",
            "required": False,
            "applies_when": "adaptive_proposal_package_selected",
            "description": (
                "Human-reviewable proposal package; YAML proposal artifacts are "
                "lifecycle envelopes, not the complete proposal."
            ),
        },
        {"gate_ledger_entry": "TRIAGE->PROPOSE", "required": True},
    ],
    # D35 (post-pre-slim, intentional): the graph_invariant kind was ADDED to
    # plan/execute/verify exits to enforce the structural seam at each transition.
    # This is a deliberate extension of the pre-slim grammar, not a regression; the
    # pin still asserts exact equality so any FURTHER drift is caught.
    "plan": [
        {"artifact_glob": "plans/{run_id}*", "required": True},
        {"gate_ledger_entry": "PROPOSE->PLAN", "required": True},
        {"graph_invariant": "plan_exit", "required": True},
    ],
    "execute": [
        {"artifact_glob": "executions/{run_id}*", "required": True},
        {"gate_ledger_entry": "PLAN->EXECUTE", "required": True},
        {"graph_invariant": "execute_exit", "required": True},
    ],
    "verify": [
        {"artifact_glob": "verification/{run_id}*", "required": True},
        {"gate_ledger_entry": "EXECUTE->VERIFY", "required": True},
        {"graph_invariant": "verify_exit", "required": True},
    ],
    "resolve": [
        {"artifact_glob": "resolutions/{run_id}*", "required": True},
        {"gate_ledger_entry": "VERIFY->RESOLVE", "required": True},
    ],
}

_PRESLIM_PURPOSE = {
    "brainstorm": "Exploration and scope clarification before entering UACP governance.",
    "triage": "Calibrate scope, score granularity, and route the request.",
    "propose": "Establish authority, scope, context, risk, and proposal viability.",
    "plan": "Convert approved proposal into bounded execution and verification strategy.",
    "execute": (
        "Perform bounded work through UACP-authorized Agent Council orchestration, "
        "Hermes Kanban coordination, delegated workers, selected runtimes, and "
        "approved tool/evidence adapters."
    ),
    "verify": "Validate completed work with context-selected evidence clusters.",
    "resolve": "Finalize outputs, archive artifacts, and emit lessons.",
}

_PRESLIM_ENTERS_FROM = {
    "brainstorm": ["none"],
    "triage": ["none", "brainstorm"],
    "propose": ["triage"],
    "plan": ["propose"],
    "execute": ["plan"],
    "verify": ["execute"],
    "resolve": ["verify"],
}

_PRESLIM_TRIAGE_ROUTING_OUTCOMES = {
    "direct": "terminal_direct",
    "lightweight": "propose",
    "standard_uacp": "propose",
    "full_governance": "propose",
    "block_or_clarify": "terminal_blocked",
}

_PHASES = ("brainstorm", "triage", "propose", "plan", "execute", "verify", "resolve")


@pytest.fixture(scope="module")
def stages() -> dict:
    return stages_default()


@pytest.mark.parametrize("phase", _PHASES)
def test_allowed_tools_pin(stages: dict, phase: str) -> None:
    assert stages[phase]["allowed_tools"] == _PRESLIM_ALLOWED_TOOLS[phase]


@pytest.mark.parametrize("phase", _PHASES)
def test_forbidden_tools_pin(stages: dict, phase: str) -> None:
    # execute must keep the present-and-empty list (terminal/execute_code allowed there).
    assert stages[phase]["forbidden_tools"] == _PRESLIM_FORBIDDEN_TOOLS[phase]


@pytest.mark.parametrize("phase", _PHASES)
def test_exits_to_pin(stages: dict, phase: str) -> None:
    assert stages[phase]["exits_to"] == _PRESLIM_EXITS_TO[phase]


def test_exits_to_is_derived_from_phase_graph(stages: dict) -> None:
    """exits_to must equal the canonical graph (no second hardcoded copy)."""
    derived = {
        (phase, target)
        for phase, body in stages.items()
        for target in body["exits_to"]
    }
    assert derived == phase_graph.lifecycle_edges()


@pytest.mark.parametrize("phase", _PHASES)
def test_phase_exit_invariants_pin(stages: dict, phase: str) -> None:
    assert stages[phase]["phase_exit_invariants"] == _PRESLIM_PHASE_EXIT_INVARIANTS[phase]


@pytest.mark.parametrize("phase", _PHASES)
def test_purpose_pin(stages: dict, phase: str) -> None:
    assert stages[phase]["purpose"] == _PRESLIM_PURPOSE[phase]


@pytest.mark.parametrize("phase", _PHASES)
def test_enters_from_pin(stages: dict, phase: str) -> None:
    assert stages[phase]["enters_from"] == _PRESLIM_ENTERS_FROM[phase]


def test_triage_routing_outcomes_and_terminate_flag_pin(stages: dict) -> None:
    assert stages["triage"]["routing_outcomes"] == _PRESLIM_TRIAGE_ROUTING_OUTCOMES
    assert stages["triage"]["can_terminate_without_full_lifecycle"] is True
    # routing_outcomes / can_terminate are triage-only; absent on other phases.
    for phase in ("brainstorm", "propose", "plan", "execute", "verify", "resolve"):
        assert "routing_outcomes" not in stages[phase]
        assert "can_terminate_without_full_lifecycle" not in stages[phase]


def test_stages_default_returns_fresh_objects() -> None:
    """Each call returns independent objects so a consumer cannot mutate the default."""
    a = stages_default()
    a["execute"]["allowed_tools"].append("MUTATED")
    a["triage"]["routing_outcomes"]["direct"] = "MUTATED"
    b = stages_default()
    assert "MUTATED" not in b["execute"]["allowed_tools"]
    assert b["triage"]["routing_outcomes"]["direct"] == "terminal_direct"


# ---------------------------------------------------------------------------
# Loader fallback + Guardian Layer-B fail-open proof.
# ---------------------------------------------------------------------------
def test_loader_injects_default_when_yaml_omits_stages() -> None:
    """Production config/phase-transitions.yaml omits stages -> loader injects default."""
    loaded = load_phase_transitions(REPO_ROOT)
    assert loaded.error is None
    assert loaded.value is not None
    # The slimmed production YAML carries no stages block of its own ...
    import yaml

    raw = yaml.safe_load((REPO_ROOT / "config" / "phase-transitions.yaml").read_text())
    assert not raw.get("stages"), "production YAML should no longer ship a stages block"
    # ... but the loader supplies the code default so consumers are unchanged.
    assert loaded.value.get("stages") == stages_default()


def _make_event(tool_name: str, phase: str) -> GuardianEvent:
    return GuardianEvent(
        runtime="test",
        adapter="unit",
        event_type="tool_call",
        tool_provider="core",
        tool_name=tool_name,
        tool_args={},
        uacp_run_id="uacp-stages-pin-001",
        uacp_phase=phase,
        workspace=str(REPO_ROOT),
        policy_version="0.1",
        declared_authority="plans/test.yaml",
        declared_side_effects=[],
        filesystem_guard_verified=True,
    )


def test_guardian_layer_b_not_failopen_with_code_default_stages() -> None:
    """With stages sourced from the loader (code default; YAML omits them),
    Guardian Layer-B still BLOCKS a protected tool that is not in the phase
    allowlist. This is the direct fail-open regression guard for the slim:
    were stages absent, Layer-B would no-op and admit the call.
    """
    policy = GuardianPolicy.load(str(REPO_ROOT))
    phase_config = load_phase_transitions(REPO_ROOT).value
    guardian = Guardian(policy, phase_config=phase_config)

    # uacp_config_write is a governed writer allowlisted in triage/execute but NOT
    # in plan -> an allowlist-miss in plan must be blocked by Layer-B.
    decision = guardian.evaluate(_make_event("uacp_config_write", "plan"))
    assert decision.decision == DECISION_BLOCK
    assert "phase_layer=allowlist_miss" in decision.evidence


def test_guardian_layer_b_blocks_unknown_phase_with_code_default_stages() -> None:
    """An unknown phase value is blocked when stages are populated (the loader
    default populates them), proving the slim did not collapse the
    unknown-phase guard to a no-op."""
    policy = GuardianPolicy.load(str(REPO_ROOT))
    phase_config = load_phase_transitions(REPO_ROOT).value
    guardian = Guardian(policy, phase_config=phase_config)

    decision = guardian.evaluate(_make_event("uacp_state_write", "execute_v2"))
    assert decision.decision == DECISION_BLOCK
    assert "phase_layer=unknown_phase" in decision.evidence

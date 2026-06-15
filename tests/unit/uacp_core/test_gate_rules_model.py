"""Production-equivalence pins for codified gate-rule grammar (Slice 4b T4c-1).

Three gate-rule blocks were moved out of config/phase-transitions.yaml and into
code (engines/domain/gate_rules.py) + operator knobs (config/uacp.toml
[heartgate.coherence] / [heartgate.run_registry]). These tests PIN the code
defaults (and the uacp.toml knobs) to the EXACT values that were in the
production YAML before the slim, guaranteeing behavior-preservation.

The pre-slim production values are captured here as literals (from the
config/phase-transitions.yaml state immediately before T4c-1):

  heartgate_coherence_required_when:
    min_composite_granularity: 7
    phases: [execute, verify]
    routing_outcomes: [full_governance]
    domains: [runtime, governance, guardian, heartgate, kanban, agent_council, uacp]
    required_field: heartgate_coherence
    required_lenses: [doctrine_coherence, cross_artifact_consistency,
      runtime_state_alignment, warning_and_deferred_item_honesty,
      authority_plane_integrity, next_phase_readiness]

  run_registry_rule:
    registry_path: state/run-registry.yaml
    enforcement: heartgate blocker on overlap with another active_run's write_paths
    required_for_transition: plan->execute
    writer_tool: uacp_run_registry_update
    exclusive_mutator_advisory: uacp-state skill

  adaptive_proposal_package_gate.required_universal_core:
    [intent, authority, scope, containment, risk, verification, transition, artifact_map]
  adaptive_proposal_package_gate.not_applicable_required_fields:
    [reason, accepted_by, owner, residual_risk, revisit_phase]
  adaptive_plan_package_gate.required_universal_core:
    [work_breakdown, dependencies, authority_and_side_effects, tool_runtime_selection,
     artifact_write_surfaces, verification_strategy, rollback_recovery,
     council_review_topology, transition_readiness]
  adaptive_plan_package_gate.not_applicable_required_fields:
    [reason, accepted_by, owner, residual_risk, revisit_phase, revisit_trigger]
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from engines.domain.gate_rules import (
    HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT,
    HEARTGATE_COHERENCE_REQUIRED_FIELD,
    HEARTGATE_COHERENCE_REQUIRED_LENSES,
    HEARTGATE_COHERENCE_SELECTORS_DEFAULT,
    PLAN_NOT_APPLICABLE_REQUIRED_FIELDS,
    PLAN_REQUIRED_UNIVERSAL_CORE,
    PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS,
    PROPOSAL_REQUIRED_UNIVERSAL_CORE,
    heartgate_coherence_required_when_default,
    run_registry_rule_default,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_UACP_TOML = _REPO_ROOT / "config" / "uacp.toml"


# Pre-slim production literals -------------------------------------------------

_PROD_COHERENCE = {
    "min_composite_granularity": 7,
    "phases": ["execute", "verify"],
    "routing_outcomes": ["full_governance"],
    "domains": [
        "runtime",
        "governance",
        "guardian",
        "heartgate",
        "kanban",
        "agent_council",
        "uacp",
    ],
    "required_field": "heartgate_coherence",
    "required_lenses": [
        "doctrine_coherence",
        "cross_artifact_consistency",
        "runtime_state_alignment",
        "warning_and_deferred_item_honesty",
        "authority_plane_integrity",
        "next_phase_readiness",
    ],
}

_PROD_RUN_REGISTRY = {
    "registry_path": "state/run-registry.yaml",
    "enforcement": "heartgate blocker on overlap with another active_run's write_paths",
    "required_for_transition": "plan->execute",
    "writer_tool": "uacp_run_registry_update",
    "exclusive_mutator_advisory": "uacp-state skill",
}

_PROD_PROPOSAL_CORE = [
    "intent", "authority", "scope", "containment",
    "risk", "verification", "transition", "artifact_map",
]
_PROD_PROPOSAL_NA = ["reason", "accepted_by", "owner", "residual_risk", "revisit_phase"]
_PROD_PLAN_CORE = [
    "work_breakdown", "dependencies", "authority_and_side_effects", "tool_runtime_selection",
    "artifact_write_surfaces", "verification_strategy", "rollback_recovery",
    "council_review_topology", "transition_readiness",
]
_PROD_PLAN_NA = ["reason", "accepted_by", "owner", "residual_risk", "revisit_phase", "revisit_trigger"]


# A. heartgate_coherence_required_when ----------------------------------------

def test_coherence_code_default_equals_pre_slim_production():
    rule = heartgate_coherence_required_when_default()
    assert rule["min_composite_granularity"] == _PROD_COHERENCE["min_composite_granularity"]
    assert rule["phases"] == _PROD_COHERENCE["phases"]
    assert rule["routing_outcomes"] == _PROD_COHERENCE["routing_outcomes"]
    assert rule["domains"] == _PROD_COHERENCE["domains"]
    assert rule["required_field"] == _PROD_COHERENCE["required_field"]
    assert rule["required_lenses"] == _PROD_COHERENCE["required_lenses"]


def test_coherence_grammar_constants():
    assert HEARTGATE_COHERENCE_REQUIRED_FIELD == "heartgate_coherence"
    assert HEARTGATE_COHERENCE_REQUIRED_LENSES == _PROD_COHERENCE["required_lenses"]
    assert HEARTGATE_COHERENCE_MIN_GRANULARITY_DEFAULT == 7
    assert HEARTGATE_COHERENCE_SELECTORS_DEFAULT["phases"] == _PROD_COHERENCE["phases"]
    assert HEARTGATE_COHERENCE_SELECTORS_DEFAULT["routing_outcomes"] == _PROD_COHERENCE["routing_outcomes"]
    assert HEARTGATE_COHERENCE_SELECTORS_DEFAULT["domains"] == _PROD_COHERENCE["domains"]


def test_coherence_knob_overrides_win():
    """Operator knob values (uacp.toml) override the code-default selectors."""
    rule = heartgate_coherence_required_when_default(
        min_composite_granularity=3,
        selectors={"phases": ["plan"], "routing_outcomes": ["standard_uacp"], "domains": ["x"]},
    )
    assert rule["min_composite_granularity"] == 3
    assert rule["phases"] == ["plan"]
    assert rule["routing_outcomes"] == ["standard_uacp"]
    assert rule["domains"] == ["x"]
    # Grammar (non-tunable) is unaffected by the override.
    assert rule["required_field"] == "heartgate_coherence"
    assert rule["required_lenses"] == _PROD_COHERENCE["required_lenses"]


def test_uacp_toml_coherence_knob_equals_production():
    """config/uacp.toml [heartgate.coherence] pins the pre-slim selectors."""
    with _UACP_TOML.open("rb") as fh:
        toml = tomllib.load(fh)
    knob = toml["heartgate"]["coherence"]
    assert knob["min_composite_granularity"] == _PROD_COHERENCE["min_composite_granularity"]
    assert knob["phases"] == _PROD_COHERENCE["phases"]
    assert knob["routing_outcomes"] == _PROD_COHERENCE["routing_outcomes"]
    assert knob["domains"] == _PROD_COHERENCE["domains"]


# B. run_registry_rule --------------------------------------------------------

def test_run_registry_code_default_equals_pre_slim_production():
    rule = run_registry_rule_default()
    for key, value in _PROD_RUN_REGISTRY.items():
        assert rule[key] == value, key


def test_run_registry_knob_enforcement_overrides_win():
    rule = run_registry_rule_default(enforcement="observe-only (warn)")
    assert rule["enforcement"] == "observe-only (warn)"
    # Grammar is unaffected.
    assert rule["registry_path"] == _PROD_RUN_REGISTRY["registry_path"]
    assert rule["required_for_transition"] == _PROD_RUN_REGISTRY["required_for_transition"]
    assert rule["writer_tool"] == _PROD_RUN_REGISTRY["writer_tool"]


def test_uacp_toml_run_registry_knob_equals_production():
    with _UACP_TOML.open("rb") as fh:
        toml = tomllib.load(fh)
    knob = toml["heartgate"]["run_registry"]
    assert knob["enforcement"] == _PROD_RUN_REGISTRY["enforcement"]


# C. Pattern-A adaptive gate sub-fields ---------------------------------------

def test_proposal_required_universal_core_equals_production():
    assert PROPOSAL_REQUIRED_UNIVERSAL_CORE == _PROD_PROPOSAL_CORE


def test_proposal_not_applicable_required_fields_equals_production():
    assert PROPOSAL_NOT_APPLICABLE_REQUIRED_FIELDS == _PROD_PROPOSAL_NA


def test_plan_required_universal_core_equals_production():
    assert PLAN_REQUIRED_UNIVERSAL_CORE == _PROD_PLAN_CORE


def test_plan_not_applicable_required_fields_equals_production():
    assert PLAN_NOT_APPLICABLE_REQUIRED_FIELDS == _PROD_PLAN_NA


# Enforce-by-default behavior (fail-closed when block absent) -----------------

def test_coherence_requirement_fires_when_block_absent(temp_uacp_root, valid_run_id):
    """With NO heartgate_coherence_required_when in config (the production
    slimmed state), the code default applies and an execute->verify transition
    lacking a heartgate_coherence field is BLOCKED. The conftest fixture's
    explicit empty-mapping opt-out is what keeps the lifecycle tests lax; here we
    delete that stub to exercise the production enforce-by-default path."""
    from core import Heartgate

    hg = Heartgate.load(str(temp_uacp_root))
    # Drop the fixture's opt-out stub so an ABSENT block exercises the code default.
    hg.config.pop("heartgate_coherence_required_when", None)

    blockers: list[str] = []
    hg._validate_heartgate_coherence_requirement(
        {
            "from_phase": "execute",
            "to_phase": "verify",
            "run_id": valid_run_id,
        },
        blockers,
    )
    assert any("heartgate_coherence required by transition policy" in b for b in blockers), blockers


def test_run_registry_rule_active_when_block_absent(temp_uacp_root, valid_run_id):
    """With NO run_registry_rule in config, the code default applies: the rule is
    active on plan->execute (here it warns because no registry file exists)."""
    from core import Heartgate

    hg = Heartgate.load(str(temp_uacp_root))
    assert hg.config.get("run_registry_rule") is None
    rule = hg._run_registry_rule()
    assert rule["required_for_transition"] == "plan->execute"
    assert rule["registry_path"] == "state/run-registry.yaml"

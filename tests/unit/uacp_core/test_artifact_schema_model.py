"""Unit tests for codified artifact schemas in engines/domain/artifact_schema.py (Slice 4a).

Asserts:
- BlastRadius Literal covers exactly {low, medium, high, critical}
- The 4 transition schemas (intent/scope/lessons/evidence_disposition) expose
  required_for_transition, path_template, required_fields / required_sections
  EXACTLY matching config/artifact-schemas.yaml
- artifact_schemas_dict() returns a dict whose access patterns match what the
  5 Heartgate readers expect (same keys, same value shapes)
"""

from __future__ import annotations

from typing import get_args


from engines.domain.artifact_schema import (
    BlastRadius,
    IntentSchema,
    ScopeSchema,
    LessonsSchema,
    EvidenceDispositionSchema,
    artifact_schemas_dict,
)


# ---------------------------------------------------------------------------
# BlastRadius
# ---------------------------------------------------------------------------

def test_blast_radius_values():
    """BlastRadius must be exactly {low, medium, high, critical} (from YAML)."""
    values = set(get_args(BlastRadius))
    assert values == {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# IntentSchema (triage->propose)
# ---------------------------------------------------------------------------

def test_intent_schema_required_for_transition():
    schema = IntentSchema()
    assert schema.required_for_transition == "triage->propose"


def test_intent_schema_path_template():
    schema = IntentSchema()
    assert schema.path_template == "proposals/{run_id}-intent.md"


def test_intent_schema_required_sections():
    schema = IntentSchema()
    assert schema.required_sections == [
        "Success Definition",
        "Explicit Out-of-Scope",
        "Termination Condition",
        "Authority Source",
    ]


# ---------------------------------------------------------------------------
# ScopeSchema (plan->execute)
# ---------------------------------------------------------------------------

def test_scope_schema_required_for_transition():
    schema = ScopeSchema()
    assert schema.required_for_transition == "plan->execute"


def test_scope_schema_path_template():
    schema = ScopeSchema()
    assert schema.path_template == "plans/{run_id}-scope.yaml"


def test_scope_schema_required_fields():
    schema = ScopeSchema()
    assert schema.required_fields == ["run_id", "write_paths", "blast_radius", "rollback_path"]


# ---------------------------------------------------------------------------
# LessonsSchema (verify->resolve)
# ---------------------------------------------------------------------------

def test_lessons_schema_required_for_transition():
    schema = LessonsSchema()
    assert schema.required_for_transition == "verify->resolve"


def test_lessons_schema_path_template():
    schema = LessonsSchema()
    assert schema.path_template == "resolutions/{run_id}-lessons.yaml"


def test_lessons_schema_required_fields():
    schema = LessonsSchema()
    assert schema.required_fields == ["run_id", "lessons"]


# ---------------------------------------------------------------------------
# EvidenceDispositionSchema (verify->resolved)
# ---------------------------------------------------------------------------

def test_evidence_disposition_schema_required_for_transition():
    schema = EvidenceDispositionSchema()
    assert schema.required_for_transition == "verify->resolved"


def test_evidence_disposition_schema_paired_paths():
    schema = EvidenceDispositionSchema()
    assert schema.paired_paths["verified_facts"] == "verification/{run_id}-{cluster}-verified-facts.md"
    assert schema.paired_paths["assumptions"] == "verification/{run_id}-{cluster}-assumptions.md"


# ---------------------------------------------------------------------------
# artifact_schemas_dict() — shape matches what the 5 Heartgate readers expect
# ---------------------------------------------------------------------------

def test_dict_has_top_level_schema_keys():
    d = artifact_schemas_dict()
    for key in ("scope", "intent", "lessons", "evidence_disposition"):
        assert key in d, f"missing key: {key}"


def test_dict_scope_required_fields():
    d = artifact_schemas_dict()
    assert d["scope"]["required_fields"] == ["run_id", "write_paths", "blast_radius", "rollback_path"]


def test_dict_scope_required_for_transition():
    d = artifact_schemas_dict()
    assert d["scope"]["required_for_transition"] == "plan->execute"


def test_dict_scope_path_template():
    d = artifact_schemas_dict()
    assert d["scope"]["path_template"] == "plans/{run_id}-scope.yaml"


def test_dict_intent_required_sections():
    d = artifact_schemas_dict()
    assert d["intent"]["required_sections"] == [
        "Success Definition",
        "Explicit Out-of-Scope",
        "Termination Condition",
        "Authority Source",
    ]


def test_dict_intent_required_for_transition():
    d = artifact_schemas_dict()
    assert d["intent"]["required_for_transition"] == "triage->propose"


def test_dict_intent_path_template():
    d = artifact_schemas_dict()
    assert d["intent"]["path_template"] == "proposals/{run_id}-intent.md"


def test_dict_lessons_path_template():
    d = artifact_schemas_dict()
    assert d["lessons"]["path_template"] == "resolutions/{run_id}-lessons.yaml"


def test_dict_lessons_required_fields():
    d = artifact_schemas_dict()
    assert d["lessons"]["required_fields"] == ["run_id", "lessons"]


def test_dict_evidence_disposition_required_for_transition():
    d = artifact_schemas_dict()
    assert d["evidence_disposition"]["required_for_transition"] == "verify->resolved"


def test_dict_evidence_disposition_paired_paths():
    d = artifact_schemas_dict()
    paired = d["evidence_disposition"]["paired_paths"]
    assert paired["verified_facts"] == "verification/{run_id}-{cluster}-verified-facts.md"
    assert paired["assumptions"] == "verification/{run_id}-{cluster}-assumptions.md"


def test_dict_cross_checks_evidence_minimum_content():
    """evidence_disposition_minimum_content must be in cross_checks (Heartgate line ~1906)."""
    d = artifact_schemas_dict()
    cross = d["cross_checks"]
    minc = cross["evidence_disposition_minimum_content"]
    assert minc["verified_facts_required_header_substring"] == "Fact"
    assert minc["assumptions_required_header_substring"] == "Disposition"


def test_dict_run_registry_present():
    """run_registry key must be present (Heartgate consumers expect it)."""
    d = artifact_schemas_dict()
    assert "run_registry" in d
    assert d["run_registry"]["required_fields"] == ["active_runs"]


def test_dict_no_knobs_in_cross_checks():
    """tool_path_capabilities and handler_refusals must NOT appear in the dict
    (they moved to uacp.toml in Step 4)."""
    d = artifact_schemas_dict()
    cross = d.get("cross_checks", {})
    scope_block = cross.get("scope_write_paths_vs_layer_b", {})
    # These operator-tunable knobs are now in uacp.toml, not in the dict
    assert "tool_path_capabilities" not in scope_block
    assert "handler_refusals" not in scope_block

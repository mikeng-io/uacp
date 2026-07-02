"""Codified artifact schemas for UACP phase-transition validation (Slice 4a).

Previously sourced from ``config/artifact-schemas.yaml`` by YAML parse in
``core.py:_load_artifact_schemas``. Now the four transition schemas
(scope/intent/lessons/evidence_disposition), blast_radius enum, cross-check
constants, and run_registry schema are declared as Pydantic models here.

The two operator-tunable path tables (``tool_path_capabilities`` and
``handler_refusals``) have moved to ``config/uacp.toml [scope]`` — the
Heartgate readers that previously pulled those from this dict now read them via
``config.get_config(root)``.

Public API:
    BlastRadius      — Literal type for the four allowed blast_radius values
    IntentSchema     — triage->propose intent doc schema
    ScopeSchema      — plan->execute scope artifact schema
    LessonsSchema    — verify->resolve lessons artifact schema
    EvidenceDispositionSchema — verify->resolve evidence pair schema
    artifact_schemas_dict()  — dict that reproduces the shape Heartgate readers
                               previously obtained from yaml.safe_load on the YAML

The dict returned by ``artifact_schemas_dict()`` is kept **structurally
identical** to the old YAML load result (same top-level keys, same nested
access patterns) so that the 5 Heartgate schema-reader call sites need zero
changes.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# BlastRadius — canonical enum (previously scope.fields.blast_radius.values)
# ---------------------------------------------------------------------------

BlastRadius = Literal["low", "medium", "high", "critical"]

# The frozenset is also exposed so scope_conformance._load_blast_radius_enum
# can derive it via get_args(BlastRadius) without an import cycle.
BLAST_RADIUS_VALUES: frozenset[str] = frozenset({"low", "medium", "high", "critical"})


# ---------------------------------------------------------------------------
# Transition schema models
# ---------------------------------------------------------------------------


class IntentSchema(BaseModel):
    """Phase 2.3: triage->propose intent doc (proposals/{run_id}-intent.md)."""

    model_config = ConfigDict(frozen=True)

    required_for_transition: str = "triage->propose"
    path_template: str = "proposals/{run_id}-intent.md"
    required_sections: list[str] = [
        "Success Definition",
        "Explicit Out-of-Scope",
        "Termination Condition",
        "Authority Source",
    ]


class ScopeSchema(BaseModel):
    """Phase 2.1: plan->execute scope artifact (plans/{run_id}-scope.yaml)."""

    model_config = ConfigDict(frozen=True)

    required_for_transition: str = "plan->execute"
    path_template: str = "plans/{run_id}-scope.yaml"
    required_fields: list[str] = ["run_id", "write_paths", "blast_radius", "rollback_path"]
    optional_fields: list[str] = [
        "read_paths",
        "forbidden_paths",
        "api_surfaces",
        "runtime_surfaces",
        "migrations",
        "side_effects",
        # Optional scope-witness claim (#85): the {file, name} touch-set the
        # cascade-witness gate derives an independent account against.
        "code_refs",
    ]


class LessonsSchema(BaseModel):
    """Phase 2.4: verify->resolve lessons artifact (resolutions/{run_id}-lessons.yaml)."""

    model_config = ConfigDict(frozen=True)

    required_for_transition: str = "verify->resolve"
    path_template: str = "resolutions/{run_id}-lessons.yaml"
    required_fields: list[str] = ["run_id", "lessons"]


class EvidenceDispositionSchema(BaseModel):
    """Phase 2.2: verify->resolve evidence disposition pair files."""

    model_config = ConfigDict(frozen=True)

    required_for_transition: str = "verify->resolve"
    paired_paths: dict[str, str] = {
        "verified_facts": "verification/{run_id}-{cluster}-verified-facts.md",
        "assumptions": "verification/{run_id}-{cluster}-assumptions.md",
    }
    assumptions_dispositions: dict[str, Any] = {
        "accepted_risk": {
            "description": "Acknowledged risk; owner accepts impact.",
            "requires": ["owner"],
        },
        "deferred": {
            "description": "Deferred to a later phase or run.",
            "requires": ["owner", "next_phase_obligation"],
        },
        "pending": {
            "description": "Must be resolved before RESOLVE — blocks if unowned.",
            "requires": ["owner", "next_phase_obligation"],
        },
    }


# ---------------------------------------------------------------------------
# Cross-check constants (evidence_disposition_minimum_content only;
# tool_path_capabilities and handler_refusals have moved to uacp.toml)
# ---------------------------------------------------------------------------

_EVIDENCE_DISPOSITION_MINIMUM_CONTENT: dict[str, str] = {
    "verified_facts_required_header_substring": "Fact",
    "assumptions_required_header_substring": "Disposition",
}

# ---------------------------------------------------------------------------
# Run registry schema constants
# ---------------------------------------------------------------------------

_RUN_REGISTRY: dict[str, Any] = {
    "kind": "uacp.run_registry",
    "path": "state/run-registry.yaml",
    "required_fields": ["active_runs"],
    "fields": {
        "schema_version": "string",
        "active_runs": {
            "type": "list",
            "item_schema": {
                "run_id": "string",
                "phase": "string",
                "write_paths": {"type": "list", "item_type": "string"},
                "scope_artifact_path": "string",
                "started_at": "integer",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Builder — reproduces the dict shape _load_artifact_schemas() used to return
# ---------------------------------------------------------------------------


def artifact_schemas_dict() -> dict[str, Any]:
    """Return a dict structurally equivalent to the old yaml.safe_load output.

    The shape is kept IDENTICAL to what ``core.py:_load_artifact_schemas``
    previously returned so that all five Heartgate reader call sites remain
    unchanged:

        self.artifact_schemas.get("intent")          → _validate_intent_doc
        self.artifact_schemas.get("scope")           → _validate_scope_artifact
        self.artifact_schemas.get("lessons")         → _validate_lessons_artifact
        self.artifact_schemas.get("evidence_disposition") → _validate_evidence_dispositions
        self.artifact_schemas.get("cross_checks")["evidence_disposition_minimum_content"]
                                                     → _validate_evidence_dispositions (line ~1906)

    The two operator-tunable knobs that previously lived under
    ``cross_checks.scope_write_paths_vs_layer_b`` (tool_path_capabilities and
    handler_refusals) are NOT included here — they have been moved to
    ``config/uacp.toml [scope]`` and their Heartgate readers have been
    updated accordingly.
    """
    intent = IntentSchema()
    scope = ScopeSchema()
    lessons = LessonsSchema()
    evdisp = EvidenceDispositionSchema()

    return {
        "scope": {
            "kind": "uacp.scope",
            "required_for_transition": scope.required_for_transition,
            "path_template": scope.path_template,
            "required_fields": list(scope.required_fields),
            "optional_fields": list(scope.optional_fields),
            "fields": {
                "run_id": "string",
                "write_paths": {
                    "type": "list",
                    "item_type": "string",
                    "description": "UACP_ROOT-relative glob patterns that EXECUTE may write.",
                },
                "read_paths": {"type": "list", "item_type": "string"},
                "forbidden_paths": {"type": "list", "item_type": "string"},
                "blast_radius": {
                    "type": "enum",
                    "values": list(BLAST_RADIUS_VALUES),
                },
                "rollback_path": {
                    "type": "string",
                    "description": "How to undo, or 'none--write-only-artifact' if not reversible.",
                },
            },
        },
        "evidence_disposition": {
            "kind": "uacp.evidence_disposition",
            "required_for_transition": evdisp.required_for_transition,
            "paired_paths": dict(evdisp.paired_paths),
            "assumptions_dispositions": dict(evdisp.assumptions_dispositions),
        },
        "intent": {
            "kind": "uacp.intent",
            "required_for_transition": intent.required_for_transition,
            "path_template": intent.path_template,
            "required_sections": list(intent.required_sections),
        },
        "lessons": {
            "kind": "uacp.lessons",
            "required_for_transition": lessons.required_for_transition,
            "path_template": lessons.path_template,
            "required_fields": list(lessons.required_fields),
        },
        "cross_checks": {
            "evidence_disposition_minimum_content": dict(_EVIDENCE_DISPOSITION_MINIMUM_CONTENT),
        },
        "run_registry": dict(_RUN_REGISTRY),
    }

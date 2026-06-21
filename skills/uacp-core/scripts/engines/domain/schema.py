"""uacp-schema (Slice 1b / graph-engine D9-D10) — the per-kind node-schema registry.

The foundational, near-pure-leaf validation sink: a `kind -> JSON-Schema (draft 2020-12)`
registry + a thin `validate(kind, doc)`. It imports only `jsonschema` + stdlib; everything
that needs validation (uacp-lint, the entity-writer, Guardian) imports IT, not the reverse.

Doctrine (D9): **closed-world** (`additionalProperties: false` — a typo'd key is an error,
not a silently dropped edge), required fields per kind, **enums for closed vocabularies**,
and the kind-specific structural rules that make the graph trustless at the source:

* a `work_unit` MUST carry a non-empty `derives_from` (forbids phantom tasks);
* an `evidence_obligation` MUST carry a `work_unit_id` (no free-floating obligations);
* an `assessment` MUST cite `evidence_refs` (>=1) (no self-attesting closures).

Scope: the five governance node kinds (scope_item, work_unit, evidence_obligation,
checkpoint, assessment), matching the real on-disk shapes (verified vs the oauth-login
fixture + graph_projection readers). The knowledge-plane `lesson` + index schemas land
next. `validate` NEVER raises — malformed input returns error strings, not exceptions.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

_DRAFT = "https://json-schema.org/draft/2020-12/schema"

# Enums — closed vocabularies (D9). NOTE: the node-item `_RESULT` below is spike-shaped
# (the real per-evidence/assessment vocabulary is {pass,warn,block,deferred}); it is
# re-grounded in a later increment with the node-items. `_BLAST_RADIUS` is the real
# scope vocabulary (artifact_schema.BlastRadius).
_RESULT = ("pass", "fail")
_BLAST_RADIUS = ("low", "medium", "high", "critical")

# kind -> JSON-Schema. Shapes verified against the oauth-login fixture + graph_projection.
_SCHEMAS: dict[str, dict[str, Any]] = {
    "scope_item": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "description": "Stable scope-item identity (si-*)."},
            "statement": {"type": "string", "description": "The in-scope intent, prose."},
        },
    },
    "work_unit": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "title", "derives_from"],
        "properties": {
            "id": {"type": "string", "description": "Stable work-unit identity (wu-*)."},
            "title": {"type": "string", "description": "What this unit of work does."},
            "derives_from": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "scope_item ids this work_unit derives from; >=1 — the "
                "anti-phantom rule (a work_unit with no derives_from is an orphan).",
            },
        },
    },
    "evidence_obligation": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "work_unit_id"],
        "properties": {
            "id": {"type": "string", "description": "Stable obligation identity (ev-*)."},
            "work_unit_id": {
                "type": "string",
                "description": "The work_unit this obligation is for (the obligation_for edge); "
                "required — no free-floating obligations.",
            },
            "statement": {"type": "string", "description": "What evidence is required."},
            "description": {"type": "string"},
        },
    },
    "checkpoint": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "work_unit_id", "result"],
        "properties": {
            "id": {"type": "string", "description": "Stable checkpoint identity (cp-*)."},
            "work_unit_id": {
                "type": "string",
                "description": "The work_unit this checkpoint records (the checkpoint_of edge).",
            },
            "result": {"enum": list(_RESULT), "description": "Checkpoint outcome (pass|fail)."},
        },
    },
    "assessment": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["obligation_id", "evidence_refs", "result"],
        "properties": {
            "id": {
                "type": "string",
                "description": "Assessment identity (as-*); optional, synthesized if absent.",
            },
            "obligation_id": {
                "type": "string",
                "description": "The evidence_obligation this assessment verifies.",
            },
            "work_unit_id": {"type": "string", "description": "The work_unit assessed (optional)."},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "checkpoint ids cited as evidence; >=1 — an assessment with no "
                "evidence is a self-attesting closure (forbidden).",
            },
            "result": {"enum": list(_RESULT), "description": "Assessment outcome (pass|fail)."},
        },
    },
    # --- Document kinds: fixture-backed YAML artifacts (artifact_schema.py fold-in, D41) ---
    # Authored from the golden fixtures (tests/e2e/fixtures/) + the artifact_schema.py field
    # vocab. SHAPE only (closed-world, enums, kind const); the referential checks these kinds
    # carry today stay in the validator that becomes uacp-lint.
    "uacp.scope": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "run_id", "write_paths", "blast_radius", "rollback_path"],
        "properties": {
            "kind": {"const": "uacp.scope", "description": "Document kind; must be 'uacp.scope'."},
            "run_id": {"type": "string", "minLength": 1, "description": "Owning run id."},
            "write_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "UACP_ROOT-relative globs EXECUTE may write (the mutation surface).",
            },
            "blast_radius": {
                "enum": list(_BLAST_RADIUS),
                "description": "Declared impact tier (low|medium|high|critical).",
            },
            "rollback_path": {
                "type": "string",
                "description": "How to undo, or 'none--write-only-artifact' if irreversible.",
            },
            "read_paths": {"type": "array", "items": {"type": "string"}},
            "forbidden_paths": {"type": "array", "items": {"type": "string"}},
            "api_surfaces": {"description": "Optional; type unconstrained until grounded."},
            "runtime_surfaces": {"description": "Optional; type unconstrained until grounded."},
            "migrations": {"description": "Optional; type unconstrained until grounded."},
            "side_effects": {"description": "Optional; type unconstrained until grounded."},
        },
    },
    "uacp.run_registry": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "active_runs"],
        "properties": {
            "kind": {"const": "uacp.run_registry", "description": "Must be 'uacp.run_registry'."},
            "schema_version": {
                "type": "string",
                "description": "Optional registry schema version.",
            },
            "active_runs": {
                "type": "array",
                "description": "In-flight run entries (write-path overlap + goal chaining).",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["run_id"],
                    "properties": {
                        "run_id": {"type": "string", "description": "The active run."},
                        "phase": {"type": "string", "description": "Current lifecycle phase."},
                        "write_paths": {"type": "array", "items": {"type": "string"}},
                        "scope_artifact_path": {"type": "string"},
                        "started_at": {"type": "integer"},
                        "goal_id": {"type": "string", "description": "Goal-driven track only."},
                    },
                },
            },
        },
    },
    "uacp.lessons": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "run_id", "lessons"],
        "properties": {
            "kind": {"const": "uacp.lessons", "description": "Must be 'uacp.lessons'."},
            "run_id": {"type": "string", "minLength": 1, "description": "Owning run id."},
            "lessons": {
                "type": "array",
                "items": {"type": "object"},
                "description": "RESOLVE lessons. Items loosely typed (the knowledge-plane `lesson` "
                "node-item — a separate concern — is not this transition artifact).",
            },
        },
    },
}


def validate(kind: str, doc: Any) -> list[str]:
    """Validate ``doc`` against the schema for ``kind``. Return a list of error strings
    (empty == valid). Never raises — an unknown kind is itself a reported error."""
    schema = _SCHEMAS.get(kind)
    if schema is None:
        return [f"unknown kind '{kind}' — no schema registered in uacp-schema"]
    validator = Draft202012Validator(schema)
    out: list[str] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        out.append(f"{path}: {err.message}")
    return out

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

# Enums — closed vocabularies (D9). Seeded with the verified `result` set (the only
# values used across fixtures/tests/engines); more land with the kinds that use them.
_RESULT = ("pass", "fail")

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

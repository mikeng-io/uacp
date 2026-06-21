"""uacp-schema (Slice 1b / graph-engine D9-D10/D40) — the control-plane schema registry.

The foundational, near-pure-leaf validation sink: a `kind -> JSON-Schema (draft 2020-12)`
registry + a thin `validate(kind, doc)`. It imports only `jsonschema` + stdlib; everything
that needs validation (uacp-lint, the entity-writer, Guardian) imports IT, not the reverse.

Doctrine (D9): **closed-world** (`additionalProperties: false` — a typo'd key is an error,
not a silently dropped edge), required fields per kind, **enums for closed vocabularies**,
and the kind-specific structural rules that make the graph trustless at the source:

* a `work_unit` MUST carry a non-empty `derives_from` (forbids phantom tasks);
* an `evidence_obligation` MUST carry a `work_unit_id` (no free-floating obligations);
* an `assessment` MUST cite `evidence_refs` (>=1) (no self-attesting closures).

Two registry layers:

* **node-item kinds** — the entities that live *inside* manifest documents (scope_item,
  work_unit, evidence_obligation, checkpoint, assessment). Defined once in `_NODE_DEFS`.
* **document kinds** — whole control-plane artifacts (`uacp.proposal` / `plan` /
  `execution` / `piv_assessment` / `lessons`) that **compose** the node-item kinds via
  JSON-Schema `$ref`/`$defs`: a plan's `work_units[]` items `$ref` the one `work_unit`
  definition — reused, never re-inlined, so a rule edited once changes both layers. Each
  document pins its `kind` (const) and is closed-world, so a misspelled top-level key —
  e.g. a typo'd `work_units` that would silently drop every task — is a load-time error.

Shapes are verified against the real canonical-form fixtures in
`design/graph-engine/spike/fixtures/oauth-login/` (+ the golden `tests/e2e/fixtures/
lessons.yaml`) by the test suite, so the registry cannot drift from the on-disk form. The
verification document's on-disk `kind` is `uacp.piv_assessment` and the resolve document's
is `uacp.lessons` (matching the kernel + fixtures; the design catalog's `uacp.verification`
/ `uacp.resolution` names reconcile to these). `validate` NEVER raises — malformed input
returns error strings, not exceptions. The knowledge-plane `lesson` node-item (which will
tighten `uacp.lessons`' items) + the index schemas land in later increments.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

_DRAFT = "https://json-schema.org/draft/2020-12/schema"

# Enums — closed vocabularies (D9). Seeded with the verified `result` set (the only
# values used across fixtures/tests/engines); more land with the kinds that use them.
_RESULT = ("pass", "fail")

# --- Node-item kinds: the entities that live INSIDE manifest documents ---------------
# Bodies only (no `$schema` key): each is reused both standalone (wrapped with the draft
# declaration in `_NODE_SCHEMAS`) and embedded as a `$defs` entry the document kinds
# `$ref`. ONE definition per kind = one source of truth. Shapes verified against the
# oauth-login fixture + the graph_projection readers.
_NODE_DEFS: dict[str, dict[str, Any]] = {
    "scope_item": {
        "type": "object",
        "additionalProperties": False,
        "required": ["id"],
        "properties": {
            "id": {"type": "string", "description": "Stable scope-item identity (si-*)."},
            "statement": {"type": "string", "description": "The in-scope intent, prose."},
        },
    },
    "work_unit": {
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

# Standalone node-item schemas: the def body + the root draft declaration, so
# `validate("work_unit", item)` works directly on a bare node.
_NODE_SCHEMAS: dict[str, dict[str, Any]] = {
    name: {"$schema": _DRAFT, **body} for name, body in _NODE_DEFS.items()
}


def _document(kind_const: str, payload: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """A closed-world document schema that carries the node-item `$defs` so its `payload`
    properties can `$ref` them (reuse, not re-inline). `kind` is pinned to `kind_const`
    and `run_id` is always required; `required` + `payload` add the kind-specific fields.
    Scalar envelope fields (status / authority / ids / ...) stay permissive here — their
    own schemas land in later increments — but the document is `additionalProperties:
    false`, so an unknown / misspelled top-level key is rejected."""
    return {
        "$schema": _DRAFT,
        "$defs": _NODE_DEFS,
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "run_id", *required],
        "properties": {
            "kind": {"const": kind_const, "description": f"Document kind; must be '{kind_const}'."},
            "run_id": {"type": "string", "minLength": 1, "description": "Owning run id."},
            **payload,
        },
    }


_AUTHORITY = {"type": "object", "description": "Authority block (own schema: later increment)."}
_STATUS = {"type": "string", "description": "Lifecycle status."}

# --- Document kinds: whole artifacts that COMPOSE the node-item kinds -----------------
_DOC_SCHEMAS: dict[str, dict[str, Any]] = {
    "uacp.proposal": _document(
        "uacp.proposal",
        {
            "proposal_id": {"type": "string", "description": "Proposal identity."},
            "status": _STATUS,
            "authority": _AUTHORITY,
            "purpose": {"type": "string", "description": "One-line statement of intent."},
            "scope": {
                "type": "object",
                "additionalProperties": False,
                "required": ["in_scope"],
                "properties": {
                    "in_scope": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"$ref": "#/$defs/scope_item"},
                        "description": "Keyed scope_items (>=1) — the declared intent the "
                        "plan must cover.",
                    },
                    "out_of_scope": {
                        "type": "array",
                        "description": "Deprecated weak form (D7: a `prohibition` node-kind "
                        "supersedes it later); left loosely typed for now.",
                    },
                },
                "description": "Scope envelope holding the keyed in_scope intents.",
            },
        },
        required=["scope"],
    ),
    "uacp.plan": _document(
        "uacp.plan",
        {
            "plan_id": {"type": "string", "description": "Plan identity."},
            "status": _STATUS,
            "authority": _AUTHORITY,
            "work_units": {
                "type": "array",
                "items": {"$ref": "#/$defs/work_unit"},
                "description": "The plan's work_units; each carries derives_from -> scope_item.",
            },
            "evidence_obligations": {
                "type": "array",
                "items": {"$ref": "#/$defs/evidence_obligation"},
                "description": "PIV obligations (one per work_unit; coverage is a closure "
                "check, not a shape rule, so this key is optional here).",
            },
        },
        required=["work_units"],
    ),
    "uacp.execution": _document(
        "uacp.execution",
        {
            "checkpoints": {
                "type": "array",
                "items": {"$ref": "#/$defs/checkpoint"},
                "description": "EXECUTE checkpoints, linked to work_units by work_unit_id.",
            },
        },
        required=["checkpoints"],
    ),
    "uacp.piv_assessment": _document(
        "uacp.piv_assessment",
        {
            "assessments": {
                "type": "array",
                "items": {"$ref": "#/$defs/assessment"},
                "description": "VERIFY assessments (one per obligation; each cites evidence_refs).",
            },
        },
        required=["assessments"],
    ),
    "uacp.lessons": _document(
        "uacp.lessons",
        {
            "lessons": {
                "type": "array",
                "items": {"type": "object"},
                "description": "RESOLVE lessons. Items stay loosely typed until the `lesson` "
                "node-item lands (later increment, knowledge/OKF plane).",
            },
        },
        required=["lessons"],
    ),
}

# The unified registry: node-item kinds + document kinds. Document kinds are dotted
# (`uacp.*`); node-item kinds are bare — they never appear as a file's top-level `kind`.
_SCHEMAS: dict[str, dict[str, Any]] = {**_NODE_SCHEMAS, **_DOC_SCHEMAS}


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

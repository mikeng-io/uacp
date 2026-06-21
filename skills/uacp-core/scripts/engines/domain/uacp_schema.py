"""uacp-schema (Slice 1b / graph-engine D9-D10) — the per-kind node-schema registry.

The foundational, near-pure-leaf validation sink: a `kind -> JSON-Schema (draft 2020-12)`
registry + a thin `validate(kind, doc)`. It imports only `jsonschema` + stdlib; everything
that needs validation (uacp-lint, the entity-writer, Guardian) imports IT, not the reverse.

Doctrine (D9): **closed-world** (`additionalProperties: false` — a typo'd key is an error,
not a silently dropped edge), required fields per kind, and the kind-specific structural
rule that a `work_unit` MUST carry a non-empty `derives_from` (what structurally forbids
phantom tasks at the source).

Scope today: the two Phase-A node kinds (`scope_item`, `work_unit`). The remaining catalog
(`evidence_obligation`, `checkpoint`, `assessment`, `lesson`) + the shared enums module land
as those kinds (and their enum fields, e.g. `checkpoint.result`) are wired in — each with its
own tests. `validate` NEVER raises: malformed input returns error strings, not exceptions.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

_DRAFT = "https://json-schema.org/draft/2020-12/schema"

# kind -> JSON-Schema. Matches the real on-disk shapes (verified against the oauth-login
# fixture + graph_projection's readers): scope_item {id, statement};
# work_unit {id, title, derives_from:[scope_item.id, ...]}.
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

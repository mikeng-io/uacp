"""uacp-schema (Slice 1b / graph-engine D9-D10, node 33) — the per-kind schema registry.

The foundational, near-pure-leaf validation sink: a `kind -> JSON-Schema (draft 2020-12)`
registry + a thin `validate(kind, doc)`. It imports only `jsonschema` + stdlib; everything
that needs validation (uacp-lint, the entity-writer, Guardian) imports IT, not the reverse.

Two layers, two doctrines (node 33 — derived from the real authority per kind, NOT authored to
fixtures): the package docs + node-items from `scripts/validate_uacp_artifacts.py`; the small
State/Resolve docs (scope/lessons/run_registry) from their Heartgate-wired authority
`engines/domain/artifact_schema.py` (whose required_fields omit `kind` → it's optional-const here):

* **Node-item shapes** (scope_item / work_unit / evidence_obligation / checkpoint /
  assessment) — the graph-projection node kinds. CLOSED-world (`additionalProperties:false`),
  small + fully enumerated. SHAPE only: required fields + the real enums. The referential
  invariants (a work_unit must be covered by a scope_item; an assessment must cite evidence)
  live in the PROJECTION / uacp-lint, NOT here — so e.g. `derives_from` is OPTIONAL on a
  work_unit (the real PIV validator requires only id/intent/expected_outputs; coverage is a
  projection edge, not a shape rule).

* **Document kinds** (uacp.scope, the 9 package-model docs, run_registry, lessons) — the
  top-level YAML artifacts the entity-writer creates. OPEN-world for the rich package docs
  (the runtime validator uses `check_required` and ALLOWS extra fields, so a closed schema
  would false-reject real docs); they validate required fields + the `kind`/`phase` consts +
  key enums. Closed-world tightening (enumerate every field) is a later per-kind ratchet. The
  small, stable docs (scope/run_registry/lessons) stay closed. The deeper cross-artifact
  REFERENTIAL checks remain in the validator that becomes uacp-lint.

`validate` NEVER raises — malformed input returns error strings, not exceptions.
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

_DRAFT = "https://json-schema.org/draft/2020-12/schema"

# Enums — closed vocabularies (D9), grounded in validate_uacp_artifacts.py.
# The per-evidence / per-assessment outcome vocabulary is {pass,warn,block,deferred}
# (V:961 execution_checkpoint evidence `result`; V:1052 piv_assessment `state`) — NOT the
# old spike {pass,fail}.
_OUTCOME = ("pass", "warn", "block", "deferred")
_BLAST_RADIUS = ("low", "medium", "high", "critical")  # artifact_schema.BlastRadius
_CHECKPOINT_TYPES = (
    "before_side_effect",
    "after_work_unit",
    "pre_verify_handoff",
    "deviation",
    "remediation",
)

# kind -> JSON-Schema. Node-items derived from the PIV/checkpoint/assessment validators;
# document kinds from the per-kind validate_* functions in validate_uacp_artifacts.py.
_SCHEMAS: dict[str, dict[str, Any]] = {
    # ---- Node-item shapes (graph-projection node kinds; closed-world, shape-only) ----------
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
        # Real PIV validator (V:845-852) requires id + intent + expected_outputs. `derives_from`
        # is NOT required there — it is the projection's PROPOSE->PLAN coverage edge, validated as
        # a referential invariant by the projection (GP_ORPHAN_WORK_UNIT), not as a shape rule.
        "required": ["id", "intent", "expected_outputs"],
        "properties": {
            "id": {"type": "string", "description": "Stable work-unit identity (wu-*)."},
            "intent": {"type": "string", "description": "What this unit of work intends."},
            "expected_outputs": {"description": "Declared outputs (list or prose)."},
            "derives_from": {
                "type": "array",
                "items": {"type": "string"},
                "description": "scope_item ids this work_unit covers (the projection coverage "
                "edge); OPTIONAL at the shape layer — coverage is enforced by the projection.",
            },
        },
    },
    "evidence_obligation": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # Real PIV validator (V:861-871): id + evidence_type + required + sufficiency. work_unit_id
        # is OPTIONAL-but-cross-checked (V:866) — present-and-unknown blocks, but it may be absent.
        "required": ["id", "evidence_type", "required", "sufficiency"],
        "properties": {
            "id": {"type": "string", "description": "Stable obligation identity (ev-*)."},
            "evidence_type": {"type": "string", "description": "Kind of evidence required."},
            "required": {"type": "boolean", "description": "Whether this obligation is mandatory."},
            "sufficiency": {"type": "string", "description": "What makes the evidence sufficient."},
            "work_unit_id": {
                "type": "string",
                "description": "The work_unit this obligation is for (the obligation_for edge); "
                "optional at the shape layer, cross-checked by the projection/uacp-lint.",
            },
        },
    },
    "checkpoint": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # The execution_checkpoint's evidence[] item (V:945-973): obligation_id (cross-ref),
        # result enum, summary. result is {pass,warn,block,deferred}, NOT {pass,fail}.
        "required": ["result"],
        "properties": {
            "id": {
                "type": "string",
                "description": "Checkpoint/evidence identity (cp-*), optional.",
            },
            "obligation_id": {
                "type": "string",
                "description": "The obligation this records (checkpoint_of edge).",
            },
            "work_unit_id": {
                "type": "string",
                "description": "The work_unit checkpointed (optional).",
            },
            "result": {
                "enum": list(_OUTCOME),
                "description": "Checkpoint outcome (pass|warn|block|deferred).",
            },
            "summary": {"type": "string", "description": "What the checkpoint records."},
        },
    },
    "assessment": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # piv_assessment.assessments[] item (V:1045-1055): obligation_id + state + evidence_refs.
        # NOTE the real outcome field is `state` (not `result`), enum {pass,warn,block,deferred}.
        "required": ["obligation_id", "state", "evidence_refs"],
        "properties": {
            "id": {"type": "string", "description": "Assessment identity (as-*); optional."},
            "obligation_id": {
                "type": "string",
                "description": "The evidence_obligation this assessment verifies.",
            },
            "state": {
                "enum": list(_OUTCOME),
                "description": "Assessment outcome (pass|warn|block|deferred).",
            },
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "checkpoint ids cited; >=1 — an assessment with no evidence "
                "is a self-attesting closure (forbidden).",
            },
        },
    },
    # ---- Document kinds: small/stable = closed-world (fully enumerated) ----------------------
    "uacp.scope": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # AS-BUILT authority: artifact_schema.ScopeSchema.required_fields (run_id/write_paths/
        # blast_radius/rollback_path) — `kind` is NOT required there, so it's optional-const here
        # (validated when present; the entity-writer injects it), matching run_registry.
        "required": ["run_id", "write_paths", "blast_radius", "rollback_path"],
        "properties": {
            "kind": {
                "const": "uacp.scope",
                "description": "Optional; validated as const when present.",
            },
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
            "no_writes_intended": {
                "type": "boolean",
                "description": "Sentinel: scope intentionally declares no governed writes.",
            },
            "self_patch_write_authority": {
                "type": "object",
                "description": "Optional self-repair authority; shape enforced by the gate.",
            },
            "api_surfaces": {"description": "Optional; type unconstrained until grounded."},
            "runtime_surfaces": {"description": "Optional; type unconstrained until grounded."},
            "migrations": {"description": "Optional; type unconstrained until grounded."},
            "side_effects": {"description": "Optional; type unconstrained until grounded."},
        },
    },
    # uacp.triage — the admission verdict (TRIAGE serialize). OPEN-world: the producer
    # (skills/uacp-triage) emits optional fields the gate does not require (granularity, council,
    # human_involvement, artifact_policy); closing it would false-reject real docs.
    # `granularity_level` is the canonical composite-granularity REQUIRED key — gate-selection, the
    # route-bands, and validate_triage all REQUIRE it (composite_granularity is the value the gate
    # actually scores on; granularity_level is the contract key, never read). The triage skill now
    # emits it (with the newer composite_granularity / phase_local_granularity), so it is required
    # here too (producer<->consumer reconciled 2026-06-24).
    "uacp.triage": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "triage_id",
            "request_summary",
            "authority",
            "factor_scores",
            "routing_outcome",
            "next_step",
            "granularity_level",
        ],
        "properties": {
            "kind": {"const": "uacp.triage"},
            "triage_id": {"type": "string", "minLength": 1},
            "request_summary": {"type": "string", "minLength": 1},
            "authority": {
                "type": "object",
                "properties": {"status": {"enum": ["pass", "warn", "block"]}},
            },
            "factor_scores": {"type": "object"},
            "granularity_level": {"type": "integer"},
            "routing_outcome": {
                "enum": [
                    "direct",
                    "lightweight",
                    "standard",
                    "full_governance",
                    "block_or_clarify",
                ],
            },
            "track": {"enum": ["standard", "goal-driven"]},
            "next_step": {"type": "string", "minLength": 1},
        },
    },
    # uacp.brainstorm_scope_package — the bounded scope crossing brainstorm->triage (BRAINSTORM
    # serialize). FLAT shape (reconciled 2026-06-24): the phase-7 doc, the e2e producer, and this
    # schema now all use flat root admission fields — the nested selected_scope/estimated_governance
    # wrappers are retired (nothing consumed them; the Heartgate only globs for file-existence, so
    # this schema IS the shape contract at write time). `routing_advisory` is enum'd to the four
    # governance DEPTHS (direct/lightweight/standard/full_governance) — NOT the 5-value
    # routing_outcome set: `block_or_clarify` is impossible here because the package is only written
    # when admitting (enter_uacp==true), so "don't admit / clarify first" cannot apply. OPEN-world
    # for the advisory / provenance extras (approach_id, signals, anticipated_phases, risks, …).
    "uacp.brainstorm_scope_package": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "title",
            "description",
            "in_scope",
            "declared_side_effects",
            "authority",
            "routing_advisory",
        ],
        "properties": {
            "kind": {"const": "uacp.brainstorm_scope_package"},
            "title": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
            "in_scope": {"type": "array", "minItems": 1},
            "authority": {"type": "object", "properties": {"source": {"type": "string"}}},
            "routing_advisory": {
                "enum": ["direct", "lightweight", "standard", "full_governance"],
            },
        },
    },
    "uacp.run_registry": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # AS-BUILT: the uacp_run_registry_update writer emits {schema_version, active_runs} and
        # never a top-level `kind` (run-registry is STATE), so `kind` is NOT required.
        "required": ["active_runs"],
        "properties": {
            "kind": {"const": "uacp.run_registry", "description": "Optional; the writer omits it."},
            "schema_version": {"type": "string"},
            "active_runs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["run_id"],
                    "properties": {
                        "run_id": {"type": "string"},
                        "phase": {"type": "string"},
                        "write_paths": {"type": "array", "items": {"type": "string"}},
                        "scope_artifact_path": {"type": "string"},
                        "started_at": {"type": "integer"},
                        "goal_id": {
                            "type": "string",
                            "description": "Goal-driven track only (optional).",
                        },
                    },
                },
            },
        },
    },
    "uacp.lessons": {
        "$schema": _DRAFT,
        "type": "object",
        "additionalProperties": False,
        # AS-BUILT authority: artifact_schema.LessonsSchema (run_id/lessons) — `kind` NOT required
        # there, so it's optional-const here (matching scope + run_registry).
        "required": ["run_id", "lessons"],
        "properties": {
            "kind": {
                "const": "uacp.lessons",
                "description": "Optional; validated as const when present.",
            },
            "run_id": {"type": "string", "minLength": 1},
            "lessons": {"type": "array", "items": {"type": "object"}},
        },
    },
    # ---- Package-model document kinds: rich = OPEN-world (required + consts + key enums) ------
    # Derived from validate_uacp_artifacts.py per-kind validators. additionalProperties is left
    # OPEN because the runtime validator allows extra fields (check_required); a closed schema
    # would false-reject real docs. Referential checks stay in uacp-lint.
    # uacp.proposal (D43): the registered, entity-write-routable PROPOSE artifact that carries the
    # KEYED scope.in_scope:[{id,statement}] — the source of the projection's scope_item nodes (so
    # GP_UNCOVERED/GP_ORPHAN can bind). Required set mirrors validate_proposal; the scope block is
    # TYPED here (keyed items, >=1) — the LOAD-BEARING enforcement of the keyed shape: it runs at
    # WRITE time (entity_write -> has_schema -> schema.validate), since proposal-scope is self-
    # contained. Contrast the PIV: work_unit.derives_from is a CROSS-artifact reference, so it stays
    # OPTIONAL in the shape schema and is required at the Heartgate TRANSITION by
    # validate_piv_contract — an intentional shape-vs-referential asymmetry between the ends. NOTE:
    # package-selection-mode runs carry scope in markdown (not a keyed uacp.proposal), so the two
    # coverage checks do not bind for that representation — a documented residual.
    "uacp.proposal": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "proposal_id",
            "run_id",
            "phase",
            "triage_artifact",
            "title",
            "objective",
            "scope",
            "declared_side_effects",
            "authority",
            "human_involvement",
        ],
        "properties": {
            "kind": {"const": "uacp.proposal"},
            "phase": {"const": "propose"},
            "run_id": {"type": "string", "minLength": 1},
            "scope": {
                "type": "object",
                "required": ["in_scope", "out_of_scope"],
                "properties": {
                    "in_scope": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["id", "statement"],
                            "properties": {
                                "id": {"type": "string", "minLength": 1},
                                "statement": {"type": "string"},
                            },
                        },
                    },
                    "out_of_scope": {"type": "array"},
                },
            },
        },
    },
    "uacp.proposal_package_selection": {
        "$schema": _DRAFT,
        "type": "object",
        "required": ["kind", "phase", "run_id", "work_heart", "universal_core", "selected_modules"],
        "properties": {
            "kind": {"const": "uacp.proposal_package_selection"},
            "phase": {"const": "propose"},
            "run_id": {"type": "string", "minLength": 1},
        },
    },
    "uacp.plan_package_selection": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "work_heart",
            "universal_core",
            "selected_modules",
            "transition_readiness",
        ],
        "properties": {
            "kind": {"const": "uacp.plan_package_selection"},
            "phase": {"const": "plan"},
            "run_id": {"type": "string", "minLength": 1},
        },
    },
    "uacp.phase_intent_verification_contract": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "applies_to_phase",
            "phase_intent",
            "work_units",
            "evidence_obligations",
            "checkpoint_policy",
            "intent_drift_conditions",
            "next_phase_handoff",
        ],
        "properties": {
            "kind": {"const": "uacp.phase_intent_verification_contract"},
            "phase": {"const": "plan"},
            "applies_to_phase": {"const": "execute"},
            "run_id": {"type": "string", "minLength": 1},
            # D43 (Codex PR#8 P1): every work_unit MUST declare coverage (>=1 derives_from
            # scope_item id) — enforced HERE at WRITE time via entity_write, symmetric with the
            # proposal's keyed scope (so a derives_from-less PIV can't pass write + a self-gated
            # plan-exit). The referential resolve of those ids stays in the projection
            # (GP_PHANTOM_EDGE); validate_piv_contract keeps it as transition defense-in-depth.
            "work_units": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["derives_from"],
                    "properties": {"derives_from": {"type": "array", "minItems": 1}},
                },
            },
            "evidence_obligations": {"type": "array", "minItems": 1},
        },
    },
    "uacp.execution_checkpoint": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "checkpoint_id",
            "piv_contract",
            "checkpoint_type",
            "work_unit_id",
            "work_performed",
            "decisions",
            "evidence",
            "intent_drift",
            "invariants",
            "next_phase_readiness",
        ],
        "properties": {
            "kind": {"const": "uacp.execution_checkpoint"},
            "phase": {"const": "execute"},
            "run_id": {"type": "string", "minLength": 1},
            "checkpoint_type": {"enum": list(_CHECKPOINT_TYPES)},
            "evidence": {"type": "array", "minItems": 1},
            # The boundary / negative-judgment slot: EXECUTE measures the negative too — what it
            # did NOT do (stayed inside its declared bounds) is evidence. Typed as an object here;
            # the four boundary keys (authority/write_boundary/rollback/privacy_preserved) are
            # required by the OFFLINE validator (validate_uacp_artifacts.py), not at write time —
            # so a minimal / in-flight checkpoint is not false-rejected (verify schema vs producer).
            "invariants": {"type": "object"},
        },
    },
    "uacp.piv_assessment": {
        "$schema": _DRAFT,
        "type": "object",
        "required": ["kind", "phase", "run_id", "piv_contract", "assessments", "overall_status"],
        "properties": {
            "kind": {"const": "uacp.piv_assessment"},
            "phase": {"const": "verify"},
            "run_id": {"type": "string", "minLength": 1},
            "assessments": {"type": "array", "minItems": 1},
        },
    },
    "uacp.verification_package": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "verified_facts",
            "assumptions",
            "deferred_items",
            "warnings",
            "blockers",
            "findings_dispositions",
            "resolve_readiness",
            "semantic_package",
        ],
        "properties": {
            "kind": {"const": "uacp.verification_package"},
            "phase": {"const": "verify"},
            "run_id": {"type": "string", "minLength": 1},
        },
    },
    "uacp.verify_resolve_readiness": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "ready_for_resolve",
            "overall_status",
            "verification_package",
            "verified_facts_summary",
            "piv_summary",
            "evidence_cluster_summary",
            "residual_risks",
            "open_assumptions",
            "deferred_items",
            "blockers",
            "heartgate_coherence_status",
            "self_approval_guard",
            "decision_rationale",
            "accepted_by",
        ],
        "properties": {
            "kind": {"const": "uacp.verify_resolve_readiness"},
            "phase": {"const": "verify"},
            "run_id": {"type": "string", "minLength": 1},
        },
    },
    "uacp.resolve_package": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "verify_resolve_readiness",
            "semantic_package",
            "final_decision",
            "residual_risks",
            "deferred_items",
            "lesson_dispositions",
            "operator_handoff",
        ],
        "properties": {
            "kind": {"const": "uacp.resolve_package"},
            "phase": {"const": "resolve"},
            "run_id": {"type": "string", "minLength": 1},
            "lesson_dispositions": {"type": "array", "minItems": 1},
        },
    },
    "uacp.resolve_closure": {
        "$schema": _DRAFT,
        "type": "object",
        "required": [
            "kind",
            "phase",
            "run_id",
            "resolve_package",
            "verify_resolve_readiness",
            "final_decision",
            "closed_scope",
            "residual_risks",
            "deferred_items",
            "lesson_dispositions",
            "operator_handoff",
            "state_disposition",
        ],
        "properties": {
            "kind": {"const": "uacp.resolve_closure"},
            "phase": {"const": "resolve"},
            "run_id": {"type": "string", "minLength": 1},
            "closed_scope": {"type": "array", "minItems": 1},
        },
    },
}

# uacp.check.* — frozen generative-gate checks (capsule #3, slice 0c). Open-world (like the
# other document kinds): enforce the COMMON authoring contract every catalog kind shares — a
# check must declare WHAT it measures (`from.target`) and HOW (`bind`) — plus the writer-injected
# `kind`/`run_id` consts. Bind RESOLVABILITY (does the artifact/edge/obligation exist?) is the
# replay engine's fail-closed concern (ERROR on an unresolvable bind, #503 class A), deliberately
# NOT duplicated here. The catalog tuple is local to keep this module a stdlib+jsonschema leaf; a
# registry-parity test pins it to layout.CHECK_KINDS so the two cannot drift.
_CHECK_SUBKINDS = (
    "field_equals",
    "field_present",
    "edge_exists",
    "artifact_integrity",
    "obligation_satisfied",
)


def _check_schema(sub: str) -> dict[str, Any]:
    props: dict[str, Any] = {
        "kind": {"const": f"uacp.check.{sub}"},
        "run_id": {"type": "string", "minLength": 1},
        "id": {"type": "string", "minLength": 1},
        "from": {
            "type": "object",
            "required": ["target"],
            "properties": {"target": {"type": "string", "minLength": 1}},
        },
        "bind": {"type": "object"},
        # A slice-0 check GATES — it cannot be authored non-blocking (reviewer finding: a
        # `warn` severity let a gated agent self-demote a failing check). Policy-graded
        # severities are an L2 concern; until then the only governed value is `block`.
        "severity": {"const": "block"},
    }
    required = ["kind", "run_id", "id", "from", "bind"]
    # field_equals MUST declare what value it expects (mimo #3): a field_equals with no `expect`
    # always FAILs at replay (exp = _MISSING), so reject it at write time rather than ship a check
    # that can never pass. The other kinds do not use `expect` (field_present/artifact_integrity/
    # edge_exists/obligation_satisfied), so it stays optional for them.
    if sub == "field_equals":
        props["expect"] = {"type": "object", "required": ["value"]}
        required = [*required, "expect"]
    return {
        "$schema": _DRAFT,
        "type": "object",
        "required": required,
        "properties": props,
    }


for _sub in _CHECK_SUBKINDS:
    _SCHEMAS[f"uacp.check.{_sub}"] = _check_schema(_sub)


def has_schema(kind: str) -> bool:
    """True if ``kind`` has a registered declarative schema.

    The entity-writer's validate-on-write is RATCHETED on this (node 33 / node 35 §5):
    only kinds with a registered schema are shape-enforced at write time."""
    return kind in _SCHEMAS


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

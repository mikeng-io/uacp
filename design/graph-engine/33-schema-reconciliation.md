---
type: contract
title: Schema Reconciliation — the per-kind shape source under the projection model
description: >-
  Resolves the as-built 4-way schema authority into a clean layering under D42 (the graph is a
  PROJECTION over the package model): schema.py = the single DECLARATIVE shape source (closed-world
  JSON-Schema, per kind); validate_uacp_artifacts.py = the REFERENTIAL/cross-artifact authority that
  becomes uacp-lint and DELEGATES shape to schema.py; artifact_schema.py folds in; config keeps only
  doctrine knobs. Fixes the spike-shaped node-items, adds the 9 missing package-model kinds, and sets
  the rule that every schema is DERIVED FROM its real producer/consumer (not authored to fixtures).
tags: [uacp, graph-engine, schema, reconciliation, uacp-lint, manifest, as-built, D41, D42]
timestamp: 2026-06-23
edges:
  - {dst: 02-decisions, rel: depends_on, provenance: asserted}      # D41 (prerequisite) + D42 (projection model)
  - {dst: 24-asbuilt-manifest-taxonomy, rel: depends_on, provenance: asserted}
  - {dst: 25-schema-source-spec, rel: depends_on, provenance: asserted}
  - {dst: 16-schema-registry, rel: relates_to, provenance: asserted}
  - {dst: 34-manifest-engine, rel: relates_to, provenance: asserted}
---

# Schema Reconciliation — the per-kind shape source

> **Why this node.** D41 froze all schema work behind one prerequisite (spike clean-break vs the
> kernel package model); D42 resolved it — **the graph is a projection over the package model**
> (synthesis, not replace/schematize). But the *schemas themselves* are still unreconciled: there
> are **four** authorities, `schema.py` is **not wired** and is **spike-shaped**, and it has **no**
> entries for the 9 real package-model kinds. The Codex PR-#2 findings (schemas authored to their
> own fixtures, not to the real producer/consumer) are instances of exactly this. This node sets the
> target layering + the derivation rule so Phase C's entity-writer (node 35) has a real shape source
> to validate against.

## 1. The as-built today (grounded)

Four authorities, overlapping and drifting (`tests/unit/uacp_core/test_schema.py` is the only thing
holding `schema.py` consistent — with its own fixtures):

| # | Authority | Owns | Wired at runtime? |
|---|---|---|---|
| 1 | `scripts/validate_uacp_artifacts.py` | per-kind SHAPE **+** cross-artifact REFERENTIAL checks (~16 kinds in `main()`) | **YES — dominant.** Heartgate dynamically imports it (`engines/heartgate/heartgate.py:457-519`, `_offline_validate_artifacts`) and runs **8 kind-validators** at transition time — phase_transition, piv_contract, execution_checkpoint, piv_assessment, verification_package, verify_resolve_readiness, resolve_package, resolve_closure — plus the always-run `validate_configs` / `validate_transition_config_consistency` / `validate_finding_states`. (`proposal_package_selection` / `plan_package_selection` are CLI-only, not gate-dispatched.) |
| 2 | `engines/domain/artifact_schema.py` | Pydantic shapes for intent / scope / lessons / evidence_disposition / run_registry | YES — Heartgate reads `artifact_schemas_dict()` for the 4 hub doc-validators |
| 3 | `engines/domain/schema.py` | per-kind JSON-Schema + `validate()` (closed-world) | **NO — tests only.** node-items are spike-shaped; 0 package-kind entries |
| 4 | `config/uacp.toml` + `phase-transitions.yaml` | doctrine knobs (allowed_transitions, gate rules, tool_path_capabilities) | YES |

**Concrete defects in `schema.py` (the D42 re-grounding target):**
- `work_unit` = `{id, title, derives_from}` — REAL (PIV contract) is `{id, intent, expected_outputs}` + `derives_from` (the net-new seam). `title` is wrong; `intent`/`expected_outputs` missing.
- `evidence_obligation` = `{id, work_unit_id, statement?}` — REAL is `{id, work_unit_id, evidence_type, required, sufficiency}`.
- `checkpoint` / `assessment` `result` enum = `{pass, fail}` — REAL vocabulary is `{pass, warn, block, deferred}`.
- **0 entries** for: proposal_package_selection, plan_package_selection, phase_intent_verification_contract, execution_checkpoint, piv_assessment, verification_package, verify_resolve_readiness, resolve_package, resolve_closure.
- Cross-authority conflicts: `uacp.lessons` requires `kind` in schema.py but not in artifact_schema.py (the wired one); `run_registry` items carry `goal_id` in schema.py but not in artifact_schema.py.

## 2. The target layering (the decision)

Under D42, split **shape** from **reference**, and pick ONE owner per concern:

- **`schema.py` = the single DECLARATIVE shape source.** Per-kind closed-world JSON-Schema: required fields, types, enums, `kind` const, `additionalProperties:false`. SHAPE ONLY — no cross-artifact resolution.
- **`validate_uacp_artifacts.py` → `uacp-lint` = the REFERENTIAL authority.** Keeps the cross-artifact/semantic checks it alone does (FK resolution across sibling docs, carry-forward, path-binding, coverage). Its per-kind **shape** checks **delegate to `schema.py`** (call `validate(kind, doc)` first, then do the referential layer). One shape source, two consumers (the gate via uacp-lint; the entity-writer via schema.py directly — node 35).
- **`artifact_schema.py` folds into `schema.py`.** The Pydantic intent/scope/lessons/run_registry shapes become schema.py entries; Pydantic retires. EXCEPT the two **Markdown** specs (`intent` section-list, `evidence_disposition` paired-paths) which are NOT JSON-Schema document kinds — they stay as markdown-validation specs (node 25), owned by uacp-lint.
- **config keeps only doctrine** (allowed_transitions, gate enable/enforcement, tool_path_capabilities) — never per-kind field lists.

Result: **shape has exactly one home (`schema.py`); reference has one home (uacp-lint); doctrine has one home (config).** The 4-way collapses to a DAG, not a mesh.

## 3. The derivation rule (the Codex lesson, made structural)

> **Every `schema.py` kind is DERIVED FROM its real producer/consumer — never authored to a fixture.**

For each kind: read the writer that emits it (governed writers / the entity-writer) AND the validator
that consumes it (`validate_uacp_artifacts.py`), and make the schema the intersection contract of
both. Test the **producer-shaped** document (e.g. the run-registry writer's actual `{schema_version,
active_runs}` with no `kind`), not a hand-authored fixture. (PR-#2's two bugs — scope missing
`no_writes_intended`/`self_patch_write_authority`, run_registry requiring a `kind` the writer omits —
were both fixture-authored schemas; both are now fixed, and this rule prevents the class.) This is the
generative-gate principle (verification-method node 10) applied to schemas: comprehend the real shape →
serialize it → it then validates deterministically.

## 4. What this node fixes / adds (the work-list, derived from §1)

1. **Re-ground the 4 node-items** to the real PIV/checkpoint/assessment shapes (work_unit `intent`+`expected_outputs`; obligation `evidence_type`/`required`/`sufficiency`; result enum `{pass,warn,block,deferred}`), keeping `scope_item.id` + `work_unit.derives_from` as the D42 seam keys.
2. **Add the 9 package-model kinds** to `schema.py`, each derived from its `validate_uacp_artifacts.py` validator (the per-kind shapes are inventoried in node 25 / the SA-B as-built map).
3. **Resolve the conflicts** by applying §3 (derive from the wired authority + the writer) — and state the answer, not just the rule:
   - `uacp.lessons` `kind`: the wired validator (`artifact_schema.py:90` `LessonsSchema`, via `heartgate.py:1068`) does NOT require it, but the writer/fixture emits it → **optional const** (validated when present), matching run_registry. (Today `schema.py:209` wrongly requires it.)
   - `uacp.run_registry` items `goal_id`: the writer (`state.py`) DOES emit `goal_id` on goal-driven runs → **include it** in the item schema (schema.py:199 already does; `artifact_schema.py` `_RUN_REGISTRY` must add it when it folds in).
   - General rule for `kind`: required where the writer emits it (the package kinds carry `kind`); optional-const where the writer omits it (run_registry).
4. **Author golden fixtures from the writer** for the 9 kinds (today only 3 of 17 kinds have fixtures), each a producer-shaped document.

## 5. Sequencing (incremental ratchet — do NOT boil the ocean)

Mirror the pyright-strict / ruff ratchet: grow `schema.py` + flip uacp-lint to delegate **one kind at
a time**, each step suite-green. Order = leaf-first (the node-items + scope/run_registry/lessons,
already partly there) → then the package gates (proposal/plan selection) → then the evidence chain
(PIV / checkpoint / assessment / verification / resolve). Each kind: derive shape → add to schema.py →
golden producer-fixture → flip that kind's uacp-lint shape-check to delegate → green. `artifact_schema.py`
retires only after its 4 kinds are migrated.

## To expand
- The exact per-kind JSON-Schema bodies (this node sets the rule + owner; node 25 holds the shapes).
- The `uacp-lint` delegation seam (how a validator calls `schema.validate(kind, doc)` then layers reference) — ties to node 34 (Manifest engine) §uacp-lint.
- Whether `schema.py` relocates into `engines/manifest/` or stays a domain leaf consumed by it (node 34 decides the home; this node only fixes the content + authority).

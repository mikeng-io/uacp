---
type: analysis
title: Graph Engine — Schema Source Spec (the real per-kind shapes schema.py must encode)
description: The authoring reference for schema.py + uacp-lint, extracted (and spot-verified) from the real validators — validate_uacp_artifacts.py (27 fns) + artifact_schema.py. Per kind: the SHAPE half (→ declarative schema.py) vs the REFERENTIAL half (→ stays imperative in uacp-lint). Exhaustive field detail lives in the cited validate_* function; this maps the split + the authoring order so schema.py never re-invents shapes (the inc-3b failure).
tags: [graph-engine, schema, uacp-lint, shape, referential, authoring-reference]
timestamp: 2026-06-22
edges:
  - {dst: 24-asbuilt-manifest-taxonomy, rel: depends_on, provenance: derived}
  - {dst: 16-schema-registry, rel: realizes, provenance: asserted}
  - {dst: 02-decisions, rel: realizes, provenance: asserted}
---

# Schema Source Spec — what `schema.py` must encode (authoring reference)

Extracted from the real validators (`scripts/validate_uacp_artifacts.py` + `engines/domain/
artifact_schema.py`) per D41/D42 and spot-verified against source. The **field-exhaustive
detail is in the cited `validate_*` function** (the source of truth) — this node maps the
**SHAPE vs REFERENTIAL split** + the **authoring order**, so `schema.py` serializes from
reality (the inc-3b failure was authoring from spike fixtures instead).

## The boundary: SHAPE (→ `schema.py`) vs REFERENTIAL (→ `uacp-lint`)

- **SHAPE** = JSON-Schema-expressible on one document in isolation: required fields, enums,
  types, nesting, non-empty arrays, `const`. → declarative `schema.py`.
- **REFERENTIAL** = everything else, three sub-kinds, all **stay imperative in `uacp-lint`**:
  1. **cross-file** — loads a sibling doc (e.g. checkpoint loads its PIV contract).
  2. **intra-doc FK** — a field must equal an id present in an array of the *same* doc
     (e.g. PIV `obligation.work_unit_id ∈ work_units[].id`) — not natively JSON-Schema.
  3. **conditional / consistency** — "if X then Y required", carry-forward, semantic-markdown,
     path-binding (`artifact must live under <dir>`), run-bound id checks.

`schema.py` owns #SHAPE; `uacp-lint` (the transformed `validate_uacp_artifacts.py`) keeps all
#REFERENTIAL. The kernel already enforces the referential half — we are not rebuilding it.

## Authoring order (clean shape first; defer markdown + legacy)

1. **Node-items (re-grounded)** — the entities inside the docs (below). Corrects inc-3a.
2. **Clean YAML document kinds** — `triage`, `scope`, `run_registry`, `phase_intent_verification_contract`, `execution_checkpoint`, `piv_assessment`, `proposal_package_selection`, `plan_package_selection`, `verification_package`, `verify_resolve_readiness`, `resolve_package`, `resolve_closure`, `phase_transition`, `council_synthesis`, `evidence_cluster`, `gate_selection`, `current_state`.
3. **Markdown kinds** — `intent`, `evidence_disposition`: **NOT JSON-Schema document kinds** (required *sections* / paired files). Relocate their constants out of Pydantic; validation stays prose-aware in `uacp-lint`.
4. **Skip (legacy/unused)** — `uacp.proposal`, `uacp.execute_task`: `validate_*` fns exist but the kinds are **not in `main()`'s dispatch** (validate_uacp_artifacts.py ~1587-1620). Do not schematize.

## Node-items — REAL shapes (corrects inc-3a; the concepts were right, the fields invented)

| node-item | REAL shape (source) | inc-3a had (WRONG) |
|---|---|---|
| `work_unit` | `{id, intent, expected_outputs}` (+ `derives_from` = the **seam**, net-new) — PIV contract `work_units[]`, validate_piv_contract:850 | `{id, title, derives_from}` |
| `evidence_obligation` | `{id, work_unit_id, evidence_type, required, sufficiency}` — PIV `evidence_obligations[]`, :869 | `{id, work_unit_id, statement?}` |
| `checkpoint` (= the `execution_checkpoint` doc, 1/work_unit) | big doc: `{…, work_unit_id, evidence:[{obligation_id, result, …}], …}`; result enum `{pass, warn, block, deferred}` — validate_execution_checkpoint:961 | `{id, work_unit_id, result∈{pass,fail}}` |
| `assessment` | `{obligation_id, state, evidence_refs, (owner/next_action/result_reason if warn\|block\|deferred)}`; **state enum `{pass, warn, block, deferred}`** — piv_assessment `assessments[]`, validate_piv_assessment:1052 | `{obligation_id, evidence_refs, result∈{pass,fail}}` |
| `scope_item` | **does not exist on disk** — the proposal `scope` is *markdown* (validate_proposal_package_selection:696-704). `scope_item` + its `id` are the **net-new seam** (D42), not an as-built shape. | `{id, statement}` |

**Two enum corrections inc-3a got wrong:** the result/state vocabulary is **`{pass, warn, block, deferred}`**, not `{pass, fail}`. (`_RESULT = ("pass","fail")` in schema.py is spike-shaped.)

## Document kinds — SHAPE summary + referential split (cite the validator for full fields)

| kind | fmt | SHAPE (required count + key enums) | REFERENTIAL (→ uacp-lint) | validate ref |
|---|---|---|---|---|
| `uacp.triage` | YAML | 8 req; `routing_outcome`∈{direct,lightweight,standard_uacp,full_governance,block_or_clarify}; `authority.status`∈{pass,warn,block}; `track`∈{standard,goal-driven} | none | :409 |
| `uacp.scope` | YAML | req: run_id, write_paths, blast_radius, rollback_path; `blast_radius`∈{low,medium,high,critical}; 6 optional | none (path reachability checked elsewhere) | artifact_schema.py ScopeSchema:65 |
| `uacp.run_registry` | YAML | req: active_runs; item: {run_id, phase, write_paths, scope_artifact_path, started_at} | none | artifact_schema.py:133 |
| `uacp.phase_intent_verification_contract` | YAML | 10 req; non-empty work_units `{id,intent,expected_outputs}` + evidence_obligations `{id,work_unit_id,evidence_type,required,sufficiency}`; checkpoint_policy.required_checkpoints∈VALID_PIV_CHECKPOINTS | intra-doc FK: obligation.work_unit_id ∈ work_units[].id (:867) | :828 |
| `uacp.execution_checkpoint` | YAML | 13 req; `checkpoint_type`(5), `evidence[].result`(4), `next_phase_readiness.status`(3)+target_phase=verify; invariants block | loads PIV (:918); work_unit_id ∈ PIV (:934); evidence.obligation_id ∈ PIV (:950); pass-evidence artifact exists+run-bound (:968); semantic-md (:1012) | :908 |
| `uacp.piv_assessment` | YAML | 6 req; `assessments[].state`∈{pass,warn,block,deferred}; non-empty; no dup obligation_id | loads PIV (:1031); obligation_id ∈ PIV required (:1050); coverage (all required assessed, :1060); overall_status=pass ⇒ no block (:1063) | :1026 |
| `uacp.proposal_package_selection` | YAML | req: phase=propose, run_id, work_heart, universal_core(8 keys), selected_modules(non-empty), not_applicable; status∈{covered,not_applicable}; plan_readiness.status(4) | package dir exists; each covered `artifact` exists + under `proposals/{run_id}/` + semantic-md (:677-731) | :670 |
| `uacp.plan_package_selection` | YAML | req: phase=plan, run_id, work_heart, universal_core(9 keys), selected_modules, not_applicable(+revisit_trigger), transition_readiness.status(3) | scope artifact exists (:750); package dir; artifacts exist+under `plans/{run_id}/`+semantic-md | :740 |
| `uacp.verification_package` | YAML | 11 req; assumptions.disposition(4); blockers.state(4); verified_facts/deferred/findings item shapes | package dir; source_path exists; 6 semantic-md artifacts; ready_for_resolve vs open blockers | :1067 |
| `uacp.verify_resolve_readiness` | YAML | 17 req; blockers.state(4); piv_summary.status(5); cluster.state∈VALID_CLUSTER_STATES; self_approval_guard.status(2) | loads verification_package + piv_assessment (kind+run_id match); cluster artifacts exist+run-bound; heartgate coherence lenses; many consistency gates (~16 total) | :1143 |
| `uacp.resolve_package` | YAML | 10 req; final_decision.status(3); lesson_dispositions.classification(5); operator_handoff (raw_inventory≠true) | loads readiness (kind+ready_for_resolve); 6 semantic-md; carry-forward risks+deferred from readiness | :1283 |
| `uacp.resolve_closure` | YAML | 12 req; final_decision.status(3); state_disposition.run_status(4)+memory_action(5); closed_scope items | loads resolve_package + readiness (+nested validate); closed_scope.source_artifact exists; carry-forward from 2 sources; blocked⇒not resolved | :1375 |
| `uacp.phase_transition` | YAML | ~15 req; decision∈{pass,warn,block}; terminal_kind enum; nested invariant_summary/warnings/deferred/handled_findings_chain/heartgate_coherence | accepted_exceptions + heartgate_coherence artifacts exist+run-bound; phase-linked gate artifacts (validate_adaptive_transition_linked_artifacts:284) | :226 |
| `uacp.council_synthesis` | YAML | 11 req (legacy aliases); verdict enum (16 vals); inspected_paths non-empty list; followup_depth≤max | finding states (self-contained) | :360 |
| `uacp.evidence_cluster` | YAML | 6 req; phase(6); state(5) — Pydantic EvidenceCluster | none | :519 (model: evidence_cluster.py) |
| `uacp.gate_selection` | YAML | 11 req; invariant_checks.status∈{pass,block}; selected_clusters.state(4) | none | :485 |
| `uacp.current_state` | YAML | kind + 8 pointer req; mutation_policy/bootstrap_closed/governed_mutation_active consts | 3 referenced artifacts exist + run-bound (:1485) | :1469 (fields: pointer.py:41) |

## Markdown kinds (NOT JSON-Schema document kinds)

| kind | fmt | what's validated | source |
|---|---|---|---|
| `uacp.intent` | **Markdown** | required *sections*: Success Definition, Explicit Out-of-Scope, Termination Condition, Authority Source | artifact_schema.py IntentSchema:50 |
| `uacp.evidence_disposition` | **Markdown (paired)** | paired `verified-facts.md` + `assumptions.md`; assumptions.disposition∈{accepted_risk,deferred,pending}; required header substrings (Fact/Disposition) | artifact_schema.py:93 |

Their *constants* (section lists, paired paths, disposition→requires) relocate out of Pydantic
so `artifact_schema.py`'s Pydantic-as-schema retires (D41); the section/paired checks stay in
`uacp-lint` (prose-aware, not declarative shape).

## What goes where (the transform target)

- **`schema.py`** (declarative): every node-item (real shapes) + the SHAPE column of every YAML
  document kind above. Closed-world, enums, `const` kind, `$ref`/`$defs` composition of node-items.
- **`uacp-lint`** (= transformed `validate_uacp_artifacts.py`, imperative, kept): every REFERENTIAL
  column — cross-file loads, intra-doc FKs, conditional/consistency, carry-forward, semantic-markdown,
  path-binding. Its per-kind shape checks **delegate to `schema.py`** (kill the imperative copies).
- **`graph_projection`** (separate thread): the cross-NODE closure, reading these real artifacts.

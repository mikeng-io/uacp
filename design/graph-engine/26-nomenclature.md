---
type: reference
title: UACP Control-Plane Nomenclature (canonical, as-built)
description: The single authoritative naming reference for the UACP control plane — every artifact KIND (document vs node-item vs corpus), the lifecycle/plane vocabulary, and a drift-guard for the terms that keep getting confused (PIV/PPV, scope/scope_item, the three "lessons", the package-selection envelopes). Grounded in the real code (validate_uacp_artifacts.py + config), NOT the spike. Read before naming anything.
tags: [uacp, nomenclature, glossary, kinds, reference, drift-guard]
timestamp: 2026-06-22
edges:
  - {dst: 24-asbuilt-manifest-taxonomy, rel: depends_on, provenance: derived}
  - {dst: 27-directory-taxonomy, rel: relates_to, provenance: asserted}
---

# UACP Control-Plane Nomenclature (canonical, as-built)

> **One name per concept.** If a name isn't here, it isn't canonical. Grounded in the real
> code (`scripts/validate_uacp_artifacts.py` dispatch + `config/uacp.toml`), not the design
> spike. For *architecture* vocabulary (planes / engines / gates / stores) see
> [18-glossary](18-glossary.md); **this node is authoritative for artifact KINDS** (18's
> node-kind list is the spike form — superseded here). Directory/file layout: [27-directory-taxonomy](27-directory-taxonomy.md).

## The three categories of "kind" (the distinction that keeps getting lost)

1. **Document kind** — a whole **file on disk** that carries a top-level `kind:` field and is
   validated as a unit (e.g. `uacp.scope`). These are what `schema.py` / `uacp-lint` validate.
2. **Node-item** — an **entity *inside* a document** (an array entry) or a **projected graph node**.
   It is **not a standalone file** and has **no on-disk `kind:`** (e.g. a `work_unit` lives inside
   the PIV contract's `work_units[]`). The graph engine *projects* these.
3. **Corpus kind** — a **knowledge-plane file** (`.uacp/knowledge|lessons/<id>.md`, OKF), distinct
   from the lifecycle manifest.

> Conflating #1 and #2 was the inc-3b error: `uacp.proposal/plan/execution` were authored as
> document kinds, but the kernel has no such files — the *work_unit* etc. are node-items inside
> the package-selection documents.

## Lifecycle phases

`brainstorm` (optional) → `triage` → `propose` → `plan` → `execute` → `verify` → `resolve`.

## Planes (WHAT — see 18-glossary for the engine/gate vocabulary)

- **relation / manifest plane** — the lifecycle documents + their structural edges. Files = truth.
- **knowledge plane** — the Oracle corpus (lessons + knowledge), semantic/embedded.
- **state plane** — run manifest, registry, pointer, ledger.
- **config / doctrine plane** — `config/*.yaml` + `config/uacp.toml`.
- *(deferred)* **code plane** — SCIP symbols.

## Document kinds (files on disk — the package-selection model)

| `kind:` | phase | meaning | format |
|---|---|---|---|
| `uacp.triage` | triage | scope calibration + granularity + routing + track | YAML |
| `uacp.proposal_package_selection` | propose | PROPOSE envelope: universal-core coverage + selected modules | YAML |
| `uacp.intent` | propose | the proposal **charter** (required *sections*) | **Markdown** |
| `uacp.plan_package_selection` | plan | PLAN envelope: universal-core coverage + modules | YAML |
| `uacp.scope` | plan | write-boundary (write_paths, blast_radius, rollback) | YAML |
| `uacp.phase_intent_verification_contract` | plan | **PIV contract**: work_units + evidence_obligations + checkpoint policy | YAML |
| `uacp.execution_checkpoint` | execute | one checkpoint per work_unit (evidence vs obligations) | YAML |
| `uacp.piv_assessment` | verify | per-obligation assessment + overall_status | YAML |
| `uacp.verification_package` | verify | VERIFY envelope: facts/assumptions/blockers/findings | YAML |
| `uacp.verify_resolve_readiness` | verify | RESOLVE-admission certification | YAML |
| `uacp.evidence_disposition` | verify | paired verified-facts + assumptions (required headers) | **Markdown** (paired) |
| `uacp.resolve_package` | resolve | RESOLVE envelope: decision + lessons disposition + handoff | YAML |
| `uacp.resolve_closure` | resolve | terminal closure record + state disposition | YAML |
| `uacp.lessons` | resolve | the RESOLVE **lessons artifact** (run_id + lessons[]) | YAML |
| `uacp.phase_transition` | (boundary) | Heartgate transition record | YAML |
| `uacp.council_synthesis` | (any) | council verdict + inspected paths + findings | YAML |
| `uacp.run_registry` | state | active-run registry | YAML |
| `uacp.current_state` | state | active-run pointer | YAML |
| `uacp.evidence_cluster` / `uacp.gate_selection` | (gate) | cluster instance / gate selection | YAML |
| `uacp.state_config` / `uacp.phase_transition_config` / `uacp.gate_selection_config` / `uacp.review_routing_config` / `uacp.evidence_cluster_registry` | config | doctrine configs | YAML |

*Legacy/unused (do not author):* `uacp.proposal`, `uacp.execute_task` — `validate_*` fns exist but the kinds aren't in the kernel dispatch.

## Node-items (entities inside documents / projected graph nodes — NOT files)

| node-item | lives inside | real fields (NOT the spike `{id,title}`) |
|---|---|---|
| `scope_item` | (proposal scope — currently **markdown**; the keyed form is the **net-new seam**) | `{id, statement}` (aspirational) |
| `work_unit` | PIV contract `work_units[]` | `{id, intent, expected_outputs}` (+ `derives_from` = seam) |
| `evidence_obligation` | PIV contract `evidence_obligations[]` | `{id, work_unit_id, evidence_type, required, sufficiency}` |
| `checkpoint` | = the `execution_checkpoint` **document** (1 per work_unit) | the doc, with `evidence[].obligation_id` |
| `assessment` | `piv_assessment` `assessments[]` | `{obligation_id, state, evidence_refs}`; `state ∈ {pass,warn,block,deferred}` |

## Corpus kinds (knowledge plane)

| kind | location | status |
|---|---|---|
| `lesson` (`Lesson` model) | `.uacp/lessons/<id>.md` | as-built |
| `knowledge_item` (`KnowledgeItem`; type ∈ {pattern,digest,analysis,contract}) | `.uacp/knowledge/<id>.md` | as-built |
| `observation` / `fact` / `procedure` / tiers `episode→pattern→rule` | (D30) | **designed, not built** |

## DRIFT GUARD — do not confuse these (the recurring failures)

| ✅ canonical | ❌ confused with | the distinction |
|---|---|---|
| **PIV** = Phase Intent Verification (`uacp.phase_intent_verification_contract`, `uacp.piv_assessment`) | **PPV** = post-phase-verification (legacy **ledger-gate rule**) | distinct concepts; the legacy ledger rule was renamed `piv→ppv` to *reserve* PIV. There is **no "PVV"**. |
| `uacp.scope` — the **write-boundary document** (write_paths/blast_radius) | `scope_item` — a **node-item** (an intent the plan must cover) | a file vs an entity-inside-a-doc; unrelated despite the shared word |
| `uacp.lessons` — the RESOLVE **lessons artifact** (`resolutions/{run_id}-lessons.yaml`) | the **lessons corpus** (`.uacp/lessons/<id>.md`) **and** the `lesson` node-item | three different things sharing "lesson(s)": a transition doc, a corpus dir, a corpus node |
| `uacp.proposal_package_selection` — the real PROPOSE document | `uacp.proposal` — **spike-fictional / legacy** | the kernel uses the package-selection envelope; bare `uacp.proposal` is not a live file |
| `uacp.plan_package_selection` + `uacp.scope` + PIV contract — the **three** real PLAN docs | `uacp.plan` — **spike-fictional** | PLAN produces three coexisting documents, not one `uacp.plan` |
| **node-item** (entity inside a doc) | **document kind** (whole file) | only document kinds have an on-disk `kind:` + are validated as files |
| **Manifest engine** (document owner) | "state engine" | reserve "state engine" for `uacp-state` lifecycle |

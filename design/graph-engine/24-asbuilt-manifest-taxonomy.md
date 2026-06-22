---
type: analysis
title: Graph Engine — AS-BUILT Manifest Taxonomy & Schema-Authority Map (comprehend-before-serialize)
description: A grounded audit of what the UACP control plane ACTUALLY contains today — every artifact kind, where it lives, who writes it, who validates it — across the governance/state/knowledge/config planes. Establishes the taxonomy the schema layer must serialize FROM, and corrects the spike-shaped assumptions that 3b/D40 were built on.
tags: [graph-engine, taxonomy, manifest, schema, as-built, audit, control-plane]
timestamp: 2026-06-21
edges:
  - {dst: 16a-control-plane-schema, rel: corrects, provenance: asserted}
  - {dst: 11-node-taxonomy, rel: grounds, provenance: asserted}
  - {dst: 16-schema-registry, rel: corrects, provenance: asserted}
---

# AS-BUILT Manifest Taxonomy & Schema-Authority Map

## Why this node exists

The schema work (Slice 1b inc 3a/3b) defined `kind → JSON-Schema` entries **before** the
real taxonomy of the manifest was established — it serialized off the graph-engine *spike
fixtures* (`spike/fixtures/oauth-login/`), not off what UACP actually writes. The result:
3 of 3b's 5 document kinds (`uacp.proposal`/`plan`/`execution`) **do not exist anywhere in
the system** except the schema entries that invented them. This inverted the core principle
(comprehend → measure → serialize): you cannot define a schema for a taxonomy you have not
comprehended. This node is the missing **comprehend** step — a grounded map of the as-built
control plane, so the schema layer has something real to serialize from.

> Grounding legend: **[V]** = verified directly in this session (file:line quoted);
> **[A]** = grounded by a read-only sub-agent investigation (file:line cited, not all
> re-verified here); **[?]** = open / not yet grounded.

## Headline: schema authority is scattered across FOUR code locations (+ grammar + config)

D40 / [16a-control-plane-schema](16a-control-plane-schema.md) framed the unification as
"migrate `artifact_schema.py` + fold the OKF lint" — **two** authorities. The audit found
**four** code-level authorities, and the one D40 never names is the largest and the only one
the kernel actually invokes at gate time:

| # | Authority | What it owns | Wired into kernel? |
|---|---|---|---|
| 1 | **`scripts/validate_uacp_artifacts.py`** (97 KB, **27** `validate_*` fns) | The deep field-semantics of EVERY lifecycle artifact (triage, the package-selections, PIV contract, checkpoint, assessment, verify/resolve packages, closure, council, phase_transition, the config kinds) | **YES** — `core.py:1862` loads it via `importlib` and runs `validate_configs` + the per-kind validators at transition time. **[V]** core.py:1855-1880 docstring: *"the offline validator owns the deeper artifact semantics… catches the real semantic false-pass."* Its own docstring still says *"intentionally not a full schema engine… for manual drills"* — but it is wired. |
| 2 | **`engines/domain/artifact_schema.py`** (Pydantic) | 4 transition artifacts — `intent`/`scope`/`lessons`/`evidence_disposition` — + `BlastRadius` enum + `run_registry`, surfaced via `artifact_schemas_dict()` | YES — `core.py:780` → `self.artifact_schemas` → 4 Heartgate readers; `scope_conformance.py:117` for `BlastRadius`. **[V]** |
| 3 | **`engines/domain/schema.py`** (JSON-Schema, 3a/3b) | 5 node-item kinds (real, composable) + 5 document kinds (**3 fictional** — see below) | **NO** — nothing calls the document validators yet (3f would). **[V]** bare `uacp.proposal/plan/execution` occur ONLY here (grep: schema.py:166-217). |
| 4 | **`engines/domain/corpus.py`** | Knowledge plane — `Lesson` + `KnowledgeItem` models | YES — via the Oracle (`corpus_io`/`corpus_writer`). **[A]** |

Plus: **codified grammar** in `engines/domain/` (`phase_transitions.py`, `gate_rules.py`,
`evidence_cluster.py`, `pointer.py`, `ledger.py`, `escalation.py`) and **config doctrine**
(the `*_config` YAMLs). Any honest "one registry" must subsume #1 — it is the de-facto
canonical artifact validator.

## Plane 1 — Governance manifest (the run lifecycle)

The kernel uses an **adaptive "package-selection" envelope model**, NOT the spike's clean
`proposal/plan/execution` documents. Per phase (kinds **[V]** at the cited core.py gate lines;
locations/shapes **[A]**):

| Phase | Real artifact kind(s) | Location | Validator |
|---|---|---|---|
| BRAINSTORM | brainstorm scope-package | `brainstorm/{id}/07-scope-package.yaml` | phase_exit_invariant glob |
| TRIAGE | `uacp.triage` | `proposals/{run_id}-triage*.yaml` | `validate_triage` |
| PROPOSE | `uacp.proposal_package_selection` (+ a `proposals/{run_id}/` module dir) | `proposals/{run_id}-package-selection.yaml` | gate **[V]** core.py:1297; `validate_proposal_package_selection` |
| PLAN | `uacp.plan_package_selection` **+** `uacp.scope` **+** `uacp.phase_intent_verification_contract` | `plans/{run_id}-plan-selection.yaml`, `-scope.yaml`, `-piv.yaml` | gate **[V]** core.py:1756, 1950; `validate_plan_package_selection`/`validate_piv_contract` |
| EXECUTE | `uacp.execution_checkpoint` (1 per work unit) | `executions/{run_id}-checkpoint-NNN.yaml` | gate **[V]** core.py:1956; `validate_execution_checkpoint` |
| VERIFY | `uacp.piv_assessment` **+** `uacp.verification_package` **+** `uacp.verify_resolve_readiness` (+ `uacp.evidence_disposition` markdown pair) | `verification/{run_id}-*.yaml` / `-{cluster}-*.md` | gate **[V]** core.py:2100, 2106; `validate_piv_assessment`/`validate_verify_package_selection`/`validate_verify_resolve_readiness` |
| RESOLVE | `uacp.resolve_package` **+** `uacp.resolve_closure` (+ `uacp.lessons` → Oracle) | `resolutions/{run_id}-resolve-selection.yaml`, `-closure.yaml` | gate **[V]** core.py:2140, 2148; `validate_resolve_package_selection`/`validate_resolve_closure` |
| (boundary) | `uacp.phase_transition`; optional `uacp.council_synthesis` | `state/runs/{run_id}-transition-*.yaml` | `validate_phase_transition`/`validate_council_synthesis` |

**Key relationships (resolved):**
- The **`*_package_selection`** envelope is an *adaptive coverage record* ("which universal-core
  concerns are covered / which modules selected / where the proof lives"), not the substantive
  doc — substance lives in the module dir + referenced markdown. The kernel's PROPOSE/PLAN gates
  require the *package_selection*, never a bare `uacp.proposal`/`uacp.plan`. **[V]**
- **PLAN emits three** distinct artifacts: `scope` = the write-boundary/containment contract
  (Guardian); `phase_intent_verification_contract` (PIV) = work_units + evidence_obligations +
  checkpoint policy + VERIFY handoff; `plan_package_selection` = the adaptive envelope. They
  coexist. **[A]**
- **RESOLVE has package + closure** (`resolve_package` = selection/decision; `resolve_closure` =
  terminal closure record with state disposition). `uacp.lessons` is the Oracle corpus OKF, a
  *separate* knowledge-plane write, not the closure doc. `uacp.resolution` is a label, not a kind.

## Plane 2 — State (how a run's documents are tied together)

- **`RunManifest`** (`state_machine.py:92`) is the run spine. Its **`artifacts: dict[str, str]`**
  maps `artifact_type → base-relative path` (e.g. `{"scope": "plans/r1-scope.yaml"}`). **[A]**
- Populated at **runtime** by `handle_register_artifact` (`state_machine.py:361-399`, path-contained,
  fail-closed) — not test-only. **[A]** (This is exactly the map `graph_projection` reads.)
- `inherited_artifacts` (goal-driven track) = reused triage/proposal/plan paths from a parent run,
  kept separate for provenance. Stored at `.uacp/state/runs/{run_id}.yaml`. **[A]**
- Sibling state: `uacp.run_registry` (`state/run-registry.yaml` — active-run + write-path overlap +
  goal chaining), `current.yaml` pointer (`CurrentPointer`, 8 required fields), and the goal-driven
  **checkpoint manifest** (gate-ledger `CHECKPOINT` records, `CheckpointEntry`). **[A]**

## Plane 3 — Knowledge (as-built ≠ designed)

- **As-built** (`corpus.py`): two models only — `Lesson` (id/title/project/domains/invariants/
  affected_paths/severity/source_run/extracted_at/eligible/recurrences/**bes**/promoted_to/tags/body)
  and `KnowledgeItem` (type ∈ {pattern,digest,analysis,contract}/id/title/description/tags/domains/
  scope/derived_from/timestamp/body). Stored flat: **`.uacp/lessons/`** + **`.uacp/knowledge/`**. **[A]**
- **On-disk inconsistency:** `.uacp/knowledge/*.md` use OKF `type:` (no `kind:`); one `.uacp/lessons/*.yaml`
  uses `kind: uacp.lesson` with an *array* shape; two `.uacp/lessons/*.md` are plain prose (no frontmatter).
  Identity is filename-derived, not a frontmatter `id`. **[A]**
- **Designed** ([22-context-loop](22-context-loop.md), D30): a richer tiered topology — TYPES
  `observation`/`fact`/`lesson`/`procedure`; TIERS `episode→pattern→rule` (via `promoted_to`); nested
  under **`.uacp/knowledge/{facts,lessons,patterns,rules}/`** + run-local `executions/{run_id}/observations/`.
  **Not built.** [11-node-taxonomy](11-node-taxonomy.md) lists only `lesson` + `knowledge_item` — i.e. the
  two design nodes (11 vs 22) are themselves unreconciled. **[A]**
- **Location divergence:** design nests lessons UNDER `knowledge/`; as-built has a separate top-level
  `.uacp/lessons/`. (This is what surfaced the "`.uacp/lessons` vs `.uacp/knowledge`" question.)

## Plane 4 — Config / doctrine

`config/uacp.toml` (`[paths]` topology + all operator knobs, fully active) + the doctrine/grammar YAMLs:
`state.yaml` (`uacp.state_config`, doctrine-only), `phase-transitions.yaml` (`uacp.phase_transition_config`,
mixed: grammar codified to `engines/domain/`, doctrine retained), `gate-selection.yaml`
(`uacp.gate_selection_config`), `review-routing.yaml` (`uacp.review_routing_config`),
`evidence-clusters.yaml` (`uacp.evidence_cluster_registry` + `uacp.evidence_cluster`). **[A]**
`[paths]`: base=`.uacp`, state, proposals, plans, executions, verification, resolutions, knowledge,
lessons (+ `bridges/`, `councils/`). **[V]** (uacp.toml).

## The validator layer — and the `uacp-lint` / `uacp-fmt` relationship

`scripts/validate_uacp_artifacts.py` is a **monolith**: one file (not a package, not per-doc
scripts), 27 `validate_<kind>` functions, dispatched by an `if/elif kind == …` chain in `main()`
(lines 1587-1617); the kernel imports the module and calls the functions in-process **[V]**. Each
function is **hybrid** — single-doc **shape** *plus* cross-artifact **referential** semantics.
Example **[V]** (`validate_piv_assessment`, line 1026): shape (`required` fields, `phase=="verify"`,
`state ∈ {pass,warn,block,deferred}`, non-empty `assessments`, `evidence_refs` present, dup-id) **and**
referential — it `_load_piv_contract(...)` and rejects any `obligation_id` not present in the
referenced contract's `evidence_obligations`. That second half loads a *sibling document* — which
JSON-Schema cannot express.

This fixes the relationship between the schema registry and the designed `uacp-lint`/`uacp-fmt`
(D8 / [13-writer-contract](13-writer-contract.md)). They are **not three things to build** — they
are one source + two consumers, with the validator already mostly written (per D41):

| Piece | Is | Built? |
|---|---|---|
| `schema.py` (uacp-schema) | the single **declarative SHAPE** source (per-kind dictionary) | partial (3a real; 3b reverted) |
| `uacp-lint` | the **transformed `validate_uacp_artifacts.py`** — shape *delegated to `schema.py`* + cross-artifact referential checks kept imperative; the kernel already imports the engine (D8 library door) | exists as the monolith; needs the shape-delegation refactor |
| `uacp-fmt` | the net-new **formatter** sibling (canonical form; never rejects); one skill / two subcommands over `schema.py` (D8) | not built |
| `graph_projection` | cross-**NODE** closure (orphan/phantom/uncovered) — separate | built (Phase A) |

Boundary refinements (D41): `uacp-lint` widens from "node-local only" (13/D8) to "per-artifact incl.
referential integrity"; cross-NODE topology stays in `graph_projection`. Gate timing: shape at
write-time (Guardian) **and** transition-time (Heartgate); referential only at transition-time (the
referenced siblings must exist). `validate_uacp_artifacts.py` is invoked today by **Heartgate at the
transition gate** (core.py:1862), not by Guardian at write-time — so write-time shape-lint via the
same `schema.py` source is net-new, the transition-time validator is the existing engine. **[V]**

## Implications (what this corrects)

1. **D40 undercounts the authorities.** The real unification target is dominated by
   `validate_uacp_artifacts.py` (#1) — kernel-wired, 27 validators — which D40/16a never name. Any
   "one registry, one paradigm" plan must account for it, not just `artifact_schema.py` + the OKF lint.
2. **3b is mostly fictional.** `uacp.proposal`/`uacp.plan`/`uacp.execution` exist only as the schema
   entries that invented them; the real PROPOSE/PLAN/EXECUTE artifacts are the package-selection
   envelopes + scope + PIV contract + checkpoint. Only `uacp.piv_assessment` and `uacp.lessons` are
   real-ish — and even those have **richer real shapes** than 3b's simplified schemas
   (e.g. real `piv_assessment` = `piv_contract` ref + assessments with `state ∈ {pass,warn,block,deferred}`
   + `overall_status`, not `{assessments:[{obligation_id,evidence_refs,result}]}`).
3. **The spike model is an aspiration, not the manifest.** The clean `scope_item → work_unit
   (derives_from) → obligation → checkpoint → assessment` chain (Phase A / graph_projection) is a
   *designed* canonical form. The kernel's lived model is the package-selection envelopes. **Reconciling
   "spike clean-break model vs kernel package model" is a prerequisite design decision** that 3b/3c
   silently assumed away.

## Open questions for the next decision (not resolved here)

- Does the graph-engine intend to **replace** the package-selection model with the clean
  `proposal/plan/execution` model (a real clean-break migration of the kernel + `validate_uacp_artifacts.py`),
  or to **schematize what exists**? These are very different programs.
- Should the one registry **subsume** `validate_uacp_artifacts.py` (port 27 field-validators to JSON-Schema)
  or **wrap/coexist** with it? D40 must be amended either way.
- Knowledge plane: build the D30 tiered topology now, or schematize the as-built `Lesson`/`KnowledgeItem`
  first? And reconcile the `.uacp/lessons` vs `.uacp/knowledge/lessons` location.
- Fate of the committed 3b (`ad79b22`): revert (it encodes invented kinds) vs keep-parked.

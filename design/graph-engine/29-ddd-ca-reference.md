---
type: reference
title: UACP Modular Architecture — DDD + Clean-Architecture Reference
description: The reference for HOW to modularize UACP's engines/modules/components — bounded contexts (DDD), the dependency-rule rings (Clean Architecture), litmus rules for "is this a module?", and where the current code violates them. Not textbook-exact; applied to the real code. The companion to the artifact graph — a graph for our MODULES.
tags: [uacp, architecture, ddd, clean-architecture, modularization, reference]
timestamp: 2026-06-22
edges:
  - {dst: 28-component-registry, rel: depends_on, provenance: asserted}
  - {dst: 30-current-state-decomposition, rel: relates_to, provenance: asserted}
  - {dst: 31-target-module-graph, rel: relates_to, provenance: asserted}
---

# Modular Architecture — DDD + Clean-Architecture Reference

> Why this exists: the kernel keeps getting smashed into giant files (`core.py` is **3,178
> lines**; `Heartgate` alone is **~2,400**). We have a graph for *artifacts* but none for our
> *modules*. This is the reference for deciding what is a module, which ring it lives in, and
> how dependencies may point — so new skills/scripts can't re-smash everything.

## Bounded contexts (DDD — the WHAT)

Each context has its own ubiquitous language, aggregate root, and repository. Today several **bleed** into `core.py`.

| Bounded context | Ubiquitous language | Aggregate root | Repository (persistence) | Current home |
|---|---|---|---|---|
| **Run lifecycle / state** | phase, status, transition, registry, pointer | `RunState` (today `RunManifest`) | files under `state/` | `uacp-state` ✅ isolated |
| **Manifest documents** | scope_item, work_unit, obligation, checkpoint, assessment | the phase documents (proposal/plan/…) | files under proposals/plans/… via Governed writers | **smeared** (no owner → Manifest engine, D43) |
| **Governance / policy** | decision, category, containment, authority | `GuardianPolicy` | config `[guardian]` | `core.py:138-677` ✅ cohesive but co-located |
| **Transition gating** | gate, blocker, invariant, evidence_cluster | `Heartgate` (per-run) | config + engines | `core.py:786-3178` ✗ god-object |
| **Knowledge** | lesson, knowledge_item, tier, retrieval | the corpus | `.uacp/{lessons,knowledge}/` | `engines/oracle/` ✅ isolated (boundary-tested) |
| **Config / doctrine** | knob, path, rule, threshold | `UacpConfig` | `config/*.{toml,yaml}` | `config.py` ✅ isolated |
| **Code plane** *(future)* | symbol, anchor, reference | (SCIP graph) | (per-commit index) | not built |

**Where contexts bleed (the problem):** `Heartgate` (transition-gating context) reaches into the **manifest-documents** context (it inline-validates intent/scope/evidence/lessons docs), the **state** context (it reads run manifests + the gate ledger + the run registry), and the **config** context (4+ inline `get_config` reads). One class, four contexts.

## The rings (Clean Architecture — the dependency rule)

Dependencies point **inward only**: Framework → Adapter → Application → Domain. Domain imports nothing but stdlib.

| Ring | Role | Modules (target) |
|---|---|---|
| **Domain** (pure; stdlib / pydantic / jsonschema only — the sink) | rules, schemas, enums, pure computation | `engines/domain/*` (schema, layout, gate_rules, phase_graph, artifact_schema, scope, checkpoint, budget, registry, pointer, ledger, escalation, corpus, evidence_cluster, …), `oracle/tier_config` |
| **Application** (use-cases; orchestrate domain, read via IO) | the engines that DO things | **Guardian**, **Heartgate**, the **validation engines** (graph_projection, scope_conformance, evidence_completeness, deferral_completeness, coherence, artifact_integrity, ledger_integrity), the **Manifest engine** (NEW), the **State engine** (`uacp-state`), the **Oracle** |
| **Adapter** (I/O + glue) | translate between app and the outside | `config.py`, `engines/io/loaders`, **Governed writers** (`governed_handlers.py` — the FS write primitive), `contracts.py`, `tool_specs.py`, `hook_kernel.py` |
| **Infrastructure / framework** (outermost; runtime-specific) | the runtimes + low-level FS | `runtime-adapters/{hermes,mcp,hooks}`, `filesystem.py` |

*(Resolves a lens disagreement: the **gates and validation engines are APPLICATION** — they orchestrate domain rules and read via IO; the pure rules they apply are domain leaves. Guardian/Heartgate are use-cases invoked BY adapters, not adapters themselves.)*

**Dependency-rule violations today:**
- **`core.py` straddles three rings in one file** — Guardian + Heartgate (application) + inline domain rules + inline IO. A 3,178-line module cannot honor the dependency rule.
- **Lazy imports = latent cycles** — `Heartgate` lazy-imports `engines.*` / `state.*` inside ~10 methods (core.py:780, 807, 835, 976, 1138, 1238, 1253, 1299, 1356, …) specifically to dodge top-level circular imports. No runtime cycle, but the coupling is real; the fix is dependency injection (pass the engine dispatcher / config / loaders into `Heartgate.__init__`), not lazy imports.
- **Validation engines import `core.resolve_uacp_root`** — a leaf-level helper sitting in an application module; should move to `engines/domain/paths.py` so engines import inward only.

## Litmus rules (when is something its own module?)

- **Standalone ENGINE (application component)** — it (a) is invoked from ≥2 places, OR (b) is a gating decision (allow/block), OR (c) has multiple internal steps worth composing. Read-only ⇒ a *validation engine* (register in `engines/base.py::ENGINES`); mutating ⇒ a use-case owner (Manifest/State engine).
- **DOMAIN LEAF** — pure rules/schemas/enums, no I/O, importable by anything. Imports stdlib only. If it imports another non-leaf, it isn't a leaf.
- **GATE** — a block/allow decision at a boundary (Guardian = write-time, Heartgate = transition). Gates *orchestrate*; they must not *contain* the validators (those are engines/leaves they call).
- **ADAPTER** — translates to the outside (I/O, a runtime, a registry). Never holds business rules.
- **SPLIT a module when** it (a) imports from ≥2 rings, OR (b) exceeds ~600 lines with ≥3 responsibilities, OR (c) holds logic that *should* be independently testable but is only reachable through the parent. All three apply to `core.py`.
- **Do NOT modularize** single-use helpers, framework wrappers (those are adapters/hooks, not engines), or anything that would split a single cohesive concept (over-shatter is as bad as smashing).

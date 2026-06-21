---
type: reference
title: UACP Component Registry — the six component kinds (canonical, as-built)
description: The single authoritative taxonomy of UACP components by KIND — Engine / Gate / Check / Leaf / Skill / Adapter — grounded in the real code. The load-bearing rule: only the 3 engines (State, Manifest, Oracle) touch the file system or LanceDB; everything else goes through them. Resolves the overloaded word "engine". Read before naming or placing any component; nothing else is canonical for component kinds.
tags: [uacp, components, engines, gates, kinds, nomenclature, reference, drift-guard]
timestamp: 2026-06-22
edges:
  - {dst: 26-nomenclature, rel: relates_to, provenance: asserted}
  - {dst: 29-ddd-ca-reference, rel: relates_to, provenance: asserted}
  - {dst: 18-glossary, rel: supersedes, provenance: asserted}
---

# UACP Component Registry — the six component kinds (canonical, as-built)

> Authoritative for **component kinds + names**, grounded in the real package/script (not design
> aspiration). [26-nomenclature](26-nomenclature.md) = artifact kinds; [27-directory-taxonomy](27-directory-taxonomy.md)
> = file layout; [29-31] = the modular architecture this realizes. Supersedes [18-glossary](18-glossary.md).

## The load-bearing rule: one engine per plane; only engines touch storage

**Each PLANE is owned by exactly ONE storage-owning *engine*, and those engines are the ONLY
components that read or write the file system or LanceDB. Everything else goes *through* them.**
That single chokepoint per plane is what makes governance real (validate-on-write, project-on-read,
unbypassable). The count is **one engine per plane** — three today, a fourth (Code) when the code
plane lands — *not* a fixed three.

> **TARGET vs as-built.** This is the **target** invariant. Today it is NOT fully true — two known
> leaks: **Guardian** (a gate) writes its operational audit log, and **`artifact_hashes`** (a leaf)
> writes the watermark under `state/`. Both are **migration debts** (route the audit + watermark
> through the **State engine** — both belong under `state/`) or an accepted named exception
> (operational audit = telemetry, not governed data). The **path-boundary lint (Phase D)** is what
> makes this invariant real; until it lands, treat this as the goal, not the state.

### Engine ↔ plane boundaries

| Plane | Engine | OWNS (storage + responsibility) | Does NOT own | Seam |
|---|---|---|---|---|
| **Run-state** | **State engine** (`uacp-state`) | `state/`: RunManifest (phase/status), run-registry, current pointer, gate ledger, escalations, **+ the artifact INDEX** `{type→path}` | document *content*; embeddings; policy | Manifest engine **registers** doc paths into State's index → State knows *that*+*where*, not *what* |
| **Manifest** | **Manifest engine** (D43, building) | the documents (`proposals/`…`resolutions/`) **+ their in-memory structural graph** | lifecycle phase/status (State); embeddings (Oracle); gate *decisions* (Heartgate) | write → registers path in State; provenance edges **out** to Oracle (`derived_from`) + Code (`code_anchor`); Heartgate invokes its projection as a Check |
| **Knowledge** | **Oracle engine** | `.uacp/{lessons,knowledge}/` + **LanceDB**: corpus + semantic index (build = embed/upsert; query = semantic + keyword + rerank) | run-state; manifest *structure* (manifest **never embedded**) | knowledge `derived_from` manifest nodes (edge **in**); semantic entry → cross into the manifest graph at query time |
| **Code** *(future, 4th)* | **Code engine** | the symbol/ref index: **SCIP** (persistent, per-commit) + **LSP** (live) | manifest / knowledge / state | manifest `code_anchor` → symbol |

**Indexing is each engine's own build+query capability, NOT a separate engine** (D44): the
query/read side is **read-only over truth** everywhere; the *build* side is a persisted write only
where the plane needs one (Oracle / Code) and **in-memory** for the manifest (D29). Caching is
allowed but **derived + rebuildable + engine-owned + never authoritative + deferred** (D44).

**An engine is invoked, not driving.** Like a car engine: it runs when the driver presses the
pedal — it doesn't choose the destination. The *drivers* are the Skills (below); the engine
executes the governed I/O when called.

## The six component kinds

| Kind | What it is | Touches storage? | Invoked or drives | Members |
|---|---|---|---|---|
| **Engine** | owns one domain's persistence (a repository) | **YES — the only ones** | invoked | **State · Manifest · Oracle** |
| **Gate** | allow/block enforcement at a boundary | no (reads via engines) | invoked at a boundary | **Guardian** (write-time) · **Heartgate** (transition) |
| **Check** | a read-only integrity test a gate runs | no (pure, over loaded data) | invoked by a gate | graph_projection · scope_conformance · evidence_completeness · deferral_completeness · coherence · artifact_integrity · ledger_integrity |
| **Leaf** | a pure domain rule / schema | no | used by all | schema · layout · gate_rules · phase_graph · artifact_schema · scope · checkpoint · budget · registry · pointer · ledger · escalation · corpus · evidence_cluster · deferral · artifact_hashes · phase_transitions |
| **Skill** | the **driver** — runs a lifecycle phase, *calls* engines + *triggers* gates | no (calls engines) | **DRIVES** | uacp-brainstorm · triage · propose · plan · execute · verify · resolve (+ orchestration: council · debate · parallel · bridge; + surface: uacp · uacp-skills · uacp-context · uacp-web) |
| **Adapter** | the raw outside mechanism an engine/gate wraps | the raw mechanism | edge | Governed-writer FS primitive · io/loaders · config · contracts · tool_specs · hook_kernel · runtime-adapters · filesystem |

## Per-kind detail

### Engines — the 3 repositories (table above)
- **The Manifest engine is a *door*, not a bag.** It **uses** the `layout` + `schema` leaves, **applies** the `uacp-lint` + `uacp-fmt` tools, **wraps** the Governed-writer adapter, **registers** doc paths into the State engine's index, and serves a **read side** (load + `graph_projection`). It does NOT *contain* those modules as its identity — it composes them behind the single door.

### Gates
| Gate | When | What it does | Script |
|---|---|---|---|
| **Guardian** | write-time (pre-tool) | tool/path classification, containment, policy → allow/block raw writes to governed paths | `core.py` (`class Guardian`, `GuardianPolicy`) |
| **Heartgate** | phase transition | runs the Checks + phase-exit invariants → emits block/pass | `core.py` (`class Heartgate`) |

### Checks — read-only, run by the Heartgate gate
`graph_projection` (structural graph) · `scope_conformance` · `evidence_completeness` · `deferral_completeness` · `coherence` · `artifact_integrity` · `ledger_integrity` — registered in `engines/base.py::ENGINES`.
> **Legacy misnomer:** the code dir is `engines/` and the registry is `ENGINES`, but conceptually these are **Checks**, not engines (they own no storage; a gate runs them). The dir name predates this taxonomy; rename is a later cleanup, not a blocker.
> **`graph_projection` ownership (one owner, one invoker):** it is the **Manifest engine's read-side projection** *exposed as* a Check — the Manifest engine hosts the implementation; Heartgate invokes it. Not double-owned (D44).

### Leaves — pure rules, the dependency sink — `engines/domain/*.py`.

### Skills — the drivers — the 7 lifecycle phase skills + orchestration (council/debate/parallel/bridge) + the router/surface skills. They DRIVE the work and call the engines; they hold no kernel logic.
- **`uacp-lint` / `uacp-fmt`** = a *tool* **Skill** (the CLI surface) over a **Leaf** (the rules in `schema.py`), per D8 — one skill, two subcommands. The **Manifest engine *applies* the leaf rules** on write; humans/CI *run* the skill. (So lint/fmt straddle Skill+Leaf, not a new kind.)

### Adapters — the Governed writers (`governed_handlers.py` + `tool_specs.py`), `io/loaders.py`, `config.py`, `contracts.py`, `hook_kernel.py`, `runtime-adapters/`, `filesystem.py`.

## DRIFT GUARD — get the KIND right

| ❌ wrong | ✅ right |
|---|---|
| calling `graph_projection` / `scope_conformance` / … "validation **engines**" | they are **Checks** (run by the Heartgate gate). Only State/Manifest/Oracle are engines. |
| Guardian / Heartgate as "engines" | they are **Gates** — they own no storage. |
| Manifest engine as "schema + layout + lint + fmt + projection" (a bag) | it's a **door** that *uses* those leaves/tools. |
| any non-engine reading/writing the FS or LanceDB directly | route it through **State / Manifest / Oracle** — no exceptions. |
| "manifest engine" == "state engine" | distinct engines: State = the *index* of which docs exist; Manifest = the *documents*. |
| "Indexer engine" / "Index port" (D14/D17/D37) | **no such engine** (D44) — indexing is each engine's internal build+query capability; `graph_projection` = a **Check** hosted by the Manifest read-side |
| "uacp-schema" as a package | the `schema` **Leaf** (`engines/domain/schema.py`). |

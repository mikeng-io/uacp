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

## The load-bearing rule: only 3 engines touch storage

**An *engine* owns ONE domain's persistence — and the three engines are the ONLY components that
read or write the file system or LanceDB. Everything else goes *through* them.** That single
chokepoint per domain is what makes governance real (validate-on-write, project-on-read, unbypassable).

| Engine | Owns (its storage) | Script |
|---|---|---|
| **State engine** (`uacp-state`) | run lifecycle **state** + the document **index** — `state/` (RunManifest = phase/status + `artifacts` index, run-registry, current pointer, gate ledger) | `state.py`, `state_machine.py` |
| **Manifest engine** (D43 — being built) | the manifest **documents** — proposals / plans / executions / verification / resolutions | `engines/manifest/` |
| **Oracle engine** | the **knowledge** corpus + vectors — `.uacp/{lessons,knowledge}/` + **LanceDB** | `engines/oracle/*.py` |

An engine is **invoked** (called to read/write its domain); it does **not drive**. Like a car
engine: it runs when the driver presses the pedal — it doesn't choose the destination. The
*drivers* are the Skills (below); the engine executes the governed I/O when called.

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

### Leaves — pure rules, the dependency sink — `engines/domain/*.py`.

### Skills — the drivers — the 7 lifecycle phase skills + orchestration (council/debate/parallel/bridge) + the router/surface skills. They DRIVE the work and call the engines; they hold no kernel logic.

### Adapters — the Governed writers (`governed_handlers.py` + `tool_specs.py`), `io/loaders.py`, `config.py`, `contracts.py`, `hook_kernel.py`, `runtime-adapters/`, `filesystem.py`.

## DRIFT GUARD — get the KIND right

| ❌ wrong | ✅ right |
|---|---|
| calling `graph_projection` / `scope_conformance` / … "validation **engines**" | they are **Checks** (run by the Heartgate gate). Only State/Manifest/Oracle are engines. |
| Guardian / Heartgate as "engines" | they are **Gates** — they own no storage. |
| Manifest engine as "schema + layout + lint + fmt + projection" (a bag) | it's a **door** that *uses* those leaves/tools. |
| any non-engine reading/writing the FS or LanceDB directly | route it through **State / Manifest / Oracle** — no exceptions. |
| "manifest engine" == "state engine" | distinct engines: State = the *index* of which docs exist; Manifest = the *documents*. |
| "indexer engine" / "the projection engine" | `graph_projection` = a **Check**. |
| "uacp-schema" as a package | the `schema` **Leaf** (`engines/domain/schema.py`). |

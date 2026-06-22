---
type: contract
title: The Manifest Engine — engines/manifest/ (the document plane's write-model + read-side)
description: >-
  Specs engines/manifest/ — the cohesive home (D43) for the manifest-document plane: a door
  (manifest.py) composing the read-side (projection.py, where graph_projection moves) + the
  document validators (the 4 that move out of the Heartgate hub, rewired to the io Loaded[T]
  contract) + the write-side (entity_writer.py, node 35) wrapping the Governed writers. D44: no
  separate Indexer — the Manifest engine owns the manifest read+write. Most pieces already exist;
  this node gives them a home + the door API + the move plan.
tags: [uacp, graph-engine, manifest-engine, projection, CQRS, decomposition, D43, D44]
timestamp: 2026-06-23
edges:
  - {dst: 02-decisions, rel: depends_on, provenance: asserted}        # D43 (Manifest engine) + D44 (Indexer dissolves)
  - {dst: 31-target-module-graph, rel: realizes, provenance: asserted}
  - {dst: 28-component-registry, rel: depends_on, provenance: asserted}
  - {dst: 33-schema-reconciliation, rel: depends_on, provenance: asserted}
  - {dst: 35-entity-writer, rel: relates_to, provenance: asserted}
---

# The Manifest Engine — `engines/manifest/`

> **Why this node.** D43 decided a dedicated Manifest engine; node 31's target tree lists
> `engines/manifest/{manifest,projection,entity_writer,governed_writers}.py`; D44 dissolved the
> standalone Indexer into each engine's read-side. But **no file exists** and nothing specs the
> package. This node is Phase C's build contract: what the engine OWNS, what MOVES in (behaviour-
> preserving, like the A3 carves), what it REUSES, and its door API. The write-side detail
> (entity-writer + validate-on-write) is node 35.

## 1. What the Manifest engine IS (and is not)

The **write-model + read-side for the manifest-document plane** — the application-ring component that
OWNS the lifecycle documents (intent / scope / proposal+plan package-selections / PIV / checkpoint /
assessment / verification / resolve / lessons). It is a **door** (node 32 §1): the single cohesive
public API over pieces that mostly already exist but are smeared across the kernel.

- It is **CQRS-shaped**: a **read-side** (project + validate documents) and a **write-side** (the
  entity-writer, node 35). Per D44 there is **no separate Indexer** — the read-side index (the
  in-memory projection) is the Manifest engine's own internal capability (D29: in-memory recompute;
  a persistent cache is a deferred scale-trigger).
- It is **not** a storage engine in the LanceDB/SCIP sense — manifests are files (truth); it reads
  them via the io adapter and never embeds them (D19/D29).
- Dependency ring (node 29/31): application engine → imports `engines.domain.*` (layout, schema),
  `engines.io` (loaders), and the Guardian gate on write. Imports no outer ring.

## 2. Package layout (node 31's target tree, specced)

```
engines/manifest/
  __init__.py        # the public door: re-export the API + __all__ (node 32 §1/§3)
  manifest.py        # the door class/façade — composes the pieces below into one API
  projection.py      # the READ-side: graph_projection MOVES here (pure move, like A3)
  entity_writer.py   # the WRITE-side: create_<entity>/edit/supersede (node 35)
  governed_writers.py# the low-level Guardian-gated FS write primitive, MOVED from the kernel root
  validators.py      # the 4 document validators MOVED out of the Heartgate hub (read-time checks)
```

(Plus `uacp-lint` / `uacp-fmt` as siblings the door calls — node 33 / node 35; they may live here or
as a standalone skill+leaf per D8/D10, decided there, not here.)

## 3. What MOVES in (behaviour-preserving carves — the A3 pattern)

Each is a relocation of existing, tested code (same AST-identity + suite-green discipline as A3.0–A3.6):

1. **`graph_projection.py` → `projection.py`.** The projection engine (node/edge model, GP_* checks,
   `validate_graph_projection` + `validate_graph_invariants`) moves in. It STAYS a registered Check
   (node 28: it's a Check, not an engine — `ENGINES` registration + the Heartgate closure/phase-exit
   call sites are unchanged via re-export). D42 re-grounding (read the real package artifacts, not
   spike fixtures) happens here, gated by node 33's schemas. **Concrete instance (Kimi-verified):**
   `graph_projection.py:97` reads `doc.get("checkpoints")` — a spike doc-level list — but a REAL
   `execution_checkpoint` is a *single* doc whose evidence is under `evidence` (`validate_uacp_artifacts.py:909`
   required fields), so real checkpoints are currently invisible to the coverage/contradicted checks.
   Re-grounding = map the projection's node/edge extraction onto the real package keys (PIV
   `work_units`/`evidence_obligations`; checkpoint `evidence`+`work_unit_id`; assessment `assessments`+
   `obligation_id`), per the node-33 shapes — not the spike fixture keys.
2. **The 4 Heartgate doc-validators → `validators.py`** (`_validate_intent_doc`,
   `_validate_scope_artifact`, `_validate_evidence_dispositions`, `_validate_lessons_artifact`,
   ~410 lines, the Phase-C item from node 30). Carve like the A3 validators: free functions, thin
   delegating methods left on Heartgate (the orchestrator + tests call them). **REWIRE** them onto the
   io `Loaded[T]` contract — but split by FORMAT (Codex-flagged): `_validate_scope_artifact` +
   `_validate_lessons_artifact` are YAML → `load_artifact` / `load_yaml_under_root` (which return
   `Loaded[Mapping]` and reject non-mappings). `_validate_intent_doc` + `_validate_evidence_dispositions`
   read **markdown** (`intent.md` / the verified-facts/assumptions `.md` pairs) via `path.read_text` +
   heading/table scans — the YAML loaders would reject these (`loaders.py` errors "not a YAML mapping").
   So **add a `load_text_under_root(workspace, rel) -> Loaded[str]`** (containment-checked, never-raises,
   optionally frontmatter-aware) to `engines/io` for the markdown validators. Net: all 4 move onto the
   io contract — 2 via the YAML loaders, 2 via the new text loader — not bare `read_text`.
3. **Governed writers → `governed_writers.py`** (moved from the kernel root, node 31). The low-level
   Guardian-gated FS primitive the entity-writer wraps. Thin re-exports keep `governed_handlers`
   importers working (A1 pattern).

## 4. What it REUSES (no move — the SA-C map's "already exists")

- `engines/io/loaders.py` — the sole disk-touch; the engine's read adapter (`load_manifest`,
  `load_artifact`, `glob_in_workspace`). The `Loaded[T]` contract is the engine's I/O boundary.
- `engines/domain/layout.py` — WHERE a document lives (path convention).
- `engines/domain/schema.py` — the declarative SHAPE source (node 33); the door validates against it.
- the Guardian gate — invoked on write (the `artifact.uacp` category hook, SA-A map).

## 5. The door API (read + write surface)

`manifest.py` composes the pieces into one façade. Indicative surface (names follow node 32 §2):

- **Read-side:** `project(workspace, run_id) -> Graph` (delegates to projection); `validate_document(kind, run_id) -> list[Violation]` (delegates to validators.py + schema.py); the closure/phase-exit Checks remain via the registered `validate_graph_projection`/`validate_graph_invariants`.
- **Write-side (node 35):** `create_<entity>(run_id, fields)` / `edit_<entity>` / `supersede_<entity>` — the entity-writer; the ONLY validated write path.

The door is the **single seam** Heartgate/runtimes call for manifest concerns — replacing today's
smear (hub validators + standalone graph_projection + raw governed writers).

## 6. Boundaries (node 28/29 invariants this must hold)

- Only the engine touches the manifest documents' read+write; other components go through the door.
- Read-side is **query-only** (D22 CQRS leak fix): projection/validators never write or veto; they
  emit Violations the gate consumes. The write-side is the only mutator.
- Files are truth (D29); any index is derived + rebuildable + in-memory (v1). No DB.

## 7. Build sequencing (each step a governed, suite-green increment)

1. Stand up the package skeleton + `__init__` door (empty façade, re-exports).
2. Move `graph_projection → projection.py` (pure move; re-export keeps ENGINES + call sites).
3. Carve the 4 doc-validators → `validators.py` + rewire to io (behaviour-preserving + io-contract).
4. Move governed writers → `governed_writers.py` (re-exports).
5. Build the entity-writer + validate-on-write (node 35) — the genuinely-new part.
6. D42 re-ground projection to the real package artifacts (gated by node 33 schemas).

## To expand
- The exact door class shape + `__all__` (at build, following the guardian/__init__ precedent).
- The projection re-grounding detail (which real package keys feed which node kinds) — node 33 + the validate_uacp_artifacts shapes.
- uacp-lint/uacp-fmt placement (here vs standalone) — D8/D10.

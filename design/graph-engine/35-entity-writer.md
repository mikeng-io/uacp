---
type: contract
title: The Entity-Writer + Validate-on-Write — the only validated manifest write path
description: >-
  Specs engines/manifest/entity_writer.py — the typed write API (create_<entity>/edit/supersede) that
  replaces raw content-blob writes: mint id → resolve layout → serialize OKF → VALIDATE (schema.py +
  uacp-lint) → canonicalize (uacp-fmt) → persist (governed writers) → register (State index) → emit
  typed edges with provenance. Closes the D25 validate-on-write gap (today the Guardian gates
  tool/path/context but NEVER content; uacp_artifact_write writes any blob with only YAML-parse
  validity). The entity-writer is the SINGLE validated path; Guardian blocks raw blob writes to
  manifest paths so it cannot be bypassed.
tags: [uacp, graph-engine, entity-writer, validate-on-write, governed-writers, guardian, D25, D26]
timestamp: 2026-06-23
edges:
  - {dst: 02-decisions, rel: depends_on, provenance: asserted}        # D25 (validate-on-write) + D26 (ids/tombstones)
  - {dst: 34-manifest-engine, rel: depends_on, provenance: asserted}
  - {dst: 33-schema-reconciliation, rel: depends_on, provenance: asserted}
  - {dst: 13-writer-contract, rel: relates_to, provenance: asserted}
---

# The Entity-Writer + Validate-on-Write

> **Why this node.** The SA-A as-built map is blunt: `uacp_artifact_write` takes a raw `content: str`
> blob and the ONLY write-time check is YAML parse-validity + a watermark — **no schema, no required
> fields, no id mint, no edge emission**. The Guardian gates tool/path/context but, by design, never
> reads content (D25). So a structurally-wrong manifest document is written and only caught later (or
> not at all). This is the "real bottleneck" Codex/the lite-council flagged. The entity-writer is the
> fix: the single **typed, validated** write path the Manifest engine (node 34) owns.

## 1. The gap it closes (grounded in SA-A)

| As-built today | What the entity-writer adds |
|---|---|
| `uacp_artifact_write(content: str)` — raw blob | typed `create_<entity>(run_id, fields: dict)` — structured args |
| only `yaml.safe_load` parse-validity (`filesystem._write_uacp_file`) | **validate-on-write**: shape-validate BEFORE persist, branched by format (YAML → `schema.validate`, node 33; markdown → structural validators, §2.4); fail-closed |
| id is whatever the agent put in the blob | **mint** a stable id (D26: ULID, locked, duplicate-id rejected) |
| no frontmatter/edge enforcement | OKF frontmatter + typed `edges:` with **provenance** (D23) emitted |
| no index/graph update | **register** the `{type→path}` entry into the State manifest + feed projection |
| watermark (`record_hash`) post-write, fail-closed | **kept** (the one good wiring that exists) |

## 2. The write pipeline (the contract)

`create_<entity>(run_id, fields)` runs a fixed, deterministic pipeline (fail-closed at every step;
nothing persists unless all pass):

1. **MINT** — allocate a stable id (ULID, D26); reject if it collides with an existing entity (the
   duplicate-id check). Edits/supersedes take an existing id instead.
2. **LAYOUT** — `engines.domain.layout` resolves WHERE this kind lives (path template); no caller path.
3. **SERIALIZE** — render the OKF document: frontmatter (kind, id, the typed `edges:` with
   `rel_type`+`provenance` per D23) + body.
4. **VALIDATE — SHAPE ONLY, BRANCHED BY LAYOUT FORMAT (the net-new gate).** Any violation →
   **reject, no write**. This is the content check the Guardian structurally cannot do.
   - **YAML kinds** → `schema.validate(kind, doc)` (node 33 declarative shape: required fields, types,
     enums, `kind` const).
   - **MARKDOWN kinds** (Codex-flagged) — `uacp.intent`, `uacp.evidence_disposition` are marked
     `MARKDOWN` in `layout.py:79,105` and are NOT JSON-Schema kinds (node 33), so `schema.validate`
     would reject them as unknown. Route these through the **markdown structural validators** (the
     required-section/heading + paired-file checks in node 34's `validators.py`) before persist — the
     write-side mirror of the read-side `load_text_under_root` fix. Every manifest write is validated,
     YAML or markdown — the "single validated manifest write path" invariant holds for both.
   - **NOT the referential layer:** cross-artifact FK / coverage (uacp-lint) needs sibling documents
     that may not exist yet during an INCREMENTAL write, so forcing it here would reject valid partial
     writes or demand placeholder siblings. Referential stays at the **transition gate** (where the
     package is complete) — per node 33 + D41. **Write-time = shape; transition-time = reference.**
5. **FORMAT** — `uacp-fmt` canonicalizes (key order, edge serialization; idempotent) so the on-disk
   form is deterministic + diff-stable.
6. **PERSIST** — call the Governed writers (`governed_writers.py`, node 34) — the Guardian-gated FS
   primitive — to write the file, then `record_hash` (watermark, fail-closed, as today).
7. **REGISTER** — call the State engine to record `{type→path}` in the run manifest's `artifacts`
   (the seam `graph_projection` reads via `load_manifest`), and emit the typed edges into the
   projection/index. (Provenance is serialized HERE — the SA-C map flagged it's not stored today.)
   **ATOMICITY (Codex-flagged):** PERSIST(6)+REGISTER(7) must be **atomic**. A REGISTER failure after
   the file is written (missing run manifest, state-validation error, I/O) would leave a persisted +
   watermarked document that is NOT in the manifest's `artifacts` — invisible to `graph_projection`
   (which only projects registered paths via `load_manifest`), breaking the "nothing persists unless
   all pass" invariant. So on REGISTER failure, **roll back** the persisted file + watermark (the
   governed writer already rolls back on a watermark-write failure, SA-A) — or use a single
   write-then-register operation that the State engine commits transactionally. The invariant must
   hold: either the entity is persisted AND registered, or neither.
   **CROSS-ENGINE BOUNDARY (Kimi-flagged):** the run-manifest is owned by the **State engine**
   (`skills/uacp-state/scripts/state_machine.py`, per `config/state.yaml:12-13`) — a *different*
   skill/engine from the Manifest engine (`uacp-core`). So REGISTER is a cross-engine call into
   `uacp-state`'s registration API, NOT an internal write (D44: each engine owns its own index;
   the Manifest engine must not write State's manifest directly). This seam is design-only today —
   nothing in `uacp-core` registers written manifest paths into State — and is a named build item.

The API surface (node 32 §2): `create_<entity>` / `edit_<entity>` / `supersede_<entity>` (supersede =
tombstone + new version, D18/D26 — tombstones stay visible to closure so a deleted-with-open-obligation
is caught).

## 3. Validate-on-write = unbypassable (D25)

Validation only matters if it can't be sidestepped:

- **Path-scoped category split (Codex-flagged — required).** Today the Guardian `artifact.uacp`
  category (`config/uacp.toml:254-257`) covers BOTH the manifest roots (`plans/ proposals/ executions/
  verification/ resolutions/`) AND non-manifest content (`knowledge/ lessons/ brainstorm/` — Oracle
  corpus + brainstorm), with `allowed_tools=[uacp_artifact_write]`. So you cannot just "make the
  entity-writer the only allowed tool for `artifact.uacp`": replacing it category-wide blocks the
  legitimate non-manifest Oracle/brainstorm writes; leaving `uacp_artifact_write` allowed keeps the
  raw-blob bypass on manifest paths. **Split the category by path:** a new `artifact.manifest`
  (the 5 manifest roots) → `allowed_tools=[<entity-writer>]` ONLY; `artifact.uacp` keeps
  `knowledge/ lessons/ brainstorm/` → `uacp_artifact_write` (raw, not entity-managed — these are
  not lifecycle manifest documents).
- With the split, the entity-writer is the ONLY writer of the manifest roots; raw `Write`/`Edit` to
  them is already hard-blocked (SA-A). Non-manifest content keeps its raw writer, unaffected.
- Net: every **manifest** write goes through validate-on-write; the graph becomes trustworthy because a
  structurally-invalid manifest document cannot be persisted (the D24/D25 "graph not trustworthy until
  raw writes blocked" condition) — without collateral-blocking the knowledge/brainstorm planes.

## 4. Why this is trustless (ties to the verification primitive)

Validate-on-write is the **generative-gate principle at write time** (verification-method node 10):
comprehend the entity's intent (the typed fields) → measure (the schema + referential assertions) →
serialize (persist only the validated, canonical form). Judgment is bounded to authoring the document;
the *check* is deterministic and fail-closed. The author cannot self-attest a malformed manifest into
existence — exactly the no-self-attestation invariant, enforced at the write boundary instead of
(only) the transition gate.

## 5. Build sequencing (after node 34 skeleton + node 33 schemas)

1. `entity_writer.py` skeleton + the pipeline scaffold (mint/layout/serialize/persist/register), no
   validation yet — behaviour-equivalent to today's `uacp_artifact_write` but typed.
2. Wire **validate-on-write** (step 4) for ONE YAML kind first (e.g. scope, via node 33's
   `schema.validate`), prove it rejects a malformed doc (non-vacuous test) — the ratchet; the markdown
   branch (intent/evidence_disposition → structural validators) lands as those kinds migrate.
3. Add the path-scoped **`artifact.manifest`** category wiring (§3) — `allowed_tools=[<entity-writer>]`
   for the 5 manifest roots, leaving `artifact.uacp` = `uacp_artifact_write` for knowledge/lessons/
   brainstorm — so the typed writer is the only writer of manifest paths; make the raw blob path
   internal/validated (close the bypass) WITHOUT blocking the non-manifest planes.
4. Grow per-kind (the node-33 ratchet) until all manifest kinds write through it.
5. Emit typed edges + provenance into the projection (enables D42's real-artifact graph).

## To expand
- The exact typed-field signatures per entity kind (derived from node 33's schemas).
- ULID minting + the duplicate-id/tombstone store (D26) — where the id-registry lives.
- The State-engine registration seam (the `handle_register_artifact` call shape).
- uacp-fmt's canonical form spec (sibling to uacp-lint; D8).

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
| only `yaml.safe_load` parse-validity (`filesystem._write_uacp_file`) | **validate-on-write**: `schema.validate(kind, doc)` (node 33) BEFORE persist; fail-closed |
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
4. **VALIDATE (the net-new gate)** — `schema.validate(kind, doc)` (node 33 declarative shape) **then**
   the uacp-lint referential layer (cross-artifact FK/coverage). Any violation → **reject, no write**.
   This is the content check the Guardian structurally cannot do.
5. **FORMAT** — `uacp-fmt` canonicalizes (key order, edge serialization; idempotent) so the on-disk
   form is deterministic + diff-stable.
6. **PERSIST** — call the Governed writers (`governed_writers.py`, node 34) — the Guardian-gated FS
   primitive — to write the file, then `record_hash` (watermark, fail-closed, as today).
7. **REGISTER** — call the State engine to record `{type→path}` in the run manifest's `artifacts`
   (the seam `graph_projection` reads via `load_manifest`), and emit the typed edges into the
   projection/index. (Provenance is serialized HERE — the SA-C map flagged it's not stored today.)
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

- The entity-writer is the **ONLY** tool in the Guardian `artifact.uacp` category's `allowed_tools`
  for manifest paths. Raw `Write`/`Edit` to a manifest path is already hard-blocked (SA-A: Guardian
  blocks non-`uacp_artifact_write` tools writing to artifact roots).
- The remaining hole — `uacp_artifact_write` itself accepting a raw blob — closes by making the
  **raw blob path the entity-writer's internal primitive**, not an agent-facing tool: the agent calls
  the typed `create_<entity>`; the low-level governed write is internal-only. (Or: keep
  `uacp_artifact_write` but route it through validate-on-write so even the blob path validates.)
- Net: every manifest write goes through validate-on-write. The graph becomes trustworthy because a
  structurally-invalid document cannot be persisted (the D24/D25 "graph not trustworthy until raw
  writes blocked" condition).

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
2. Wire **validate-on-write** (step 4) using node 33's schema.validate for ONE kind (e.g. scope),
   prove it rejects a malformed doc (non-vacuous test) — the ratchet.
3. Add the Guardian `artifact.uacp` wiring so the typed writer is the allowed tool; make the raw blob
   path internal/validated (close the bypass).
4. Grow per-kind (the node-33 ratchet) until all manifest kinds write through it.
5. Emit typed edges + provenance into the projection (enables D42's real-artifact graph).

## To expand
- The exact typed-field signatures per entity kind (derived from node 33's schemas).
- ULID minting + the duplicate-id/tombstone store (D26) — where the id-registry lives.
- The State-engine registration seam (the `handle_register_artifact` call shape).
- uacp-fmt's canonical form spec (sibling to uacp-lint; D8).

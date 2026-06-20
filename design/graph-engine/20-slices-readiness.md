---
type: analysis
title: Graph Engine — Slices & Infra Readiness
description: The incremental build plan (Slice 1/2/3, each a standalone vertical) and the as-is infrastructure readiness map — what is already serialized (~65%), the precedents, and the gaps.
tags: [graph-engine, roadmap, slices, readiness]
timestamp: 2026-06-19
edges:
  - {dst: 02-decisions, rel: sequences, provenance: asserted}
---

# Slices & Infra Readiness

## Slice order (each a standalone vertical; "don't do everything in one trial")

### Slice 1 — granularity + serialization foundation

> **RE-SCOPED by D20 + reframed (final-review T4):** Slice 1 = **manifest schema fix + a read-only
> closure projector** ("Phase A"). The entity writer + Guardian raw-write block + validate-on-write is
> **Phase B** (the real bottleneck), NOT v1. Concretely Phase A = the two keys (`scope_item.id` +
> `work_unit.derives_from` — **clean break, NO shim, per D32**), an **in-memory** projector (~100–200
> lines, globs node files → dicts), the closure checks on **today's** fixtures, derived/optional
> `_index.yaml` (D21), and real validate-on-write (D25). The SQLite/sqlite-vec substrate, the Index
> port, the `uacp-schema`/`uacp-lint`/`uacp-fmt` packages, and the entity re-layout in the bullets below
> are **deferred to Slice 1b+** (extract when real usage demands). The bullets below are the original
> (larger) scope, retained for reference.
- `scope_item.id` + `work_unit.derives_from` — close the one broken seam.
- Entity-per-file OKF layout + `_index.yaml` aggregate for PROPOSE/PLAN/VERIFY (level up to EXECUTE/
  lessons granularity).
- **`uacp-schema`** foundational pure-leaf package (JSON-Schema per node + index kind; enums;
  closed-world `additionalProperties:false`; field descriptions) — the single registry, replacing
  today's scattered/manual/mostly-absent validation (see [02-decisions](02-decisions.md) D9/D10 and
  [16-schema-registry](16-schema-registry.md)).
- **`uacp-lint`** standalone package (fmt + lint subcommands, ruff-style) over a **pure-leaf rules
  module** that the write path also imports (see [02-decisions](02-decisions.md) D8) — generalized
  from the partial `test_okf_frontmatter` seed; node-local well-formedness only (closure stays in the
  projection engine).
- Entity-level engine-mediated writer (`create_work_unit(...)`), with validate-on-write.
- `graph_projection` engine: SQLite node/edge tables + recursive-CTE two-way lookup + the integrity
  report (orphan/phantom/uncovered/unverified/skipped).
- **No code-plane, no constraints.** Proves the whole thesis: run the walker on today's fixtures and
  it auto-flags the PROPOSE→PLAN seam.

> **Validated by spike (2026-06-20):** the read-only in-memory projector + closure checks
> ([spike/findings.md](spike/findings.md)) ran against the real `uacp-governed-lifecycle-dry-run` manifest
> and self-demonstrated the seam (9 uncovered intents, 2 orphan work_units, 0 `derives_from`). Migration
> surface (verified vs **main**): `in_scope` is read only by **presence checks**
> (`validate_uacp_artifacts.py:438`, `phase_transitions.py:183`), not item-structure readers → the
> `scope_item.id` migration is **additive — clean break, NO shim (D32)**: the readers are key-presence
> checks, and the spike **proved** the keyed `in_scope` PASSES the real `validate_proposal`. Council
> Integration F2 **retired**.

### Slice 2 — code / reality plane (the central lookup problem)
- `code_anchor` obligation at EXECUTE; a **SCIP** indexer projecting `code_symbol` nodes +
  `defines`/`references`/`calls` edges (tree-sitter as a cheap change-detector to trigger re-index).
  Enables the full `code → intent` round trip.
- Substrate (bake-off D12 / [17-codeplane-substrate-bakeoff](17-codeplane-substrate-bakeoff.md)):
  **SQLite + recursive CTE** for the code-graph edges (same engine as the manifest plane); **LanceDB**
  for code fuzzy search. No SurrealDB/Kùzu/Cozo (abandoned/immature in 2025-26).
- Elevated from Slice 3 (2026-06-19): trustless evidence shows codespace lookup was the real strain.

### Slice 3 — negative space
- `prohibition` / `method_constraint` / `metric` node kinds; `constrains` / `measured_by` / `violated`
  edges; metric→deterministic EXECUTE/VERIFY check. Builds on Slice 1's node model.

## Infra readiness (as-is, verified in tree)

**Already serialized as typed edges (~65%)**
- `RunManifest.inherits_from`, `.goal_id`, `.inherited_artifacts` (state_machine.py:99-109)
- `work_unit.id`, `obligation_id`, `work_unit_id`, `piv_contract` (validate_uacp_artifacts.py:828-975)
- `Lesson.source_run`, `.promoted_to`, `KnowledgeItem.derived_from` (corpus.py:54,59,118)
- `checkpoint.rolled_back_to` (checkpoint.py:50)

**Precedents that make the engine cheap**
- `engines/oracle/index_build.py` — a working load→project→upsert projection (the deserialize pattern).
- `engines/__init__.py` — 5 self-registering read-only engines; `graph_projection` slots in beside them.
- `tests/unit/skills/test_okf_frontmatter.py` — partial OKF lint (the `uacp-lint`/`uacp-fmt` seed).
- OKF already adopted for the knowledge/reference layer (ADR-0017).

**Gaps to build**
1. `scope_item.id` + `work_unit.derives_from` — the seam (Slice 1).
2. A real edge store/loader — SQLite + recursive CTEs (there is a stubbed `sqlite-vec` in
   `oracle/store.py:171-197` to fill or sidestep).
3. Schema-validation-on-write — `governed_handlers.py:447` writes any YAML; close via the entity-level
   writer + `uacp-lint` (Slice 1).
4. `uacp-fmt` canonical formatter — does not exist (Slice 1).
5. `code_anchor` + symbol indexer — no code indexing exists today (Slice 2; indexer = SCIP, store =
   SQLite, per bake-off D12 / [17-codeplane-substrate-bakeoff](17-codeplane-substrate-bakeoff.md)).

## Governance note

This bundle is **pre-governance design input**. The Slice 1 schema/kernel changes (proposal schema,
new engine, writer promotion) are council-gated kernel/policy changes and must enter through a
governed run (TRIAGE → PROPOSE → council). This bundle becomes that run's source material.

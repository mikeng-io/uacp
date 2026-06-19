---
type: contract
title: Graph Engine — Edge Schema
description: The canonical serialized edge record {src, dst, rel_type, provenance}, the four provenance classes, and the rel_type vocabulary across all three planes.
tags: [graph-engine, edge, schema, provenance, contract]
timestamp: 2026-06-19
edges:
  - {dst: 02-decisions, rel: realizes, provenance: asserted}
---

# Edge Schema (contract)

The unification is **not** a unified engine — it is a **unified edge serialization**. One record,
emitted identically whether the edge is born in a governed artifact, the oracle, or the parser:

```yaml
edge:
  src: <node_id>          # required
  dst: <node_id>          # required
  rel_type: <string>      # required — from the vocabulary below
  provenance: <enum>      # required — derived | parsed | asserted | inferred
```

The reason a "unified graph engine" felt necessary is that edges are today serialized three
incompatible ways (YAML FK fields in state, markdown links in OKF, nothing for code). Unify the
*serialization* and the engine collapses to a loader: `union(edges) -> traverse`.

## Provenance — the trust class (the load-bearing field)

`provenance` records *how the edge was known*. It is what lets one stream carry hard and soft edges
without ever confusing a proof for a guess.

| provenance | source | trust | example |
|---|---|---|---|
| `derived` | a foreign key in a governed artifact | **hard** | `work_unit.derives_from → scope_item` |
| `parsed` | AST / git / LSP | **hard** | `login() calls verifyPassword()` |
| `asserted` | human/LLM committed it *as a key* | **hard once committed** | the PROPOSE→PLAN translation |
| `inferred` | embedding / OKF link / "aboutness" | **soft, advisory** | `lesson-42 relates-to authentication` |

The query layer filters by provenance: *hard-only* = the deterministic plane; *include inferred* =
the knowledge plane. Same engine, one flag.

## rel_type vocabulary

Grouped by plane. All are `derived` unless noted.

**Relation / governance plane**
- `derives_from` — work_unit → scope_item. **provenance: asserted** (the one semantic commitment).
- `obligation_for` — evidence_obligation → work_unit.
- `work_unit_id` — checkpoint → work_unit.
- `evidence_refs` — assessment → checkpoint.
- `obligation_id` — assessment → evidence_obligation.
- `inherits_from` / `inherited_artifacts` — run → parent run (goal-chaining).
- `rolled_back_to` — checkpoint → prior checkpoint.

**Knowledge plane**
- `source_run` — lesson → run.
- `derived_from` — lesson/knowledge → run entities (provenance: derived).
- `relates_to` / `about` — knowledge ↔ knowledge. **provenance: inferred** (advisory only).

**Code / reality plane (Slice 2)**
- `code_anchor` — checkpoint → code_symbol (file+symbol+lines+commit). **provenance: parsed.**
- `calls` / `imports` / `references` — code_symbol → code_symbol. **provenance: parsed.**

**Negative space (Slice 3)**
- `constrains` — prohibition/method_constraint → scope_item/work_unit. **provenance: asserted.**
- `measured_by` — work_unit → metric.
- `violated` — checkpoint/assessment → constraint/metric (emitted when a bound is breached).

## Invariants

1. Every edge's `src` and `dst` MUST resolve to a node that exists (no dangling endpoints) —
   except where the projection deliberately records a **phantom** finding (see
   [14-projection-engine](14-projection-engine.md)).
2. `provenance` is never inferred by the engine — it is serialized by the producer. The engine never
   *upgrades* an `inferred` edge to `derived`.
3. An `asserted` edge is created by judgment **once**, then is as hard as any `derived` edge. The
   engine treats `asserted` and `derived` identically for traversal; they differ only in audit.
4. **(D23)** Provenance is enforced **per `rel_type`** via a closed map in `uacp-schema`
   (`derives_from→asserted`, `relates_to`/`about→inferred`, `calls`/`code_anchor→parsed`, FK rels
   →`derived`). Validation REJECTS any edge whose provenance violates its rel_type's mandated class — so a
   producer cannot forge a guessed `relates_to` as `derived`. Provenance is producer-serialized; the
   schema enforces *vocabulary*, never *truth-of-provenance*.

> **Existence ≠ correctness (D23).** Closure proves *coverage topology* (every node reachable, every
> intent covered), NOT that an `asserted` edge points at the *right* node. A `work_unit` that invents a
> `derives_from` to a real-but-unrelated `scope_item` passes every deterministic gate — that is why a
> change to an `asserted` edge's dst re-triggers **council**, and why `parsed` edges are checked against
> SCIP (`forged-parsed`). Do not over-trust a green closure report as semantic correctness.

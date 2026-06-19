---
type: contract
title: Graph Engine — Node Taxonomy & Identity
description: The node kinds across the three planes, the DDD identity rule (entity test), and which nodes carry stable ids.
tags: [graph-engine, node, taxonomy, identity, ddd, contract]
timestamp: 2026-06-19
edges:
  - {dst: 10-edge-schema, rel: depends_on, provenance: derived}
---

# Node Taxonomy & Identity (contract)

A node is one OKF file: YAML frontmatter (identity + edges) + body (content). The graph is the
deserialization of all nodes and their serialized edges.

## The identity rule (DDD entity test)

> A thing gets a **stable id and its own file** iff it has **identity** and an **independent
> lifecycle** — it can be referenced, and it changes on its own schedule.

This is the cut for granularity (see [02-decisions](02-decisions.md) D3). It rejects both failure
modes: smashing (no id, lives inside a monolith) and over-shatter (fragmenting a single concept that
has no independent lifecycle).

- `work_unit` — has id, changes independently → **own file**.
- a rationale paragraph inside a node body — no independent identity → **stays in the body**.

## Node kinds

| kind | plane | carries id | born in | value in |
|---|---|---|---|---|
| `scope_item` | governance | yes | PROPOSE | body (intent) |
| `work_unit` | governance | yes | PLAN | both |
| `evidence_obligation` | governance | yes | PLAN | frontmatter |
| `checkpoint` | governance | yes | EXECUTE | frontmatter |
| `assessment` | governance | yes | VERIFY | frontmatter |
| `lesson` | knowledge | yes | RESOLVE | body (knowledge) |
| `knowledge_item` | knowledge | yes | (curation) | body |
| `prohibition` | negative (Slice 3) | yes | PROPOSE/PLAN | body (why-not) |
| `method_constraint` | negative (Slice 3) | yes | PLAN | body |
| `metric` | negative (Slice 3) | yes | PROPOSE/PLAN | frontmatter (the bound) |
| `code_symbol` | code (Slice 2) | yes (file+symbol) | parser | n/a (projected) |

## Identity assignment

- ids are minted by the **engine**, not the agent (see [13-writer-contract](13-writer-contract.md)).
- id form follows the existing safe-id convention (`^[A-Za-z0-9._-]{1,128}$`).
- ids are **kind-prefixed and run-scoped** for legibility: `si-1`, `wu-2`, `ev-1`, `cp-1`, `as-1`.
- a `code_symbol` id is its anchor (`auth/oauth.py::oauth_callback`), resolved by the parser, not minted.

## Aggregates

A node never floats alone. Each phase's nodes belong to an **aggregate** = a directory + an
`_index.yaml` that lists members, holds aggregate-level edges, and carries the closure inputs
(e.g. PLAN's `coverage` map). The aggregate — not co-location of bytes — is the consistency boundary,
and the engine enforces its invariants on write.

## The seam this closes

Today `scope_item` has **no id** and `work_unit` has **no `derives_from`** — so the PROPOSE→PLAN edge
cannot exist. Minting `scope_item.id` (this taxonomy) + adding `work_unit.derives_from` (the
[edge schema](10-edge-schema.md)) is the entire fix for the one broken seam. Everything downstream is
already FK-integral.

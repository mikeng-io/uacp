---
type: analysis
title: Graph Engine — Context & Intent
description: Why this exists — the original symptoms, the trustless-ACP flaw, and the "manifests are wiki" reframe that unifies the relation and knowledge planes.
tags: [graph-engine, context, intent, rationale]
timestamp: 2026-06-19
edges: []
---

# Context & Intent

## The symptoms that started this

Observed in a prior "trustless ACP" and latent in UACP: the manifest phases are mutually
inconsistent because the relations between items are not load-bearing.

- **PROPOSE** — items carry wrong/unstated assumptions; the items themselves are inconsistent.
- **PLAN** — **phantom tasks** appear: a planned task with no real parent intent, and nothing can
  prove it is an orphan.
- **VERIFY** — the system "verifies" something that does not exist, or marks a task verified that
  was actually skipped.

The unifying cause: cross-phase relations are determined **semantically** (an LLM re-interprets
prose each phase) where they must be **deterministic** (retrieved and proven structurally).

## What we verified about the current system

The graph is **already deterministic from PLAN onward** — `work_unit_id`, `obligation_id`,
`piv_contract` are hard foreign keys; a checkpoint that names a non-existent work unit fails
validation. The integrity below PLAN is real.

**There is exactly one broken seam: PROPOSE → PLAN.** `scope.in_scope` is a list of bare strings
with no stable ids, and no plan field references back to a scope item. PLAN re-reads the proposal
*in prose* and re-authors its own structure. That single missing edge is the root of every symptom:

- A plan task with no parent intent cannot be flagged because scope items have **no identity**.
- You can prove "every assessment maps to a real work_unit," but you **cannot** prove "every intent
  maps to a work_unit that was executed and verified." The graph has a root detached from its trunk.

The reason it is semantic *here specifically*: everyone falls back to RAG precisely at the points
where they forgot to mint an id. No primary key → no foreign key can point at it → re-read the prose.

## The reframe that unifies the planes

On a human level, a spec/proposal/manifest is "governance." But from UACP's perspective those
artifacts are **also knowledge** — they describe intent, rationale, the business "why." They belong
in the same wiki database as lessons and references.

So the relation plane and the knowledge plane are not two stores. They are **one OKF wiki**, where
some nodes additionally carry hard edges. This reframe is what makes a *single* graph engine
possible, and it resolves the earlier objection against putting OKF on manifests:

- OKF as a **relation model** (markdown cross-links) — rejected: it would *downgrade* the FK
  integrity manifests already have.
- OKF as a **serialization container** (frontmatter holds typed hard-edge keys) — adopted: it lets a
  manifest be a wiki page whose edges stay provable.

(The full verdict and the options weighed are in [02-decisions](02-decisions.md) D1.)

## Intent (what we are actually building)

A serialize/deserialize graph engine that makes **all** manifest relations deterministic and
**provable by traversal**, with semantics confined to two bounded places: entry-point resolution and
the single `asserted` PROPOSE → PLAN translation. Plus the missing **negative space** — what *not* to
do, how *not* to, why *not*, and the measurements that bound it (see
[15-constraints-metrics](15-constraints-metrics.md)).

This bundle is **design-only**; nothing is built. It is the source material for a later governed run.

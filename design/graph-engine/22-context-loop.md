---
type: contract
title: Graph Engine — The Context Loop (knowledge plane extraction / injection)
description: How RESOLVE distills grounded context-artifacts, how in-flight capture works, the on-disk layout, embedding strategy, and partition/tag keys. "Context, not memory" — distilled-from-and-anchored-to the structural record.
tags: [graph-engine, context, knowledge-plane, extraction, resolve, contract]
timestamp: 2026-06-20
edges:
  - {dst: 11-node-taxonomy, rel: depends_on, provenance: derived}
---

# The Context Loop (knowledge plane)

**Framing (D30).** An agent doesn't *recall* — it is *handed context*. So the knowledge plane is not
"memory"; it is **durable, grounded, retrievable context-artifacts** distilled *from* the manifest (the
structural record of what happened) and anchored back to it by `derived_from`. Context is
distilled-from-and-anchored-to structural truth — never free-floating. The value is the **judgment of
what to extract**, not the storing (a bigger context window does not solve it).

## The loop (three timescales)

| Timescale | What | Trust | Lands in |
|---|---|---|---|
| **in-flight** (EXECUTE/VERIFY) | cheap auto-capture of raw signals at trigger points | low (candidate) | run-local `observation` nodes |
| **at RESOLVE** | judged distillation → typed, generalized, grounded artifacts | higher | knowledge plane (fact/lesson/procedure) |
| **across runs** | semantic **consolidation** (episode→pattern→rule) | rising per tier | tier migration via `promoted_to` |

```
TRIAGE/start  ← inject RULES (eager — always loaded)
PROPOSE/PLAN  ← inject PATTERNS (filtered by topic)
EXECUTE       ← inject EPISODES (by situation, JIT) ; CAPTURE in-flight
VERIFY        ← capture outcomes
RESOLVE       → DISTILL → CONSOLIDATE vs corpus → promote tiers
   └─ corpus grows → feeds the next run's injection
```
The manifest lifecycle **is** the injection schedule; each phase pulls its own tier.

## 0. Attribution & portability (every artifact — D33)

Distinct from grounding (`derived_from` = *why it's true*): an `attribution` block records *who/what
asserted it, under what conditions* — `generated_by {agent, model, runtime}`, `authorized_by` (reuse
`authority`), `source_run`, `project`, and a **`portability`** axis (`project-local | transferable |
universal`). Portability makes "does this transfer to a NEW project?" a deterministic filter, and composes
with the tiers below: **tier × portability = the transfer gate** (episode=project-local → cross-run
`rule`=universal). Git supplies commit-lineage; frontmatter supplies what git can't see (agent/model/
scenario). Attribution is descriptive — never overrides grounding. Full spec: [02-decisions](02-decisions.md) D33.

## 1. Extraction (RESOLVE — the 2nd judgment seam)

Typed distillation questions over the run graph → candidates. Three rules:
- **Grounding required:** every candidate cites `derived_from` → real run evidence; **ungrounded = rejected**.
- **Reconcile vs corpus:** semantic-search existing artifacts → **NEW** / **PROMOTE** (tier-up + add
  `derived_from`) / **SUPERSEDE** (contradiction by stronger evidence).
- **Gate high tiers:** episode→lesson cheap; pattern→rule needs N independent episodes or council.
- Symmetric to PROPOSE→PLAN: structural ground meets semantic judgment; `asserted`-grade.

## 2. Capture (in-flight)

A run-local **`observation`** node kind, emitted at trigger points (`result: fail` + fix, retry,
assumption-break, deviation), `derived_from` the checkpoint. Cheap, append-only, low-trust; RESOLVE
distills them; archived with the run unless promoted. (All judgment deferred to RESOLVE.)

## 3. File structure

```
knowledge/                       executions/{run_id}/
  _index.yaml                      observations/ obs-*.md   (run-local, archived w/ run)
  facts/ lessons/ patterns/ rules/   *.md  (OKF nodes)
```
Each = OKF node: frontmatter (`kind/type, tier, derived_from, source_run, status, tags`) + body.
Directories are convenience; **type/tier in frontmatter drives behavior** (not the dir).

## 4. Embedding (per D19/D29)

- **Embed** `facts`/`lessons`/`patterns` — the distilled body (episodic: embed the *problem/situation*
  text → retrieve by situation-similarity). Via the **Oracle** pipeline (BGE-M3 + Qwen3 rerank) → **LanceDB**,
  keyed by node id, **+ FTS** for exact terms.
- **Do NOT embed** `rules` (eager-loaded) or the manifest (never embedded).
- Embeddings are derived (rebuildable, gitignored).

## 5. Partition vs tag

- **Partition** (hard — changes store/access): by **plane**; **eager rules vs retrieved artifacts** (rules
  aren't in the vector index at all).
- **Tag** (soft — filter columns): `type`, `tier`, `domain/topic`, `source_run`, `status`, recency.
- **Phase-keyed injection = a *filtered* query** (`tier`+`domain`) — production retrieval is filtered, not
  whole-corpus (council F2), so tags MUST be indexable scalar columns beside the vector. Start logical
  (one table + filters); physically partition only if a domain gets huge.

## Lifecycle = reuse D18 (no new machinery)

Context-artifacts are knowledge-plane **nodes** with the manifest node lifecycle: created (extracted) →
promoted (`promoted_to`, tier-up) → **superseded** (newer/stronger-evidence contradiction) → tombstoned
(obsolete). **Contradiction management = supersede by evidence strength**, traceably. Same edges, same
closure discipline (`stale-reference` catches edges into superseded artifacts).

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Contradictory artifacts accumulate | supersede by evidence strength/recency; loser tombstoned but kept |
| Stale context re-injected | recency/decay weighting + tombstone filtering at injection |
| Injection noise (wrong tier at wrong phase) | phase-keyed, tier-scoped, bounded, **filtered** retrieval |
| One-off promoted to a "rule" | promotion gate (N independent episodes / council) |
| Ungrounded distillation | `derived_from` required; falsifiable by walking back to evidence |
| In-flight capture overhead | keep cheap/low-trust; defer judgment to RESOLVE |

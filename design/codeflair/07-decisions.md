---
type: analysis
title: Codeflair — Decisions & Settled Priors
description: The forks this design made explicit — with the alternatives weighed and the rationale — plus the load-bearing rejected prior (query-string expansion) that Codeflair must not be confused with. The sibling to graph-engine's 02-decisions, kept so future readers see what else was on the table and why it lost.
tags: [codeflair, decisions, rationale, priors, non-goals]
timestamp: 2026-06-24
edges:
  - {dst: 00-overview, rel: decides_on, provenance: asserted}
---

# Codeflair — Decisions & Settled Priors

Each entry: the decision, the alternatives weighed, and why. Numbered `CF-Dn` to avoid collision with
graph-engine's `Dn`.

## CF-D1 — Output authority = read-only heatmap (hypothesis only)

**Chosen:** the loop returns a ranked subgraph as a *hypothesis*; it writes nothing and asserts no edge.
**Rejected:** (a) propose candidate cause-edges submitted as gated proposals; (b) both at once.
**Why:** read-only output keeps Codeflair entirely out of the governance write-path, so there is no
governed-writer and no self-attestation risk, and it dissolves the LLM-vs-re-derivability tension
(evidence deterministic; only the path stochastic; trace replayable). Edge-promotion is a separate,
gated, deferred path ([06](06-open-questions.md)), not v1.

## CF-D2 — LLM role is decided by bake-off behind a fixed interface

**Chosen:** the policy (`next_probes` / `score`) is swappable; the default is chosen by measurement.
**Rejected:** picking A/B/C up front on argument. **Why:** house style — D12/D29/D44 were all
bake-offs (D12/D29 were measured bake-offs; D44 is an architecture correction, not a bake-off). The
interface, probes, outputs, and trace are invariant to the winner, so the harness ships before the
policy is fixed. (The contender set was later widened to include **Policy D**, no-LLM — see
CF-D5.)

## CF-D3 — Co-change is a first-class probe; default-on is benchmarked

**Chosen:** co-change is a first-class member of the probe set, but whether it is on by default is a
benchmark axis. **Rejected:** (a) symbol-only v1 (would literally miss non-symbol-linked relations —
the whole point); (b) co-change as a mere future add-on. **Why:** it is the only probe that finds
temporal relations no reference-walk can reach, *and* the noisiest — so it must exist but earn its
default. This resolves the apparent contradiction between [02](02-probes.md) ("first-class") and
[05](05-benchmark.md) ("on/off axis").

## CF-D4 — v1 is a spike around Oracle, not a standalone service

**Chosen:** v1 = a loop wrapped around the *existing* Oracle reranker + SCIP + Manifest-engine graph,
built to measure the iterated-beam + co-change delta. Graduate to a named standalone service only after
it proves out. **Rejected:** stand up Codeflair as its own application-ring service immediately.
**Why:** the council showed most substrate already exists; the genuine new delta is small (co-change +
beam-iterating the reranker). Building service-shaped infra before the delta is measured is premature
commitment. The graduation target's identity is already sanctioned by D44:912.

## CF-D5 — The bake-off must include a no-LLM control (Policy D)

**Chosen:** a mandatory deterministic-score policy (no model calls) as the benchmark's null hypothesis;
promotion gate = an LLM policy must beat D by a stated margin on recall@K (esp. the `inferred` subset),
not merely beat the 42s bar; recall@K reported split by probe provenance. **Rejected:** A/B/C only.
**Why:** with every contender containing an LLM, the bake-off could not discover the LLM is unnecessary.
"Pruning is necessary" (true, cardinality) was being conflated with "LLM pruning is necessary"
(unproven). Policy D is what makes the most expensive, least-deterministic component stand trial.

## CF-D6 — Gaps: first-class output, best-effort scored

**Chosen:** gaps (missing tests, orphan symbols, cross-plane orphans) stay a first-class *output* but
are scored on a separate best-effort label set, not folded into the primary recall@K. **Rejected:**
(a) demote gaps to an unscored side output; (b) keep gaps fully in the primary metric. **Why:** gaps are
the most actionable part of the heatmap and serve the original "get the gap" mission, but they are
*absences* with no clean ground truth — folding them into recall@K would define an ill-posed metric.

## CF-D7 — REJECTED PRIOR (do not re-walk): query-string expansion

**This is load-bearing.** Codeflair does **search/evidence expansion** — iterating *probe → prune* to
grow the evidence frontier. It is **not** *query-string expansion* (rewriting/synonym-expanding the
search query). Query-string expansion was **built, then removed as dead code** (zero callers) in this codebase; the
evidence — IR literature + the QMD hybrid-search retirement at ~42s/query — is that it is the **wrong
target on a strong-rerank stack**. Because "expansion"
is Codeflair's central verb, a future reader — or an Oracle/edge-model reviewer — could mistake the
expansion loop for a re-tread of that dead path. **It is not.** Any proposal that reintroduces
query-string rewriting under the Codeflair banner is out of scope by this decision.

## CF-D8 — Codeflair IS the Code Engine (build + store + query), reversing "not an engine"

**Chosen:** scope Codeflair as UACP's **4th engine** — the whole codespace plane: it **produces** the
code graph (SCIP indexing, [01a](01a-indexer.md)), **stores** it ([01b](01b-store.md)), and **queries**
it (the relation-finder, [02](02-probes.md)+). **Rejected:** the first cut's *read-only lookup driver,
not an engine*. **Why:** that narrow scope exposed a real gap — `code_anchor`/`code_symbol` are declared
edge types **with no producer** ("no code indexing exists today"), and graph-engine called the code plane
*"the real strain"* (D12) yet never built it. Designing the **consumer** on an unbuilt **producer** is
the gap. The all-in-one engine closes it by construction and matches D44's already-named *"Code engine
(the future 4th) — build = SCIP per-commit + LSP live; query = symbol/reference lookup."*

**Consequence (a deliberate reversal):** owning the code-graph store makes Codeflair an **engine**
(`29-ddd-ca-reference.md`: *storage is touched only by engines*). The R1/R2 councils' "not an engine"
was **correct for the lookup-only scope** — a pure reader owns no storage — and is reversed only because
the scope changed. The same reference carries a *"if you're about to add a 4th 'engine,' stop — it's
almost certainly a Check, Leaf, or Gate"* guard — but that line **also names "Code later"** as the
sanctioned 4th plane (State/Manifest/Oracle/Code), so the Code engine is the guard's explicit exception,
not a new invention it forbids.

The build-side writes a rebuildable index (a derived cache, not governed state, D29/D44 — and the
precedent is Oracle's persisted LanceDB index, *not* the in-memory graph_projection); the **query layer
stays read-only/hypothesis-only** over that store. The write is sound **only** under the preconditions in
[01b-store](01b-store.md) (store outside `.uacp/`'s governed roots; build path registered as a
self-attesting engine op). This decision **supersedes** the "not an engine / read-only service" framing
wherever the earlier nodes still carry it.

## CF-D9 — Codeflair core is UACP-independent; UACP is a pluggable adapter

**Chosen:** factor the engine into a **standalone core** (SCIP/LSP/grep/co-change + store + loop +
heatmap — runs on any git repo, **zero UACP**) and a thin **UACP adapter** (the manifest-graph probe +
the `code_anchor` cross-plane join + the governed-writer/Guardian wrapper + the run watermark). The
dependency arrow is **adapter → core**, never the reverse; a core import of anything UACP-specific is the
litmus violation. Full boundary in [09-abstraction](09-abstraction.md). **Rejected:** baking UACP
manifest/governance assumptions into the engine. **Why:** code intelligence is valuable on any codebase,
not just under UACP; coupling the core to UACP would forfeit that and make the engine untestable outside
a governed run. The seam is a **probe registry** + a stable **`query(seed,k,budget)→heatmap`** API: the
loop is blind to which probes are registered, so UACP just *adds* the cross-plane probes + relation-plane
node types. **Consequence:** without UACP you keep the whole code-side (blast radius / relations / gaps /
trace) and lose only the cross-plane "what governs this code" half. The eval set already reflects the
split (`layer: core|uacp-adapter`; 5 core / 1 adapter). The governed-writer preconditions of
[CF-D8](07-decisions.md)/[01b-store](01b-store.md) are **adapter-scoped** — standalone, the engine just
writes a cache dir.

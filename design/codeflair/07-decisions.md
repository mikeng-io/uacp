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
almost certainly a Check, Leaf, or Gate"* guard — but the same reference **schedules "Code later"** as a
future plane (State/Manifest/Oracle/Code), so the guard does not block it: the Code engine exists because
the scope changed (CF-D8), not as a new engine the guard forbids.

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
trace) and lose only the cross-plane "what governs this code" half. The eval seed-set is split the same
way (`layer: core | uacp-adapter`; see `eval/seed-set.yaml`, PR #13). The governed-writer preconditions of
[CF-D8](07-decisions.md)/[01b-store](01b-store.md) are **adapter-scoped** — standalone, the engine just
writes a cache dir.

## CF-D11 — Codeflair is deterministic; no LLM in the core (Policy D is the engine)

**Chosen:** the engine is a **deterministic graph + statistics** machine — index (SCIP/LSP parse) →
store (SQLite) → traverse (recursive CTE) → rank (edge-type · graph-distance · co-change-PMI · recency ·
centrality). **No LLM in the core loop.** **Rejected:** the "light-LLM-pruned loop" (the old A/B/C
framing) as the default. **Why:** reasoning from first principles, *blast radius is transitive closure and
relevance is a scoring function* — neither is semantic. Empirically confirmed on Trustless: sub-millisecond
correct blast radius, zero LLM, ~200,000× under the 42s/query bar. Policy D (no-LLM) is therefore the
**default engine**, not a benchmark control; A/B/C are deferred curiosities. **Policy D uses no model at
all.** *If* a deferred LLM policy is ever revisited, its use is confined to **structure** (rank/cluster),
**never content** (no summarizing/"semanticfy" — that breaks
re-derivability and steals the orchestrator's job). Semantics lives in the **orchestrator**, not Codeflair.

## CF-D12 — Standalone, zero-UACP, installable package; repo location reversible; Go is the product home

**Chosen:** a standalone, **zero-UACP** package — lib + CLI + MCP + plugin (CF-D9 faces), independently
installable, a CI lint enforcing "no UACP import in core." **DECIDED: it lives as an in-UACP abstracted
package** (the boundary, not the repo, makes it standalone) — extract to its own repo only if
adoption/release-cadence later demands; reversible. **Product language = Go**
(single static binary for portable execution, SCIP-ecosystem-native, embeds scip-go, dogfoods); Python is
the spike language; perf is language-agnostic (SCIP+SQLite do the work). **Install model:** one binary;
Codeflair auto-fetches **prebuilt** SCIP indexers (not `go install` — empirically broken); LSP is
**discovered/provisioned and degrades gracefully, never dropped** (it's the freshness half of the SCIP⊕LSP
reconcile); the host installs only Codeflair + the toolchain it already has for its own code. Detail in
[12-delivery](12-delivery.md). *(No tension with [CF-D4](07-decisions.md): CF-D4's "not a standalone
service" was about not being a separate **application-ring service inside UACP**; CF-D12 is the
**packaging/distribution** boundary — orthogonal axes.)*

## CF-D13 — Cross-language coherence is deterministic; the LLM is a deferred residual

**Chosen:** cross-language links are built from **deterministic** signals — **grep** (shared route/command/
event strings; grep is language-agnostic), **contract parsing** (proto/OpenAPI/GraphQL codegen), and
**co-change**. SCIP gives **zero** cross-language edges (proven), so these *construct* the inferred layer.
**Rejected (deferred):** a semantic/embedding matcher. **Why:** the real couplings (HTTP/CLI/events) are
shared strings grep already catches; the only residual an LLM adds is meaning-matched entities with no
shared string, no contract, and no co-change — **weak-by-definition**, probably not blast-radius-relevant.
Revisit an LLM only if real usage proves the residual matters. Cross-language edges are `inferred`,
hypothesis-only. Detail in [13-multi-language](13-multi-language.md). *(This, with CF-D11, lands the whole
design: Codeflair is deterministic, core and cross-language; the LLM is a maybe-never.)*

## CF-D14 — Adopt the substrate, build only the fuse + UACP adapter (tree-sitter base + SCIP/LSP refine)

**Chosen:** a 2026 prior-art check ([14-prior-art-and-adoption](14-prior-art-and-adoption.md)) shows the
code-graph-for-agents engine is **commodity** (Serena, Aider repo-map, Codebase-Memory, codegraph, knowing,
…). So Codeflair **adopts the substrate and builds only the novelty.** **Rejected:** building the engine
from scratch. **The probe stack is a precision ladder** — **tree-sitter** is added as the *breadth/fallback
floor* (all languages, no toolchain, parses broken code; fuzzy) under **LSP/SCIP** *refinement where
available* (precise). This resolves efficiency-vs-quality by **layering, not choosing**: tree-sitter where
SCIP can't reach, SCIP where the toolchain allows (UACP's trust-grade case). **Build:** the fuse/reconcile
+ ranking + the **UACP cross-plane adapter** (the only genuine novelty). **Adopt:** tree-sitter (base),
**Serena/multilspy** (live LSP — don't hand-integrate N servers), `scip-go` etc. (precise SCIP). The spike
is the eval harness for choosing among adoptable graph tools.

---
type: analysis
title: Graph Engine — Code-Plane Substrate Bake-Off
description: Web-sourced (2026-06-19) evaluation of the code-plane indexer, the embedded graph/vector store, and the LanceDB-replacement risk. Verdict — SCIP + SQLite + keep LanceDB; SurrealDB/Kùzu/Cozo rejected with reasons.
tags: [graph-engine, bake-off, scip, sqlite, surrealdb, lancedb, code-plane]
timestamp: 2026-06-19
edges:
  - {dst: 02-decisions, rel: realizes, provenance: derived}
---

# Code-Plane Substrate Bake-Off (2026-06-19)

Three parallel research tracks, web-sourced. Triggered by the finding that trustless's real strain was
**codespace lookup/search**, and the proposal to replace LanceDB with SurrealDB.

## Track 1 — Indexer: **SCIP wins**

| Candidate | Verdict |
|---|---|
| **SCIP** (Sourcegraph) | **1st.** Symbol/reference-precise (Occurrence→Symbol→Relationship; `defines`/`references`/`imports`/`implements` with line ranges); Apache-2.0; maintained (successor to LSIF; indexers for TS/Py/Go/Rust/C++/Java/…); fully local; loads as edge-rows via `scip print --json` or a `protoc` Python binding. |
| tree-sitter (+ast-grep) | **2nd, complementary only.** Syntactic/CST — no cross-file reference/call resolution → repeats the "too coarse" failure if used alone. Use as a cheap change-detector to trigger SCIP re-index. |
| Stack Graphs (GitHub) | **Out — archived Sep 9 2025.** Best incremental design, but unmaintained. |
| LSIF | **Out — dead.** Deprecated into SCIP (destructive migration). |
| raw LSP | Wrong shape — SCIP indexers already wrap these engines and serialize the whole graph in one pass. |

**Gap:** SCIP has no file-level incremental indexing yet → re-index per commit/checkpoint (acceptable for
governance cadence; not per-keystroke). Sources: announcing-scip, sourcegraph/scip (proto, CLI, license),
github/stack-graphs (archived), LSIF→SCIP migration docs, ast-grep tool-comparison.

## Track 2 — Embedded store: **SQLite + recursive CTE wins** (the purpose-built graph DBs collapsed)

| Engine | Note |
|---|---|
| **SQLite + recursive CTE (+sqlite-vec)** | **1st.** Zero abandonment risk, zero install friction, single-file rebuildable index, best Python fit. Handles bounded-depth code traversal + moderate vectors. **Caveat:** recursive CTE degrades on deep multi-hop over ~500K+ nodes; sqlite-vec is brute-force/IVF, not full HNSW. |
| CozoDB | **2nd technically** (Datalog graph + HNSW, 2-hop <1ms @1.6M/31M), but **dormant** (no release since Dec 2023; commits stale ~18mo; alpha Python binding; unanswered maintenance issue) → fork-dependent. |
| Kùzu / LadybugDB | **Fastest embedded graph engine benchmarked** (15–374× over Neo4j; HNSW vectors) but **archived Oct 2025** (Apple acqui-hire). LadybugDB fork on watch — revisit if it sustains 6–12mo maintenance. |
| DuckDB (+VSS/DuckPGQ) | Graph + vector extensions **both experimental**; VSS persistence "not recommended in production." |
| SurrealDB (embedded) | Server-first, heaviest; embedded mode lacks client transactions. BSL 1.1 (embedding allowed, not a blocker). Overweight for a rebuildable file index. |
| ArcadeDB | **Dismissed** — JVM; fails Python/zero-infra/in-process. |

Sources: The Register (Kùzu acqui-hire), gdotv embedded-graph landscape, Kùzu benchmark, Cozo perf/HNSW
docs + GitHub activity, sqlite-vec stable release, SQLite-as-graph write-up, DuckDB VSS/DuckPGQ docs,
SurrealDB embedding + license docs.

## Track 3 — Replace LanceDB? **No** (reranker is store-agnostic, so keeping it costs nothing)

- **LanceDB** today: IVF(+HNSW sub-index), native BM25 FTS, native hybrid (RRF), Lance columnar format, Lance SDK 1.0 (Dec 2025); embedded, disk-native. The incumbent baseline.
- **SurrealDB vector: MEDIUM-HIGH risk.** First-class hybrid (BM25+HNSW+`search::rrf()`) is a real plus, but: 3.0.0 shipped a KNN correctness bug; **open embedded-backend corruption bug #6872**; HNSW RAM-resident (256MiB cache); DiskANN persistence ~1 month old; no independent recall benchmark. Worth it **only if** already consolidating onto SurrealDB for the code graph — which the Track-2 verdict says we are **not**.
- **CozoDB vector: HIGH risk** — project-liveness, not vector quality (dormant; alpha binding; no native hybrid).
- The **Qwen3 reranker sits post-retrieval → store-agnostic**; it survives any swap. No independent ANN benchmark exists comparing these for local RAG → any swap must budget its own recall@k harness first.

## Synthesis / Verdict

**Net substrate:** **SCIP** indexer (+ tree-sitter change-detector) · **SQLite + recursive CTE** for ALL
deterministic edges (manifest + code graph) · **LanceDB** for ALL vectors (Oracle + code fuzzy search).
**No SurrealDB, no Kùzu, no Cozo** in v1.

The user's scale point stands (code-plane lookup is central — it's Slice 2), but the SurrealDB swap is
**not** justified: the multi-model graph engines that would justify it are abandoned (Kùzu), dormant
(Cozo), or immature-embedded (SurrealDB), and the code-graph winner is the same SQLite the manifest
plane uses — so the consolidation premise never materializes.

**Watch-trigger to reconsider a unified graph+vector engine:** LadybugDB (Kùzu fork) demonstrating
6–12 months of sustained maintenance **AND** a measured deep-multi-hop traversal wall on SQLite at the
code-graph scale we actually reach. Decide then, with data — not on faith now.

## Quality evidence: sqlite-vec (exact) vs LanceDB (approximate) — 2026-06-19

> **Re-anchored by D27 (council T8):** the "RAG quality near-flat across recall 0.4→1.0" claim and the
> arXiv 2606.04522 cite are **withdrawn** (overstated / uncorroborated). The sound claim stands on its
> own: **sqlite-vec is exact ⇒ 100% recall ⇒ strictly ≥ any ANN.** The LanceDB-retirement gate is
> **3-axis**: filtered recall@k (plane/run-scoped) + p95 latency at size + independent rebuild cost.

Settles whether the single-DB choice (D16) costs retrieval *quality*. It does not — it improves it at
our scale.

- **sqlite-vec = exact brute-force KNN = 100% recall by construction.** It is the ground truth others
  are measured against. (sqlite-vec KNN docs; author Alex Garcia issue #25: "brute-force search only".)
- **LanceDB = approximate (ANN).** Its own docs use the flat/exhaustive scan as the "ground-truth to
  measure ANN recall" — i.e. ANN sits *below* exact. Recall is a tuning dial (`nprobes`/`refine_factor`),
  and PQ/SQ quantization "can significantly reduce recall" (LanceDB docs; Chang She benchmark). Known
  defect: issue #1428, IVF_HNSW_SQ/PQ recall ~87% vs Faiss ~97%.
- **Head-to-head recall@10: sqlite-vec 1.00 vs LanceDB 0.96** (Shaharia Azam Go embedded-DB benchmark).
- **Quality is dominated by the embedding model + reranker, not the store** — and RAG answer quality is
  near-flat across recall 0.4→1.0 (arXiv 2606.04522: BERTScore varies ≤1.2%; "inadequate" recall still
  yields answers "of identical quality as exact kNN"). So the 1.00-vs-0.96 gap barely reaches the answer.

**Conclusion.** On the quality axis, sqlite-vec (exact) ≥ LanceDB (approximate) wherever an exhaustive
scan is affordable (~thousands → hundreds-of-thousands of vectors). LanceDB's value is **scale/speed**
(defending recall once exact search is too slow), not quality. So the single-DB decision is
**quality-justified**; the only open check for the Oracle corpus is its *size* (exact-search speed),
not its recall.

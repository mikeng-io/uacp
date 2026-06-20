---
type: analysis
title: Graph Engine — Decision Ledger
description: The decisions made in design, each as options-considered -> verdict -> rationale. This is where the conversation's judgment is preserved instead of evaporating.
tags: [graph-engine, decisions, verdict, rationale]
timestamp: 2026-06-19
edges:
  - {dst: 01-context-intent, rel: decides_on, provenance: asserted}
---

# Decision Ledger

Each decision: the options weighed, the **verdict**, and the rationale. Verdicts here are
design-level; they are ratified (or overturned) when this bundle enters a governed run.

---

## D1 — OKF: container, not relation-model

**Options.** (a) Force OKF/llm_wiki link-based relations onto manifests. (b) Adopt OKF only as a
serialization *container* (frontmatter holds typed hard-edge keys). (c) Keep manifests outside the
wiki entirely.

**Verdict: (b).** Adopt OKF *format* across all manifests; keep edges as typed keys, never markdown
links.

**Rationale.** Manifests already carry hard FKs (`work_unit_id`, `obligation_id`). OKF's relation
model is markdown cross-links — a broken link cannot *fail*, so forcing it would **regress** the
strongest part of the system to hyperlinks. But OKF's *frontmatter* is structured YAML — the perfect
home for a `{rel_type, provenance}` keyed edge. So we take the container and reject the relation
model. OKF over llm_wiki because OKF is format-only, vendor-neutral, and already adopted (ADR-0017);
llm_wiki is an app whose "graph" is relevance-weighted (soft edges). Steal one llm_wiki primitive
only — `sources:` provenance — which UACP already has as `derived_from`.

## D2 — SQLite projection, not a native graph DB, not graph-as-source-of-truth

**Options.** (a) Native graph DB (Neo4j) as source of truth. (b) Graph-as-source, Markdown rendered
from it. (c) Governed YAML/Markdown stays source of truth; project deterministically into SQLite
(node + edge tables; recursive CTEs for traversal).

**Verdict: (c).**

**Rationale.** UACP's authority and audit model is file-based and git-versioned, and the governed
writers write files. SQLite is "an existing relational structure" with real FKs and recursive-CTE
graph traversal — zero new infra. The projection is *pure* (same artifacts in → same graph out), so
it inherits the artifacts' trustworthiness without becoming a second source of truth. The same
node/edge tables export to a graph DB unchanged if ever needed.

## D3 — Granularity: entity = file, not aggregate = file

**Options.** (a) One file per aggregate (current: whole PIV with all work_units in one file).
(b) One file per entity (task), aggregate = directory + `_index.yaml`. (c) Maximal shatter.

**Verdict: (b).** Superseded an earlier "aggregate = file" stance taken mid-design.

**Rationale.** Monolithic files are *how* siblings get silently dropped: a whole-file rewrite passes
every sibling task through the model on every edit. Entity-per-file shrinks the write blast radius to
one node. Reject (c): maximal shatter recreates the fragmentation/reassembly tax (manual
note-gardening). The cut is **identity + independent lifecycle**, not "more files." Precedent: the
lessons corpus and EXECUTE checkpoints are already one-file-per-entity.

## D4 — v1 is lookup, not synthesis

**Verdict.** v1 deserializes and traverses only. Synthesis (generating explanations/decompositions)
is deferred.

**Rationale.** Lookup is replay of serialized keys — provable by construction, cannot lie. Synthesis
is where semantics and trust leakage re-enter. Draw the v1 boundary where determinism holds.

## D5 — Code/reality plane deferred to Slice 3

**Verdict.** Slice 1 = governance + knowledge (intent → verify). Code-plane (`code_anchor` + symbol
indexer) is Slice 3.

**Rationale.** The intent→verify half is buildable now from artifacts UACP already writes plus two
keys. The code half is a whole second surface (a code indexer + a new EXECUTE evidence obligation)
and should not gate the foundation. Code/reality is itself *deterministic* (AST/LSP/git, not
semantic) — deferral is about scope, not difficulty of principle.

## D6 — Entity-level writes, not permissive path writes

**Verdict.** Promote governed writers from path-level (`write_path(blob)`) to entity-level
(`create_work_unit(run_id, {...})`); fold schema-validation-on-write into Slice 1.

**Rationale.** Today `_handle_uacp_artifact_write` writes whatever YAML it is handed — a producer can
serialize a malformed edge. For a serialization engine that is a correctness hole. The entity-level
writer is where the OKF-frontmatter + edge-key contract is *enforced*, and it expresses the Clean
Architecture dependency rule at runtime (the agent talks to a repository, never the filesystem).

## D7 — Negative space is first-class (Slice 3 — amended 2026-06-20 from Slice 2; deferred per council)

> **Amended (council D27/Devil-F4):** slice number corrected to Slice 3, and the whole constraints/
> metrics plane is **deferred** (extract when a real "agent did unrequested work" failure exists). For
> v1, `out_of_scope` with one `prohibition` kind + `constrains` edge captures most of it — *no*
> metric/threshold engine.

**Verdict.** Promote `prohibition` / `method_constraint` / `metric` to node kinds with
`constrains` / `measured_by` / `violated` edges. `out_of_scope` bare strings are deprecated as the
weak form.

**Rationale.** Today the manifest serializes only affordances (do X / how / why). Guardrails live as
unenforceable prose. A constraint + metric becomes a deterministic EXECUTE/VERIFY check; negative
edges are as provable as positive ones. PLAN bites hardest — it inherits zero enforceable limits from
PROPOSE today. (Detail in [15-constraints-metrics](15-constraints-metrics.md).)

## D8 — `uacp-fmt` + `uacp-lint`: standalone package over a shared pure-leaf rules module

**Options.** (a) Pack the formatter/validator inside `uacp-core`. (b) Standalone tools that keep their
own copy of the schema. (c) A standalone `uacp-lint` package carrying **both** `lint` and `fmt`
subcommands (ruff-style), as a thin shell over a single **pure-leaf rules module** that the
`uacp-core` write path imports too.

**Verdict: (c).**

**Rationale.** Standalone wins the developer/CI/cross-runtime surface — a portable CLI, importable,
MCP-exposable — and fits the ADR-0017 "tool" skill convention. But the node/edge schema must have ONE
source: (b) duplicates it, violating no-authority-mirrors and inviting drift; and if a standalone tool
imported `uacp-core` while the core writer imported the tool, that is a **cycle**. Resolution: the
schema + rules live as a **pure-leaf module** (the `engines/domain` leaf pattern already exists —
`phase_graph.py` is a stdlib-only leaf). Both the standalone tool and the in-process write path import
the leaf; neither imports the other. `uacp-fmt` and `uacp-lint` ship as **one skill, two subcommands**
— NOT two skills. Decisive reason: they must agree on the same schema; as two skills they can
version-skew (fmt emits a form lint rejects) — a bug impossible by construction when they are one
skill over one leaf. They are co-invoked (write path runs fmt→lint; CI runs both) and never used
independently of the same rules; self-containment is satisfied by the single cohesive responsibility
"manifest-node hygiene = canonical form + validity". Two skills would be justified only if fmt and
lint had independent consumers and independent schemas — they have neither. **Closure/cross-node
checks do NOT live here** — they stay in the `uacp-core` projection engine; this skill is node-local
well-formedness + canonical form only.

## D9 — schema-first: every YAML validated, closed-world, enums everywhere

**Verdict.** Every YAML — every node, every aggregate `_index.yaml`, config — validates against a
**fixed JSON-Schema** (draft 2020-12). `additionalProperties: false` (closed-world); **enums for every
closed vocabulary** (`kind`, `provenance`, `rel_type`, `result`, `status`, `phase`, `severity`); a
`description` on every field stating what it is / does / does not. No "trust me, the YAML is good" —
**including the design bundle's own `_index.yaml`** (dogfooded via `schema/design-index.schema.json`).

**Rationale.** A serialization engine that does not validate its own serialization is self-attesting —
the exact failure the design rejects. Enums turn invalid values into load-time errors. Closed-world
catches typo'd/renamed keys that would otherwise silently drop an edge. JSON Schema is
language-agnostic; pydantic models may *export* to it so code and schema stay one source.

## D10 — `uacp-schema`: a separate foundational pure-leaf package, not composed into `uacp-core`

**Verdict.** A separate minimal `uacp-schema` package (JSON-Schema files + enums module + a thin
`jsonschema`-based `validate()`; no kernel logic, no policy).

**Rationale.** The schema registry IS the pure-leaf rules module and the **sink of the dependency
graph** — `uacp-lint`, `uacp-fmt`, Guardian, Heartgate, the projection engine, and the `uacp-core`
writer all depend on it. If it lives inside `uacp-core`, standalone `uacp-lint` must drag the whole
kernel just to read a schema (killing "standalone" and re-opening the cycle risk). As its own minimal
package nobody imports `uacp-core` to get schemas; it is the "shared kernel of types at the bottom".
`uacp-core` *composes* it; the schema authority now scattered across `validate_uacp_artifacts.py` +
`engines/domain/artifact_schema.py` + config YAMLs relocates here as the single registry.

## D11 — storage substrate: YAML source of truth; SQLite for relations, LanceDB for semantics; native graph DB deferred

**Context.** "Manifests in a graph DB (SurrealDB/ArcadeDB) instead of YAML?" conflates two layers:
**serialization / source-of-truth** (YAML-OKF — git, audit, governed writers) and the **index / query
substrate** (where you traverse). The DB question is only about the latter.

**As-is (audited 2026-06-19).** Manifests live on a **plain filesystem**; retrieval is globbing. The
only DB is **LanceDB**, used solely for the Oracle knowledge corpus. **No index for manifest relations
exists** — relational data on a bare FS.

**Verdict.** Source of truth stays YAML-OKF. Index splits by plane: **SQLite + recursive CTE** for the
deterministic relation plane (D2 holds); **LanceDB** for the semantic plane (entry-point resolution +
inferred edges — already its job, locked). **No native graph DB in v1.**

**Rationale.** Manifest graphs are small (tens–hundreds of nodes per run, DAG-ish); recursive CTEs
handle them trivially, embedded and zero-infra, and the projection is a rebuildable cache. ArcadeDB
(JVM) is a poor fit for a Python/file kernel. SurrealDB is interesting (multi-model graph+vector,
embeddable; could someday unify SQLite+LanceDB) but adds a runtime dependency, and LanceDB is already
baked-off + locked — replacing it buys nothing in v1. **Don't pick a graph DB because the data "has
graph elements"; pick one when traversal/pattern-query cost exceeds recursive SQL.** **Reconsideration
trigger:** Slice 3's code-plane symbol graph (100k+ nodes, dense cyclic edges) is where CTEs strain and
a native graph engine earns its dependency — decide then, with that data in hand.

**Amended by D12 (2026-06-19):** the graph-DB decision is **code-plane-local**, and trustless evidence
indicates the code plane is the *central* lookup problem — so it is **live now**, not deferred. The
"manifest graphs are small" reasoning still holds for the relation plane; it never applied to the code
plane.

## D12 — codespace indexing: symbol/reference-precise code intelligence; the store is where a graph+vector engine is justified

**Context.** Per trustless's own history, the serious unsolved strain was **lookup/search over the
codespace**, not verify-side manifest granularity. Two pieces of evidence: (a) its code graph
(`.trustless/indexes/codegraph/graph.json`) was **file-level symbol/import extraction** — too coarse to
bind a task to the right *symbol* ("locking things into the codespace"); (b) it built a full hybrid
vector search (QMD), measured it at **42s/query**, and **retired it** (2026-05-24). Coarse graph + slow
naive RAG = lookup that does not work. This is the granularity problem the design must solve, and it is
distinct from (and harder than) the manifest granularity already settled.

**Two separable decisions** (do not conflate):

1. **Indexer** — adopt **symbol/reference-precise code intelligence**: **SCIP** (Sourcegraph; protobuf;
   successor to LSIF; per-language indexers) or **Stack Graphs** (GitHub; incremental, tree-sitter
   name resolution). NOT a hand-rolled file-level syntactic graph; NOT whole-document vector RAG. The
   precise `defines`/`references`/`calls` edges are the `parsed`-provenance code-plane edges
   ([10-edge-schema](10-edge-schema.md)).
2. **Store** — a real-repo symbol graph is 100K–1M+ edges (dense, cross-referenced). This is where
   SQLite CTEs strain and a **native graph + co-located vector engine (SurrealDB)** is justified —
   here, not in the manifest plane. Replacing LanceDB becomes reasonable IF this store is stood up
   anyway: the Qwen3 reranker is post-retrieval / store-agnostic, so it survives a LanceDB→SurrealDB
   move, and one multi-model engine can hold code-graph traversal + code semantic search + (optionally)
   Oracle vectors.

**Verdict.** Adopt a symbol/reference-precise indexer (SCIP or Stack Graphs — bake off). Evaluate a
graph+vector store (SurrealDB) for the code plane via a measured bake-off against the Qwen3 pipeline
before committing to replace LanceDB. Do NOT commit to SurrealDB on faith. The manifest plane stays on
YAML + SQLite (it is the spine code anchors attach to); the code plane is where the substrate question
genuinely lives.

**Bake-off result (2026-06-19, web-sourced — full detail in [17-codeplane-substrate-bakeoff](17-codeplane-substrate-bakeoff.md)):**
- **Indexer → SCIP** (Apache-2.0; symbol/reference-precise; maintained; edge-rows via `scip print --json`); tree-sitter as a cheap change-detector. Stack Graphs archived Sep 2025; LSIF dead; tree-sitter-alone too coarse.
- **Store → SQLite + recursive CTE** (same engine as the manifest plane). The purpose-built embedded graph DBs collapsed in 2025: KùzuDB archived (Apple acqui-hire; LadybugDB fork too young), CozoDB dormant since 2023-24, DuckDB graph+vector experimental.
- **SurrealDB → rejected.** Server-first/heaviest; embedded vector is months-post-GA with a shipped KNN correctness bug + an OPEN embedded-storage corruption bug (#6872) + RAM-resident HNSW. Its only justification was "consolidate the code graph onto it" — but the code-graph winner is SQLite, so that condition never materializes.
- **LanceDB → kept** (Oracle + code fuzzy search); the Qwen3 reranker is post-retrieval/store-agnostic, so keeping it costs nothing.
- **Net:** SCIP indexer; SQLite for ALL deterministic edges (manifest + code graph); LanceDB for ALL vectors. No SurrealDB.
- **Watch-trigger:** revisit a unified graph+vector engine only if LadybugDB (Kùzu fork) sustains 6–12mo maintenance AND a measured deep-multi-hop wall appears on SQLite at real code-graph scale.

## D13 — vectors co-located in SQLite (sqlite-vec); LanceDB scoped to Oracle; no cross-store atomicity

**Verdict.** New vectors (code fuzzy search, manifest entry-resolution) live in **sqlite-vec inside the
relation SQLite** — one store, ACID via SQLite's own transactions. **LanceDB is scoped to the
pre-existing Oracle corpus only.** There is **no cross-store transaction**: truth is the files; both DBs
are rebuildable projections, each tagged with a **source watermark** (commit/content hash); stale →
rebuild; crash mid-build → rebuild (truth never corrupts).

**Rationale.** Answers the atomicity question by removing it. Co-locating new vectors with the relation
edges means the hot write path touches a single SQLite file. sqlite-vec's brute-force/IVF is fine at
code-symbol / manifest scale (thousands–tens of thousands), and the Qwen3 reranker is store-agnostic so
quality is preserved. Corrects the earlier "LanceDB for all vectors" framing. (Alternatives if
constraints change: CozoDB — one engine graph+vector — if it were maintained; Postgres+pgvector+AGE if a
server is acceptable. Under embedded/zero-infra, SQLite+sqlite-vec wins.)

**Clarification (the DB never replaces git).** SQLite is a `.gitignore`d, rebuildable **index** — git
tracks the OKF/YAML *files* (the manifest), which stay fully diffable/reviewable. The DB holds nothing
authoritative. A "data-lake / query-in-place" alternative also exists and keeps files-as-truth even more
literally: **DuckDB** (the embedded equivalent of AWS Athena — full SQL incl. recursive CTE over local
JSON/Parquet, no server) querying git-tracked JSONL/Parquet directly, removing the separate-index step.
Trade-off: DuckDB's graph (DuckPGQ) + vector (VSS) extensions are experimental, and the data must be
JSON/Parquet (git-diffable but less human-readable than OKF). Decision stands at SQLite-as-index for
maturity; DuckDB-over-files is the noted fallback if avoiding a separate index becomes a priority.

## D14 — the `Index` port: one abstraction composing the hybrid backends, adapter-swappable

**Verdict.** The system depends on a single **`Index` port** — `sync()` (build/project), `resolve()`
(fuzzy entry), `search()` (fuzzy search), `walk()` (exact CTE traversal), `lookup()` (hybrid:
resolve ∘ walk). The **default adapter** composes SQLite(+sqlite-vec) + LanceDB(Oracle). No caller
touches a backend directly.

**Rationale.** Clean Architecture port/adapter. (1) **Ends the substrate churn:** SQLite / DuckDB /
SurrealDB / Kùzu become interchangeable adapters behind the same port, so the store choice
(D2/D11/D12/D13) is a localized swap, never a caller change. (2) **Enforces the read-model boundary:**
the adapter is the *only* component that touches a backend → "files = truth, indexes = derived" becomes
structurally enforceable. (3) **One home** for build + watermark + staleness, and for the hybrid
choreography (fuzzy-entry then exact-walk). Lives in `uacp-core` (kernel infra), depends on
`uacp-schema` (leaf); not a standalone dev tool. **Closure checks sit ON TOP** (queries via the port,
consumed by Heartgate), not inside the Index.

## D15 — data-plane shape & naming: one Index engine over two stores (relation + semantic)

**Verdict.** The data plane = **one `Index` engine** (the D14 facade) composing **two stores** — a
**relation store** (exact edges; SQLite + recursive CTE) and a **semantic store** (fuzzy; vector + FTS)
— built by a **projector** (files → stores; SCIP feeds code edges). It is **not** "three sibling
engines": `Index` is the *parent facade*, not a peer of relation/semantic.

**Naming.** Use **relation store** + **semantic store**. **Reserve "knowledge" for the Oracle *corpus***
(a dataset that lives in the semantic store) — the same store also holds code/manifest vectors that are
not "knowledge", so name the component by function (semantic search), not by one of its datasets.

**Semantic-store adapter candidates** (swappable behind the Index port, D14): `sqlite-vec`, **LanceDB**
(Oracle, current), and **`zvec`** (Alibaba; in-process; Apache-2.0; HNSW/IVF/DiskANN; vector+FTS+hybrid;
11.5k★, active, battle-tested) — the leading contender, and potentially a single vector engine for all
planes. Gate on a **recall bake-off vs LanceDB** before making any default; do not replace Oracle's
locked LanceDB without it.

## D16 — single database: one SQLite (sqlite-vec + FTS5) holds everything

**Verdict.** Collapse to **one physical DB** — SQLite with `sqlite-vec` (vectors) + `FTS5` (keyword) —
holding exact edges + vectors + full-text. The "relation store" and "semantic store" (D15) become **two
logical table-sets in one SQLite**, not separate databases. Supersedes D13's two-store split. **Retire
LanceDB** pending an Oracle recall bake-off (`sqlite-vec`+Qwen3 vs LanceDB+Qwen3); pass → LanceDB
removed → true single DB.

**Rationale.** User preference: one DB over many. SQLite+sqlite-vec is the only **mature in-process**
engine doing **both** graph (recursive CTE) **and** vector+FTS — `zvec` lacks graph; DuckDB's vector is
experimental; multi-model graph DBs are abandoned. **Bonus: one file = one ACID transaction → the
cross-store atomicity problem (D13) disappears.** **Price:** `sqlite-vec` ANN is brute-force/IVF (not
HNSW/DiskANN) — acceptable at our scale, and the post-retrieval Qwen3 reranker compensates. **Scale
trigger to revisit:** if the Oracle corpus outgrows brute-force *speed*, add a dedicated vector engine
(`zvec`) as a second store behind the Index port (D14) — a localized swap, accepted only then. The
Index port means single-vs-multi-store is never a caller-visible change.

**Quality evidence (2026-06-19).** sqlite-vec is **exact brute-force = 100% recall** (the ground truth);
LanceDB is **approximate** (head-to-head recall@10: 1.00 vs 0.96; quantization degrades it further; issue
#1428). RAG answer quality is dominated by the embedding model + reranker and is near-flat across recall
0.4→1.0. So single-DB on sqlite-vec is **quality-justified, not a compromise**; the only open check is
whether the Oracle corpus is large enough that exact-search *speed* fails (a scale check, not quality).
Detail: [17-codeplane-substrate-bakeoff](17-codeplane-substrate-bakeoff.md) "Quality evidence".

**DuckDB note.** DuckDB is **not** the transactional core: our hot path is many small per-entity upserts
(**OLTP** — SQLite's fit), whereas DuckDB is **OLAP** (bulk/analytical; single-row updates are its weak
spot), and its graph (DuckPGQ) + vector (VSS) extensions are *experimental* (VSS persistence "not
recommended in production") — currently *less* production-ready than sqlite-vec. DuckDB earns a place
only as an **optional adapter behind the Index port (D14)** for two roles, if/when wanted: (1) a
**data-lake query-in-place** mode over git-tracked Parquet/JSONL (embedded "Athena" — trades
human-readable OKF truth for columnar files); (2) an **analytics/reporting lens** (cross-run rollups its
columnar scans handle far better than SQLite). Not the default; decided later if a need appears.

## D17 — two engines (Manifest + Indexer); "planes" are data categories, not engines

**Correction.** An earlier draft conflated "knowledge plane" with the manifest. Fixed: the **manifest is
pure structural data (relation plane) — NO vectors**; the **knowledge plane is strictly knowledge +
lessons** (the Oracle corpus — semantic, embedded).

**Verdict — two engines (CQRS write/read split):**
- **Manifest engine** (a.k.a. state engine) — the **write-model**: owns all governed documents as files
  (truth, git) and ALL filesystem read/write + CRUD (create/edit/delete/supersede).
- **Indexer engine** — the **read-model**: builds the derived index from the files and serves all
  queries (the D14 `Index` port). The only component that touches the store.
The boundary is a single sync/notify call (Manifest mutates a file → Indexer updates the index). No
overlap: one owns truth+FS, the other owns index+query.

**Planes are data CATEGORIES (what), not engines (who):**
- **relation plane** = the manifest's structural nodes+edges (FKs). **No vectors.** Graph index
  (SQLite + CTE); exact/keyword lookup.
- **knowledge plane** = knowledge + lessons (Oracle). **Semantic, embedded** (vectors).
- **code plane** = code symbols/edges (structural, SCIP) + code semantic search (vectors).
The manifest is **never embedded** — semantic entry comes from the knowledge/code plane, then you cross
into the manifest's structural graph and traverse exactly. The Indexer engine internally maintains
whichever index kinds the planes need (structural graph + vector), hidden behind its port (D14).

**Is it abstract enough?** Yes — two engines is the minimal, non-overlapping decomposition (truth-I/O vs
index-I/O = write-model vs read-model). The planes live *inside* the indexer as index kinds; they are
not additional engines, which is what removes the earlier overlap. Source of truth stays the files
(git); vectors apply to the knowledge/code planes only, never the manifest.

## D18 — node lifecycle: edit / delete / supersede, with a `status` and append-over-destroy

**Verdict.** Every node carries a `status` (`active` → `superseded` | `deleted`). The three
mutation-over-time ops, all routed through the Index middleware with closure re-checks:
- **edit** — governed re-write of the **same id**; identity preserved so inbound edges stay valid;
  fmt+lint re-validate; git diffs the one file.
- **delete** — **never hard-delete a node with dependents** (closure blocks it — would create phantoms);
  default is a **tombstone** (`status: deleted`, retained for audit); git keeps history.
- **supersede** — create the successor + `supersedes` / `superseded_by` edges (provenance `asserted`);
  old node → `status: superseded` (kept); children re-pointed via migration; the supersession is a
  queryable fact.

**Rationale.** In a git-tracked, audit-required, referentially-integral system you **favor append +
`status` + supersede over destructive mutation/delete** — silent edits/deletes are exactly how
orphans/phantoms and lost decision-lineage return. Reuses existing UACP edge families (`rolled_back_to`,
`promoted_to`, `inherits_from`) and `status` enums. Flows in [19a-operational-flows](19a-operational-flows.md) §7–9.

## D19 — what to index / embed / store-in-vector-DB: **index by access pattern**

**Verdict.** Three retrieval modes = three index kinds, all in the one SQLite: **graph** (edges + CTE,
for relationships), **keyword** (FTS5, for exact text), **vector** (sqlite-vec, for meaning). Assign each
piece of data by *how you will retrieve it*:

- **Indexed structurally (graph [+ keyword])** — everything navigated by identity/relationship: **all
  manifest nodes + edges**, **code symbols + edges** (SCIP), and **knowledge/lesson metadata** (ids,
  tags, provenance). The manifest lives *only* here.
- **Embedded** — only free text retrieved by *meaning*: **knowledge + lessons** (bodies), **code
  text/docstrings** (optional), and **queries** (transient, not stored). **Never the manifest.**
- **In the vector DB (sqlite-vec)** — the persisted embeddings of the above (knowledge/lessons [+ code
  text]). The manifest is **absent**.

**Litmus per item:** "how will I retrieve this?" → by key/link = graph; by exact name = FTS; by rough
meaning = vector. **The manifest is structural-only because you always reach it by traversal** — its
semantic entry is opened by the knowledge/code plane, then you cross into the structural graph. Vectors
get you *to* the door, never *inside* the manifest.

**Rationale.** Separates the three concerns that kept getting conflated (indexing ≠ embedding ≠
vector-store). Embedding structural data is wasteful and meaningless — a node's "meaning" is its edges.
Keeps the manifest deterministic and the vector DB small/relevant.

---

# Council remediation (2026-06-20) — D20–D27

These decisions adopt the 6-lens council review ([21-council-review](21-council-review.md)). They
trim v1 to the validated serialization core and fix the convergent correctness gaps.

## D20 — Re-scope Slice 1 to a minimal in-memory vertical (council T6)

**Verdict.** Slice 1 = ONLY: (a) the two keys `scope_item.id` + `work_unit.derives_from` (**clean break —
no compat-shim, per D32**); (b) an **in-memory projector** (~100–200
lines: glob OKF files → dict of nodes/edges); (c) the closure checks run on **today's** fixtures
(auto-demonstrates the seam); (d) `_index.yaml` made derived/optional (D21); (e) real validate-on-write
(D25). **No SQLite, no Index port, no sqlite-vec, no schema/lint/fmt packages, no entity re-layout beyond
the keys.** **Rationale.** Per-run data is tens–hundreds of nodes — fits in RAM; the dict projector proves
the entire thesis with zero new infra and zero substrate decisions to regret. Supersedes the old Slice 1.

> **Amended (final-review T4 + D32):** v1 is reframed as a **manifest schema fix + a read-only closure
> projector** (= "Phase A", which the spike has largely done). The entity-level writer + formatter +
> validator + **Guardian raw-write block** + validate-on-write enforcement is **Phase B** — the real
> bottleneck (Codex), and the graph is not trustworthy until raw manifest writes are actually blocked.
> The `scope_item.id` migration is a **clean break, no compat-shim** (D32) — the spike proved the keyed
> `in_scope` PASSES the real `validate_proposal` (scripts/validate_uacp_artifacts.py:438).

## D21 — Truth is the per-node files; `_index.yaml` and SQLite are both DERIVED (council T1)

**Verdict.** **The source of truth for structural data is the per-node OKF files** — each node owns its
outbound edges in its own frontmatter (`wu-2.md` → `derives_from: [si-1]`); the edge is true because the
*child node* declares it. Truth is **distributed across the node files**, not centralized. `_index.yaml`
(members/edges/coverage) and SQLite are **both derived projections**, each reproducible from the files,
**neither authoritative**. The child frontmatter key is canonical; `_index.yaml` is regenerated by
`uacp-fmt` and in the minimal v1 (D20) can be **dropped entirely** (the projector globs node files);
reintroduce it later only as a committed derived snapshot for git-diff readability. Add closure check
**`index-consistency`** (any `_index.yaml` / SQLite must reproduce from the node files, else BLOCK).
**Rationale.** Removes the redundant 2nd/3rd source of truth (frontmatter + `edges` + `coverage`); makes
concurrent writes commutative/race-free; eliminates the aggregate-rewrite blast-radius D3 killed but
`_index.yaml` reintroduced.

## D22 — Index/Indexer is query-only; CQRS one-directional (council T2)

**Verdict.** The Index port answers questions and is **side-effect-free**. The *decision* (block a delete,
advance a phase) belongs to the Manifest engine / Guardian / Heartgate consuming the answer — never the
Index. Manifest→Indexer sync is one-directional (notify); read-backs are the Manifest engine *querying*
the port. **Rationale.** Fixes the read-model write-veto + closure-copy leak; restores the write/read
separation D17 claims.

## D23 — Provenance enforced per rel_type; existence ≠ correctness (council T3)

**Verdict.** `uacp-schema` carries a **closed per-`rel_type` provenance map** (`derives_from→asserted`,
`relates_to→inferred`, `calls`/`code_anchor→parsed`, FK rels→`derived`); validation REJECTS any edge whose
provenance violates it. Closure proves *coverage topology*, NOT semantic correctness of an `asserted`
edge's dst — stated explicitly in 10-edge-schema. Add checks **`forged-parsed`** (a `parsed` edge SCIP
can't reproduce) and **`contradicted`** (a `pass` assessment whose evidence is `fail`/`violated`). Any
change to an `asserted` edge's dst **re-triggers council**, not just closure. **Rationale.** Provenance is
producer-serialized and forgeable; the deterministic plane must not traverse a forged-as-hard soft edge;
judgment edges must not be silently rewritten after the one gate that checks them.

## D24 — Watermark-gated closure; STALE = BLOCK (council T4)

**Verdict.** Every closure query carries the current FS/git content hash; if `index.watermark != fs.hash`
the Index MUST rebuild-then-answer or return **STALE**, and Heartgate treats STALE as **BLOCK** (never
PASS). The index path is added to Guardian's protected-write set (no hand-edit under a run).
**Rationale.** A governance gate must never PASS off a stale/divergent index; closes the FS→DB window and
the hand-edit vector.

## D25 — Validate-on-write is real, unbypassable, net-new Slice 1 (council T5)

**Verdict.** Validate-on-write is **NOT yet built** (today's Guardian checks tool/path/context, never
content; `config/state.yaml`: "enforcement not yet implemented"). It is a named Slice-1 deliverable. The
entity-writer must be the **ONLY** path that writes a manifest file, and Guardian MUST block any raw write
(Write/Edit/`uacp_artifact_write` blob) targeting a manifest path. All bundle text describing Guardian
content-validation is **target-state**, not current. **Rationale.** Without closing the raw-write path,
validate-on-write is advisory and every downstream closure runs over a graph that may already contain a lie.

## D26 — New closure checks + boundary corrections (council, multiple)

**Verdict.** The integrity report gains: `index-consistency` (D21); `provenance-per-rel-type` +
`forged-parsed` + `contradicted` (D23); **`stale-reference`** (an active node with a hard edge to a
`superseded`/`deleted` dst); **`deleted-with-open-obligation`** (no tombstone/supersede of a node carrying
an unsatisfied obligation without a recorded waiver — **tombstones stay visible to closure**);
**`duplicate-id`** (PK-uniqueness backstop; ids become ULID/locked-mint, `wu-2` is a human label).
Boundary naming: the **run** is the closure/consistency boundary; the **aggregate** is the
write/transaction boundary. `code_symbol` is a **distinct identity regime** (repo-scoped, parser-resolved,
git-lifecycle), not governance-plane minting. **Rationale.** Closes supersede lineage-rot, tombstone
obligation-evasion, id races, the decorative-aggregate claim, and the code-id exception.

## D27 — Quality-evidence re-anchored; stale facts refreshed; defer the speculative layers (council T7/T8 + Devil)

**Verdict.**
- **Quality:** DROP the "RAG quality near-flat across recall 0.4→1.0" claim and **verify-or-remove** the
  arXiv 2606.04522 cite; re-anchor solely on "sqlite-vec is exact ⇒ 100% recall ⇒ strictly ≥ any ANN." The
  LanceDB-retirement gate is **3-axis**: filtered recall@k (plane/run-scoped) + p95 latency at projected
  size + independent rebuild cost (code re-index must not re-embed Oracle).
- **Facts:** LadybugDB ≈v0.17 + a live `Vela-Engineering/kuzu` fork — the embedded graph+vector option is
  NOT dead; SQLite chosen for zero-abandonment + zero-install, not inevitability.
- **Reconcile** `14-projection-engine` to D16 single-DB (its two-store/LanceDB-as-live-backend text is
  superseded; D11/D13/D15 are historical, not live contract).
- **Defer (extract-from-working, not build-ahead):** the Index port (D14) as a *v1 deliverable*, the
  SQLite/sqlite-vec substrate, schema/lint/fmt as *separate packages* (one pure-leaf module in
  `engines/domain` until an external consumer needs `pip install`), the constraints/metrics plane (D7), and
  the code plane (D5 original — keep deferred until real usage demands it).

**Rationale.** Aligns claims with evidence, de-risks substrate via the port-when-needed, and trims v1 to
the durable serialization core the whole council validated.

## D28 — the aggregate is itself a node; an OKF *profile* with canonical-vs-derived fields (refines D21)

**Context.** D21 said "node frontmatter is canonical; `_index.yaml` is derived" — but `_index.yaml` holds
fields that derive from no member: `kind/title/status/governance/scope/origin` describe the *collection*,
not any node. They cannot be derived; they are aggregate-intrinsic.

**Verdict.** The aggregate is **itself a node**. `_index.yaml` is therefore two zones: **canonical** for
the aggregate's own intrinsic fields (status/scope/governance/…), and **derived** for the
member-collection fields (`members` = glob the dir; `edges` = collect each node's `edges:`). D21 refines
to: *each node — including the aggregate — is canonical for its OWN data + outbound edges; only the
collection/mirror fields are derived.* The two zones are marked so `uacp-fmt` regenerates the mirror and
preserves the intrinsic.

**Format = extended OKF, not a new standard, not llm_wiki.** Formalize a **UACP OKF profile** in
`uacp-schema` = OKF (markdown + YAML frontmatter, per-dir aggregate) **plus**: (1) typed outbound
`edges:` with `rel_type`+`provenance` in node frontmatter (the relation layer plain OKF lacks); (2) the
aggregate as a first-class node (frontmatter = intrinsic truth; `members`/`edges` = derived mirror —
aligns with OKF's `index.md` per-dir convention); (3) a canonical-vs-derived field convention. **Reject**
a new from-scratch standard (OKF is adopted, git-friendly, human-readable) and **reject** llm_wiki (its
relations are wikilinks + relevance weights = the soft model rejected for the relation plane; its only
useful idea, `sources:` provenance, we already have). The profile *is* what `uacp-schema` encodes — a
documented extension, not a separate format to maintain.

**Rationale.** Resolves "how do the non-edge pieces derive?" — they don't; they are aggregate-intrinsic
and the aggregate owns them. Keeps OKF rather than inventing or importing a format.

## D29 — Structural = plain YAML + in-memory; semantic = LanceDB; no sqlite-vec, no structural DB (supersedes D16)

**Context.** D16 consolidated everything into one SQLite, justified by **co-location** of edges + vectors
("one store, free atomicity"). D20/D29 put the **structural plane on plain YAML files + an in-memory
projector** (no SQLite) — so there is **no SQLite for the edges to co-locate vectors with**. The single-DB
rationale evaporates.

**Verdict.**
- **Structural / relational plane:** plain YAML files (truth) + in-memory projection. **No database.**
  Tens-of-ms per run; trustless by construction (every read re-derives from truth — no standing index to
  verify). Performance/complexity analysis: same O(V+E) class as SQLite; the gap is ~5 ms vs ~50 ms per
  run, below the bar to add a DB. (SQLite is a **deferred scale-triggered cache**, never pre-adopted; if
  added, it is a cache not a source and gates re-verify against truth — D24.)
- **Semantic plane** (knowledge/lessons + code search): **LanceDB** — the existing, locked, baked-off
  Oracle store (BGE-M3 + Qwen3 reranker), disk-native, scales better than `sqlite-vec` brute-force as the
  corpus grows. Used for *new* semantic needs (code search) too.
- **`sqlite-vec`: NOT adopted.** Its only advantage was co-location, which is gone. **D16's "retire
  LanceDB" is moot** (it was contingent on the abandoned consolidation).
- **Do NOT pre-adopt `sqlite-vec` "to reserve SQLite."** YAGNI: it pays a real rip-out + re-validation cost
  now for optionality that's cheaply purchasable later (the Qwen3 reranker is store-agnostic; the vector
  backend is swappable). Buy it if/when the structural scale trigger fires.

**No cross-store atomicity cost** (the worry that drove D16): structure (manifest) and vectors (knowledge
corpus) are different planes on different data — the manifest is **never embedded** (D19) — so there is
nothing to keep atomic between the two stores.

**Rationale.** Once structure is plain-files, the single-DB consolidation has no justification; the vector
store reverts to the incumbent LanceDB, and `sqlite-vec` loses its reason to exist. Simplest *and* most
trustless: files for structure (recomputed from truth), the existing vector store for semantics (a
separate plane that never gates governance).

## D30 — the context loop: grounded extraction at RESOLVE + phase-keyed injection + consolidation = node lifecycle

**Verdict.** The knowledge plane is **context, not memory**: durable artifacts distilled *from* the
manifest and anchored to it by `derived_from`. Three timescales — **in-flight capture** (run-local
`observation` nodes, cheap/low-trust), **RESOLVE distillation** (typed `fact`/`lesson`/`procedure` nodes,
grounding REQUIRED, reconciled vs corpus as NEW/PROMOTE/SUPERSEDE — the **2nd judgment seam**, symmetric to
PROPOSE→PLAN), and **cross-run consolidation** (episode→pattern→rule via `promoted_to`, gated). **Injection
is phase-keyed by tier**: rules eager at TRIAGE, patterns (filtered by topic) at PROPOSE/PLAN, episodes
(by situation, JIT) at EXECUTE. **Embed only retrieve-by-meaning artifacts** (facts/lessons/patterns) into
LanceDB (+FTS); **rules are eager-loaded, never embedded**; the manifest is never embedded. **Partition**
by plane + eager-vs-retrieved; **tag** by type/tier/domain/status/recency as filter columns (retrieval is
*filtered*, council F2). The artifact **lifecycle reuses D18** (create→promote→supersede→tombstone);
**contradiction management = supersede by evidence strength**. Full spec: [22-context-loop](22-context-loop.md).

**Rationale.** Closes the loop (consume→capture→distill→consolidate→re-inject) using machinery already
defined (nodes, edges, provenance, D18 lifecycle, D19 access-pattern, D29 LanceDB). Grounding keeps the
knowledge plane trustless (every claim traces to evidence); the typed/tiered/tagged extraction keeps
retrieval filtered and the corpus self-correcting via supersede.

## D31 — the feasibility spike IS the BRAINSTORM phase; pattern: spike → grounded evidence → PROPOSE viability

**Verdict.** A PoC / feasibility spike is **not a new phase** — it is the **BRAINSTORM-phase activity**
(UACP's optional pre-governance exploration that precedes TRIAGE). The Slice-1 spike
(`spike/projector.py` + `spike/findings.md`) **is** this initiative's brainstorm step. Its grounded
evidence flows: BRAINSTORM (spike) → TRIAGE (routing) → PROPOSE (`viability: viable` — rationale cites
`findings.md`) → PLAN (the migration-surface finding informs the compat-shim). `findings.md` is the run's
**brainstorm evidence**. **Reusable pattern:** *de-risk with a read-only spike before committing to
governance; the spike's grounded findings become the proposal's viability evidence.*

**Rationale.** Gives the PoC a proper existing home in the lifecycle, keeps evidence grounded + linked,
and dogfoods the brainstorm→propose flow. (Formalizing "feasibility spike" in canonical
`docs/lifecycle/` is a follow-up *governed* change — not done unilaterally; canonical docs need council.)

## D32 — pre-production → clean break, no compat-shim; council Integration-F2 retired

**Verdict.** UACP is **pre-production** (no external users; runtime Guardian/Heartgate enforcement not yet
implemented; existing manifests are **test fixtures**). So there is **no backward-compatibility
obligation**. Slice 1 does a **clean break**: `scope_item.id` + `work_unit.derives_from` become the new
canonical form — **no dual-format shim**. Verified on real source (main): the only code reader of
`in_scope` (`validate_uacp_artifacts.py:438`) is a pure **key-presence** check that survives any item-shape
change; `phase_transitions.py:183` is a description string, not enforcement. Old fixtures correctly read as
`uncovered`/`orphan` by the new checks (accurate — they predate the keys); **no migration script
required**. **Council Integration-F2 (compat-shim) is RETIRED**; Slice 1 shrinks accordingly.

**Rationale + proof.** A shim is dead weight without users/data to protect. Proven end-to-end in the spike:
the projector now reads **both** forms — legacy run = 9 uncovered / 2 orphan / 0 edges (broken), new-form
fixture (`spike/fixtures/oauth-login/`) = **0 uncovered / 0 orphan / 3 `derives_from` edges (CLOSED)**. The
two keys fix the seam.

## D33 — knowledge attribution: grounding ≠ authorship; an `attribution` block + a `portability` transfer axis (knowledge plane, deferred)

**Context.** The design grounds knowledge artifacts by `derived_from` (*why is this true* → run evidence).
A second, distinct provenance axis was missing: **attribution** (*who/what asserted it, under what
conditions*). For AI-generated knowledge "author" is multi-dimensional; each layer is a different trust/
transfer signal.

**Verdict.** Add an `attribution` block to knowledge-plane artifacts (EXTENDS the as-built
`Lesson`/`KnowledgeItem` — does NOT fork it):
```yaml
attribution:
  generated_by: { agent: <id>, model: claude-opus-4-8, runtime: hermes }  # NET-NEW
  authorized_by: <operator>     # REUSE authority.requested_by
  source_run: <run_id>          # REUSE (exists in corpus)
  project: <repo/project id>    # NET-NEW (ownership)
  portability: project-local | transferable | universal   # NET-NEW — the transfer axis
  # domain/tags + created_at: REUSE existing tags + git
```
- **Git reuse — one layer only.** Git supplies commit author + timestamp + content-hash + history *for
  free* → reuse for the **commit-lineage** layer; do NOT duplicate it into frontmatter. But the **git
  author is the committer (operator/CI), NOT the generating agent** — git cannot see agent/model/runtime/
  scenario, so those live in frontmatter. Two layers, no overlap.
- **Transferability (the prize, the `portability` axis).** `portability` turns "does this knowledge apply
  to a NEW project?" into a deterministic **filter** (`portability != project-local AND domain matches`),
  not a guess. `project-local` = grounded in this repo's specifics (a schema, a path) → does NOT transfer;
  `transferable` = domain knowledge ("OAuth account-linking risk") → transfers within a domain;
  `universal` = validated across N projects → transfers anywhere. Composes with the tier ladder (D30):
  `episode`=project-local by default; a cross-run-validated `rule` promotes toward `universal`.
  **Tier × portability = the transfer gate** — how a lesson graduates from owned-by-one-project to shared corpus.
- **Attribution is descriptive, never a trust override.** `generated_by.model` does not make a claim more
  true — grounding (`derived_from`) still does the proving. Model attribution is a historical fact (what
  produced it *then*), never rewritten; supersede if re-derived.

**Scope.** Knowledge-plane only (the manifest is not "authored knowledge"); **deferred from v1** with the
rest of the context loop (D30). Required net-new = `generated_by` + `project` + `portability`; everything
else reuses `source_run`/`authority`/`tags`/git. Promotion to `universal` needs validation across ≥N
projects (same evidence-gate discipline as tier promotion). Risks: mis-tagged `universal` pollutes other
projects → gate it; attribution-as-boast → it's metadata, never overrides grounding; over-tagging → only
`portability`+`generated_by` required.

## D35 — phase-keyed structural gates: run the seam check at EACH transition, not only at terminal closure

**Context (verified vs `core.py`).** Today `validate_transition` (line 761) enforces `phase_exit_invariants`
(line 823→1097) which check **artifact/ledger EXISTENCE only** — never graph STRUCTURE. The structural
seam engine `graph_projection` (uncovered/orphan/phantom/contradicted) is invoked ONLY by
`validate_closure` (line 893) at terminal RESOLVE. **Consequence:** a dropped intent at PROPOSE→PLAN is not
caught at that boundary — it surfaces 4 phases later at closure. **A structural gate is missing at each
phase transition.**

**Verdict.** Make the structural checks **phase-keyed**: each fires (as a BLOCK) at the transition where
its inputs first exist and must be complete; informational before that:

| transition | structural gate enforced |
|---|---|
| PROPOSE→PLAN | `uncovered` (every scope_item has `derives_from`), `orphan`, `phantom` |
| PLAN→EXECUTE | every work_unit has an evidence_obligation |
| EXECUTE→VERIFY | every work_unit/obligation has a checkpoint |
| VERIFY→RESOLVE | `unverified` (passing assessment), `contradicted` |

This is the concrete form of the T2 "phase-aware closure" finding (each check has a *phase-of-enforcement*,
not just structural-vs-progress). **Mechanism already exists** — `phase_exit_invariants` is config-driven
per `stages.<phase>`; add a new **`graph_invariant` kind** alongside the existing artifact-glob/ledger
kinds, and have `validate_transition` run the phase-scoped subset of `graph_projection`. **No new engine** —
re-use the Phase-A engine, scoped per transition.

**Scope.** Next increment after Phase A (graph_projection currently terminal-only). It is what turns "the
seam is *checkable*" into "the seam is *gated early*". Depends on runtime actually invoking
`validate_transition` at transitions (the broader "enforcement not yet implemented" gap).

## D34 — code plane: evaluate adopting `codegraph` over a custom SCIP build (amends D12; deferred)

**Context.** D12 / node-17 specced the deferred code plane as a custom **SCIP** (symbol-precise) indexer
+ **SQLite** store. `github.com/colbymchenry/codegraph` (assessed 2026-06-20) is a packaged realization of
almost exactly that shape: a pre-indexed **code knowledge graph** via **tree-sitter AST + cross-file
symbol resolution** (calls→defs, imports→sources, extends/implements), stored in **SQLite + FTS5**,
**embeddable in-process + MCP server**, 20+ languages, **MIT**, ~52k stars, v1.0 active, **built for AI
coding agents incl. Hermes Agent** (UACP's runtime).

**Verdict.** When the code plane is built, **evaluate adopting codegraph instead of a custom SCIP
integration** — lean adopt. It satisfies every D12 constraint (symbol-precise, SQLite, embedded/MCP,
permissive, agent-oriented) off-the-shelf; building bespoke would be NIH. **One gate before committing:**
verify its resolution is **precise enough to anchor a task→symbol+lines** — D12 preferred SCIP precisely
because tree-sitter *alone* was "too coarse" for cross-file resolution; codegraph adds a resolution layer
on top, but heuristic resolution is less rigorous than typecheck-grade SCIP for ambiguous cases
(overloads, dynamic dispatch). Bake codegraph vs SCIP on a real repo for anchor-precision before locking.

**Rationale.** A 52k-star MIT in-process code-graph designed for the exact runtime, matching our store
(SQLite) and constraints, likely **supersedes the "build SCIP custom" path** — but it is the **deferred
code plane** (not v1), so this is "leading candidate, verify-at-build-time", not an adoption now. Note: if
adopted, codegraph's own SQLite is the CODE plane's index — it does NOT change the manifest plane
(D29: plain-files + in-memory, no DB); the two planes stay separate.

**Storage + LSP internals (verified 2026-06-20).** codegraph is **SQLite-only — NO vector DB, NO
embeddings**: symbols + edges as relational tables + FTS5 keyword; retrieval is **exact graph traversal +
keyword**, deterministic, not vector-ANN. This **independently validates D19/D29** (structure = exact graph,
never embedded; vectors only for fuzzy) — a 52k-star code-intelligence tool made the same call.
**vs LSP:** codegraph is NOT an LSP and uses none — edges are tagged `provenance:'heuristic'` (tree-sitter
+ a resolution pass), honest ceiling ~83% on convention-heavy frameworks (ASP.NET/Spring), misses dynamic
dispatch. Three shapes for the code plane: **LSP** = typecheck-precise but on-demand/stateful, NOT a
dumpable graph (wrong shape for a persistent index); **codegraph** = persistent SQLite graph + MCP, ready,
but heuristic precision; **SCIP** = pre-built persistent AND typecheck-grade (SCIP indexers wrap the same
typecheckers LSP uses, serialized in one shot). So the bake-off (above) is concretely **codegraph
(heuristic, packaged) vs SCIP (typecheck-grade, build-it)** — and for UACP's actual need (anchor a
checkpoint to a symbol+line on a concrete edit), tree-sitter nails the common case; the heuristic ceiling
bites call-graph *completeness*, not *which-symbol-did-this-edit-touch*, so codegraph is plausibly
sufficient for anchoring. Decide at build time on real repos.

## D36 — the code plane is for PREVENTION at PLAN, not validation at VERIFY; edges carry confidence; context is phase-keyed (deferred)

**Context (Trustless lesson).** In a growing codebase the failure family is not *validation* (checking
after) but *prevention*: the agent plans **blind to the existing wiring** → ungrounded schema refs, scope
explosion, "margin trading before the order book." So the code plane's highest value is a **PLAN-side
context source** ("what exists, what depends on what, what will I touch/break?"), at the FRONT of the
lifecycle — not a VERIFY-side gate. (A bigger context window does not give this — dumping files ≠ knowing
the wiring; you need the *structured* dependency graph, deterministically.)

**Consequences for the substrate choice (refines D34):**
1. **Prevention wants COMPLETENESS** — a missed dependency is an unforeseen break (the exact thing being
   prevented). codegraph's ~83% heuristic ceiling bites here (missed edge = unseen blast radius); SCIP's
   precision serves prevention. But SCIP is narrow (precise on some files, blind on the rest in a polyglot
   repo), so "approximate coverage of everything" (codegraph) can beat "precise coverage of some + blind
   elsewhere." → the **hybrid / degradation ladder is *motivated by prevention*, not just convenience**:
   SCIP-precise for the major-language core, codegraph-heuristic for breadth, the `code_anchor` floor
   (file+symbol+line from the diff — language-agnostic, needs no indexer) for the intent→code link.
2. **Surface edge CONFIDENCE via provenance.** A codegraph edge is `provenance: heuristic`; a SCIP/LSP edge
   is `provenance: parsed` (precise). The planning agent must KNOW "this *might* depend on X (heuristic)"
   vs "*definitely* (precise)" — it calibrates planning risk. This is the manifest's provenance discipline
   applied to code understanding: the agent plans with trust-awareness, never treating a guess as fact.

**Phase-keyed code context (parallel to D30 knowledge injection):** PLAN → inject wiring + blast-radius of
what the intent touches (**prevention**, the high-value use); EXECUTE → navigate locally + record the
`code_anchor` (tracking); VERIFY → did the wiring break / dangling refs / broken callers (validation,
secondary). The agent understands code by **querying the structured wiring at the phase where it matters**,
confidence-tagged — not by reading files into context.

**Scope.** Deferred code plane. All of LSP/codegraph/SCIP are EXTERNAL deps (UACP owns the `code_anchor` +
the edge/provenance contract, never an indexer; skills reference the tool). The framing is load-bearing for
when the code plane is built: front-load for prevention, hybrid-by-coverage, confidence-by-provenance.

## D37 — the indexer is a CROSS-CUTTING layer, not a sibling plane; SCIP & codegraph are both index-first (clarifies D14/D17/D34)

**Insight (refines the topology).** "Indexer plane" was a misnomer. There are **content planes** (WHAT) and
**one indexer layer** (HOW) that cuts across them:
- **content planes** — each = *(files = truth) + (an index)*: **manifest/relation** (index = in-memory
  node/edge graph), **knowledge/doc** (index = LanceDB vectors), **code** (index = SCIP/codegraph SQLite).
- **indexer** = the shared mechanism **project content → deterministic index → query it**, spanning all
  content planes, with a **plane-specific backend adapter** (in-memory / LanceDB / SCIP-SQLite). This IS
  the Index engine / Index port (D14) seen correctly: ONE projection+query layer, THREE contents, THREE
  adapters. The same "serialize → project → query" discipline is identical across manifest (edges→graph),
  code (symbols→graph), knowledge (text→vectors) — one mechanism, three contents (the unification).

**Code-indexer framing corrected (amends D34).** The map/GPS metaphor blurred the mechanism. Precisely:
**LSP** parses **live** per-query via a server; **SCIP** **indexes the whole codebase first, then queries
the index** — and *that index-first model is exactly UACP's pattern*, so SCIP is architecturally aligned.
BUT **codegraph is ALSO index-first** (builds SQLite, then queries) — so index-first is NOT the
differentiator; both fit. The only real difference is index-BUILD: SCIP = typecheck-precise, per-language
indexer (`scip-go`+`scip-typescript`+…; "coverage = which indexer package you install"); codegraph =
tree-sitter, one broad tool, heuristic. **Genuine either/or, decided at build time** — NOT "codegraph
primary" (D34's earlier lean is softened). LSP stays out: live-parse is the wrong shape for a persistent
queried index. Deferred — pick at code-plane build.

## D38 — do NOT consolidate the per-plane stores; one index file per plane, partitioned by lifecycle (locking rationale; reaffirms D29)

**Question (recurring).** SCIP brings its own SQLite → should we roll LanceDB into it / merge into one
shared SQLite (sqlite-vec) so everything is one DB?

**Verdict. No — keep one index file per plane, separate.** Three reasons:
1. **SCIP's SQLite is the TOOL's file, not ours** — a rebuildable artifact SCIP owns/wipes. Co-tenanting
   our durable knowledge vectors inside a third-party tool's index is fragile (it can rebuild it away).
2. **SQLite locks the whole DATABASE FILE, single-writer** (not row/table-level). Default journal: a write
   **blocks all reads** on that file; WAL helps (readers don't block the writer) but **writers still
   serialize**. Co-located, a heavy **code re-index** (big write) would block/serialize concurrent
   **knowledge vector search** in the same file. **Separate files = separate locks = zero cross-contention.**
3. **Different rebuild lifecycles** — code index rebuilds per COMMIT; knowledge index at RESOLVE. Co-locating
   couples independent cadences into one file (a code change touches the knowledge corpus's file).

**Therefore: keep LanceDB** (do NOT switch to sqlite-vec) — the only justification for that switch was
co-location (D16), which we are explicitly NOT doing; with no co-location benefit it just costs the rip-out
+ recall re-validation. D29 stands.

**Principle — one index file per plane, partitioned by lifecycle:** manifest = in-memory graph (per-run,
UACP) · knowledge = LanceDB (RESOLVE, UACP) · code = SCIP's own SQLite (per-commit, SCIP-owned, we query).
Separate files → isolated locks, isolated rebuilds, clean ownership. SCIP bringing a SQLite **reinforces**
separation, it does not pull toward consolidation.

## D39 — the three-layer stack: UACP is the SEMANTIC layer ABOVE SCIP; domain knowledge is STRUCTURAL (external validation + sharpening of D36)

**External reference (independent, ChatGPT, on Trustless's ~300k LOC).** Converges on D36 and frames it
cleanly. The agent's hardest question in a domain-heavy system is NOT "where is `Transfer()`?" (ripgrep/
LSP/SCIP all answer that) but **"why must it Journal → Settlement → Reconciliation, and which invariants
cannot break?"** — and **SCIP knows NONE of this.** Static analysis cannot derive domain ordering,
invariants, or capability dependencies; they come from architecture + domain knowledge.

**The stack:**
```
Source Code → LSP → SCIP → UACP Semantic Graph → Coding Agent
```
- **LSP** = live editing (autocomplete/rename/diagnostics) → gopls, tsserver. External; UACP does not own it.
- **SCIP** = static symbol graph (def/refs/impl/call-hierarchy). External; the code plane. Supporting, not the prize.
- **UACP Semantic Graph** = the prize: "this function is in the Settlement phase; modifying it requires
  checking Ledger invariants and re-validating the Reconciliation workflow." = our **manifest plane**
  (intent→task→impl) + **knowledge plane** + a **domain layer**.

**The sharpening (what this ADDS).** ChatGPT's "Layer 3" examples — workflow sequences (Journal *precedes*
Settlement), invariants (transaction *must balance*; settlement *only once*; reconciliation *idempotent*),
capability deps (Trading Engine *requires* Ledger+Registry+Identity) — are **STRUCTURAL, not semantic**:
they are typed edges (`precedes`, `requires`, `must_satisfy`), deterministic and queryable, **the same
relation-plane discipline (serialized edges) extended into the DOMAIN** — NOT fuzzy vectors. So domain
knowledge lives in the **structural/relation plane**, queried by exact walk ("what must hold before I
modify Settlement?" → walk the invariant/requires edges), and connects to SCIP via **`code_anchor`** (a
code symbol ←→ its domain-semantic node). This reuses existing/planned node kinds: `rule`/`prohibition`
(constraints plane D7) for invariants, `requires`/`precedes` edges for capability/workflow graphs.

**Consequence.** The code plane (SCIP) is **supporting infrastructure**; the **domain semantic graph is the
high-value layer** for domain-heavy systems (reaffirms D36: code plane = prevention support, not the
prize). Prevention at PLAN = SCIP (who-references-what, structural code) + UACP (what-must-hold / what-
depends-on-what at the domain level). Domain knowledge is **declared/authored architectural knowledge**
(plus run-distilled lessons), eager-loaded as rules (D30 tier). Deferred with the code plane + constraints
plane, but the framing locks UACP's position: **a semantic knowledge layer above SCIP, structural at its
core.**

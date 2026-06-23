---
type: design
title: "Oracle Retrieval Engine — Design"
description: "Design for a config-gated Python retrieval aggregator composing run-state lookup, semantic search, and Honcho memory"
tags: ["oracle", "retrieval", "semantic-search", "knowledge"]
timestamp: 2026-06-17
status: archived
---

# Oracle Retrieval Engine — Design

> Design doc C of three. A = brainstorm phase · B = lesson/knowledge corpus + distillation · **C = this**.
> Reads/writes the corpora defined in Doc B. Build after (or with) B.

**Goal:** A config-gated, in-repo Python **retrieval aggregator** that composes deterministic run-state lookup + semantic lesson/knowledge retrieval + Honcho memory, and injects ranked prior-art into the decision phases ("retrieval-led reasoning"). Models run **behind external OpenAI/TEI/Cohere-style HTTP endpoints**, not in-process.

**Status:** Approved in brainstorming dialogue 2026-06-17. Model picks verified by web research 2026-06-17 (see §Model stack).

---

## Architecture

```
                         uacp_oracle_query (governed, read-only)
                                     │
                      ┌──────────────┴───────────────┐
                      │   Aggregator (Python)         │   phase-tier gating · provider packets ·
                      │   engines/oracle/             │   trust classes · retrieval-led · caching
                      └───┬───────────┬───────────┬───┘
            deterministic │   semantic│           │ memory
                          ▼           ▼           ▼
                  run-state      lessons +     Honcho
                  (.uacp/<phase>) knowledge    (HTTP)
                  prefix/key      (.uacp/{lessons,knowledge})
                  lookup              │
                                      ▼
                              retrieval store (LanceDB)  ──► dense + FTS + RRF
                                      │
                          external model endpoints (HTTP, configurable URLs)
                          embed (/v1/embeddings) · rerank (/v1/rerank) · expand (/v1/chat)
```

Three composed tiers (per the agreed model):

| Tier | Corpus | Retrieval |
|---|---|---|
| **Deterministic** | manifests / run-state (`.uacp/<phase>/…`, registry, ledger) | by prefix/path/structured key (run_id, phase, goal_id, write_paths, gate decision). **No embeddings.** |
| **Semantic + deterministic** | lessons + knowledge (`.uacp/{lessons,knowledge}/`) | hybrid (dense + keyword) → RRF → rerank, **plus** tag filter + BES rank (lessons) |
| **Memory** | Honcho | memory API (operator/architectural prefs); read all phases, write prefs only at resolve |

## Per-phase gating (`tier_config.PHASE_TIERS`)

✚ retrieval-led (mandatory-before-reasoning when enabled) · ○ advisory · ✎ write-back · — none.

| Phase | Mode | Active sources |
|---|---|---|
| brainstorm | ○ | knowledge, lessons, run-history, Honcho prefs |
| triage | ○ | lessons, knowledge, run-history, scope-overlap, Honcho |
| propose | ✚ | lessons (domain), knowledge, run-history, Honcho arch-prefs |
| plan | ✚ | lessons (domain+invariant+file), knowledge, scope-overlap |
| execute | — | intra-run checkpoints only; exact plan |
| verify | ✚ | lessons (domain), knowledge, intra-run rounds, gate-ledger |
| resolve | ✎ | — (writes lessons; recompute BES; promotion check — Doc B) |

Each source is independent and **non-fatal**: a missing/unreachable source is logged to `sources_skipped`, never blocks. Sources return normalized **provider packets** `{source, trust_class, payload, evidence_required, repo_commit}` with **trust classes** (`authoritative_record` / `normative_reference` / `advisory_signal`) — advisory packets carry `evidence_required=true` so a phase can't treat a hint as proof. (All ported from Trustless ACP's `providers.py`/`tier_config.py`.)

## Retrieval pipeline (semantic tier) — QMD-shaped

The 2026 hybrid consensus (research-confirmed, high confidence) is exactly QMD's shape, so we replicate it:

1. **Query expansion** — ⛔ **RETIRED 2026-06-23** (see `docs/decisions/decision-log.md`). ~~optional; a small instruct LLM via the chat endpoint emits multi-query variants + conditional HyDE (gate on low confidence).~~ Removed: the role was never wired into the pipeline, and a small-model expander regresses recall on the BGE-M3 + Qwen3-Reranker stack; hybrid dense+FTS+RRF already supplies recall robustness. The pipeline now starts at step 2 (hybrid retrieve).
2. **Hybrid retrieve** — dense (BGE-M3 dense vectors) **+** keyword/lexical (FTS / BM25, or BGE-M3 sparse) in parallel.
3. **RRF fusion** (k=60) — robust, native in the store; beats learned fusion.
4. **Rerank** — cross-encoder/LLM reranker over fused top-N via the rerank endpoint.
5. **BES/tag overlay (lessons only)** — gate on concrete relevance (domain/invariant/file/intra-run), then blend BES bonus into the score (Doc B).

## Model stack (external endpoints — configurable, swappable)

**Decision: embedded default, URL override — per role.** Each role (embedding, rerank, query-expansion) runs its pinned model **embedded (in-process) by default**; configuring a **URL override** for that role uses the URL instead. Per role it's one or the other — **never both at once** (`url override > embedded default`). With the semantic layer disabled (or its runtime absent and no URL), the engine falls back to the **keyword + structured + BES floor**. The embedded runtime for the pinned GGUF models is an in-process llama.cpp binding (the Python analog of QMD's node-llama-cpp, which runs this exact model set) — exact runtime settled at implementation. This deliberately reverses an earlier URL-only lean: embedded-default makes semantic + rerank work **out-of-the-box** (no server to stand up — and rerank is the hardest thing to serve externally), with the URL override as the upgrade path to bigger/remote models.

Because models live behind URLs, these are **recommended defaults**, not hard deps. Research (2026-06-17) confirmed the picks; the binding constraint is **what each server can serve**:

**Servability matrix (plan the adapter around this):**
- **TEI** `/embed` (dense) + `/rerank` — but `/rerank` only serves *classic cross-encoder* rerankers (XLM-RoBERTa/BGE family); TEI uses its own `{query,texts}` shape, not Cohere's.
- **vLLM** — the most "just works": OpenAI `/v1/embeddings`, Cohere-compatible `/v1/rerank` (for LLM rerankers converted to seq-cls), and `/pooling` for sparse/ColBERT. BGE-M3 needs `--hf-overrides '{"architectures":["BgeM3EmbeddingModel"]}'` or it silently drops sparse/ColBERT.
- **Ollama** — easy dense embeddings + chat; **no native rerank endpoint** as of mid-2026.

**Pinned defaults** (specific models to serve behind the URLs — not just a family; all quantized, ~2.5 GB total, laptop-runnable):

| Role | Pinned default | Size (quant) | Ctx | License | QMD uses |
|---|---|---|---|---|---|
| Embedding | **BGE-M3** | ~1–2 GB | 8192 | MIT | EmbeddingGemma-300M-Q8 (329 MB) |
| Rerank | **Qwen3-Reranker-0.6B** | 639 MB (Q8) | 32k | Apache | same (Qwen3-Reranker-0.6B-Q8) |
| Query expansion | **qmd-query-expansion-1.7B** (credit: tobi/qmd) | 1.28 GB (Q4_K_M) | 32k | Apache (base) | same model |

- **Embedding — BGE-M3** (default): the only pick giving dense + sparse + ColBERT from one 8192-ctx encoder, MIT; no "M3v2" as of 2026-06. **Caveat:** TEI serves **dense only** — for the sparse/ColBERT legs use vLLM (`--hf-overrides …BgeM3EmbeddingModel`) or FlagEmbedding; *or* just take BGE-M3 **dense + the store's FTS/BM25** as the lexical leg (simpler, still hybrid). Lighter dense-only alternates: **EmbeddingGemma-300M** (329 MB, 2048 ctx — QMD's pick), **Qwen3-Embedding-0.6B** (639 MB, 32k, Apache), **Harrier-OSS-v1-0.6B** (MIT, 32k, no GGUF yet).
- **Rerank — Qwen3-Reranker-0.6B** (default). Reasons it beats the no-fuss bge pick: **(1) context** — 32k vs bge-reranker's ~512-token recommended cap; our lessons/knowledge are prose chunks that exceed 512, so bge would truncate before scoring while Qwen3 reranks the full chunk; **(2) quality** — newer top-tier reranker (MTEB-R; vendor-reported → validate via the bake-off below); **(3) consistency** — Apache-2.0, QMD's own pick, and same Qwen family as the embedder/expander alternates; **(4) serving cost is trivial on vLLM** (already our blessed server) — a one-time seq-cls conversion (`--hf_overrides …Qwen3ForSequenceClassification` or a pre-converted `…-seq-cls` checkpoint); the "no TEI support" downside doesn't bite when vLLM is primary. **Alternate: bge-reranker-v2-m3** — keep it for **TEI / zero-conversion** setups: a true XLM-RoBERTa cross-encoder TEI serves natively on `/rerank`, Apache, strong multilingual, but ~512-token practical cap.
- **Query expansion — qmd-query-expansion-1.7B** (default, *optional* — skip → raw query). **Credit: this model is from [tobi/qmd](https://github.com/tobi/qmd) (Tobias Lütke)** — a Qwen3-1.7B SFT emitting typed BM25/semantic/HyDE expansions at 1.28 GB; fit-for-purpose beats raw size. **Why not the big new models:** Gemma 4 E2B/E4B and Qwen3.6/3.7 are the **wrong tier** — Gemma 4 E2B = 2.3B-eff/5.1B-total (~7 GB, more reasoning than a rewrite needs), Qwen3.6's smallest *open* weight is **27B**, Qwen3.7 is **closed/API-only**. Small alternate (cleaner license, no CJK limit): **Qwen3-1.7B** (1.83 GB Q8). (qmd card license unstated — base is Apache, verify before commercial use; known limit: expands CJK queries to English-only terms.)
- **License watch-outs** (avoid for shipping): Jina-Reranker-v3 / Jina-embeddings-v5 = CC-BY-NC; NVIDIA Llama-Embed-Nemotron = non-commercial.

**Minimum-viable hardware:** ~2.5 GB weights total. **CPU-only laptop works** (8 GB RAM minimum, 16 GB comfortable; the 1.7B expander is the only slow-on-CPU piece — offload/disable first). **8 GB VRAM** holds the whole stack resident; **Apple Silicon 16 GB** unified is ideal; 24 GB only if co-hosting a large generation LLM. (Model sizes from HF cards; RAM/VRAM are engineering estimates — vendors publish no minimums for sub-1B models.)

**Server:** **vLLM** covers embed + rerank + sparse in one; **TEI + Ollama** works for the dense-only / classic-reranker path (Ollama has no rerank endpoint).

### Validation — empirical model bake-off (a plan step, not a paper pick)

The picks above are *paper-recommended* (specs + vendor-reported quality). Before they're final, run a **smoke-test bake-off** over a seed eval set and measure quality (nDCG@k / MRR on a small labeled query→doc set drawn from real lessons/knowledge) + p50/p95 latency across **scenarios**: short query vs long doc-chunk (the bge ≤512 cap should show here), multilingual/CJK, and exact-keyword vs paraphrase recall. Rerankers to compare: **Qwen3-Reranker-0.6B** vs **bge-reranker-v2-m3** (± mxbai-rerank-v2).

**Harness caveat — not Ollama for rerankers.** Ollama has **no rerank endpoint**, so it can't drive a reranker bake-off (it's fine for *embedding* smoke tests). Use one of: **TEI** (`/rerank`, for bge-class), **vLLM** (`/score`/`/v1/rerank`, for Qwen3 seq-cls), or a direct **FlagEmbedding / sentence-transformers** Python script (no server — simplest for a one-off bake-off). Blocker: this needs a **seed eval set**, which doesn't exist until runs produce lessons — so seed it with a handful of hand-labeled query→doc pairs (or synthetic) to bootstrap. Captured as an EXECUTE-phase step in the Oracle implementation plan.

## Store

**LanceDB** (embedded, no server) at `.uacp/knowledge/indexes/` — gives vector + FTS + **native RRF hybrid** + reranker hooks, so we don't hand-write fusion. Source of truth stays the per-file OKF docs (Doc B); the index is **derived and rebuildable**. Behind a thin store interface so **sqlite-vec + FTS5** remains a lighter swap-in if the LanceDB dep proves unwelcome (corpus is small enough that brute-force KNN suffices).

## Config (`[oracle]`)

```toml
[oracle]
enabled = false                      # off → keyword + structured + BES floor only
store = "lancedb"                    # | "sqlite-vec"
index_path = ".uacp/knowledge/indexes/"
cross_project_recall = false         # opt-in lesson recall beyond current project

# Per role: the model runs EMBEDDED by default; set `url` to override → use the URL instead.
[oracle.embedding]
model = "bge-m3"
url = ""                             # empty → embedded; else e.g. "http://localhost:8000/v1/embeddings"
api_key_env = "ORACLE_EMBED_KEY"     # URL mode only; secret from env, never in config

[oracle.rerank]
model = "qwen3-reranker-0.6b"
url = ""                             # empty → embedded; else e.g. vLLM "http://localhost:8000/v1/rerank"

[oracle.query_expansion]
model = "qmd-query-expansion-1.7b"   # credit: tobi/qmd
url = ""                             # empty → embedded; else e.g. "http://localhost:8000/v1/chat/completions"
enabled = true

[oracle.honcho]
url = "..."
enabled = true
```

## Degradation (per-role precedence: url override > embedded > floor)

- **Semantic enabled, no URL override** → run the **embedded** model for that role.
- **URL override set** → use the URL (vLLM / TEI / remote) instead of embedded.
- **Rerank disabled / unavailable** → skip rerank; return RRF-fused order.
- **No Honcho** → skip memory packets.
- **`enabled = false`** (or embedded runtime absent and no URL) → semantic off; engine serves the **keyword (store FTS) + structured run-state + BES** floor — today's direct-file behavior plus structured lesson ranking, zero models.

**Dependency note:** the embedded default pulls an **optional, lazily-loaded** in-process model runtime (a llama.cpp binding) + the pinned GGUF weights (~2.5 GB, auto-fetched) — loaded only when the semantic layer is enabled with no URL override. The **floor needs none of it**. LanceDB + an HTTP client (URL mode + Honcho) are the remaining deps. (This is the trade for out-of-the-box semantic — an in-process runtime, reversing the earlier URL-only stance.)

## Determinism / caching

Packets zero out timestamps before cache-prefix injection; the index/result cache keys on `repo_commit` + content hashes (so code/corpus changes invalidate). Ported from Trustless ACP's determinism discipline (stable cache prefix for council/reviewer reuse).

## The governed tool

`uacp_oracle_query` — **read-only** (no state mutation), so it fits the governed-tool model without a writer's authority. Input: `{phase, project, domains?, invariants?, file?, query?}`. Output: ranked provider packets + `metadata.sources_skipped`. RESOLVE's lesson write-back and promotion use the existing artifact/state writers, not this tool.

## Open items

- **vLLM vs TEI+Ollama** as the documented "blessed" local setup (vLLM covers more; TEI/Ollama simpler). Pick one for the quickstart; support both via config.
- **BGE-M3 sparse vs FTS5 BM25** as the lexical leg — both viable; sparse needs the `/pooling` path, FTS is free in the store. Start with store FTS; add sparse if recall needs it.
- **ColBERT/multi-vector** (PyLate/Qdrant) — opt-in future mode (~2× storage); not in the default pipeline.
- **Honcho retrieval shape** — confirm its query API and how memory packets rank against lessons/knowledge.

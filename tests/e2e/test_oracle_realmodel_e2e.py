"""GATED real-model end-to-end proof for the UACP Oracle semantic path.

WHAT THIS PROVES
----------------
The Oracle ships inert (``enabled=false``) and its semantic legs are otherwise
covered only by unit tests with mocked/poisoned deps. This module proves the
real ML retrieval path actually runs end-to-end with REAL deps:

  * STORE      — a real on-disk LanceDB index (temp dir): ``create_table`` with
                 real 384-dim MiniLM vectors + a native FTS index, then the
                 store's real ``dense_search`` / ``fts_search`` / ``rrf_hybrid``.
  * EMBEDDING  — the Oracle's real URL-mode client (``embed_texts`` over real
                 httpx) driven against an in-process OpenAI-compatible
                 ``/v1/embeddings`` stub backed by a REAL sentence-transformers
                 model (``all-MiniLM-L6-v2``, ~80MB, pure-pip, no compile).
  * PIPELINE   — the real ``semantic_retrieve`` orchestration (dense + fts ->
                 ``rrf_fuse`` k=60 -> rerank -> ``apply_bes_overlay``), driven
                 with the real store + a real embedding adapter + a real
                 reranker adapter. Not reimplemented here.
  * RERANK     — the Oracle's real URL-mode client (``rerank`` over real httpx)
                 driven against an in-process TEI-style ``/rerank`` stub backed
                 by a REAL cross-encoder (``ms-marco-MiniLM-L-6-v2``, ~80MB).

WHY URL-MODE FOR THE CLIENTS
----------------------------
The embedding/rerank clients have two real serving modes: URL (httpx ->
OpenAI/TEI endpoint) and EMBEDDED (in-process llama_cpp / FlagEmbedding, which
load no bundled weights in-repo and need multi-GB pinned models). The URL mode
is the LIGHTEST faithful path that exercises the real client code: real httpx
request/response parsing against a real model served in-process. The EMBEDDED
binding modes remain covered by their own unit tests. We deliberately do NOT
download the pinned BGE-M3 (~2GB+) / Qwen3-Reranker — this proves the plumbing,
not the specific pinned model (that is the separate reranker bake-off).

GATING (core suite stays green)
-------------------------------
This module SKIPS unless BOTH hold:
  * env ``UACP_ORACLE_E2E=1`` is set (explicit opt-in), AND
  * the heavy deps import (``lancedb``, ``sentence_transformers``, ``httpx``).
A default ``pytest -q`` (no env, deps maybe absent) never runs it.

RUNNING IT
----------
Install the optional ``oracle-e2e`` extra into an env (the heavy deps are NOT
in core ``pyproject`` dependencies), then opt in::

    uv pip install -e ".[oracle-e2e]"     # or: pip install -e ".[oracle-e2e]"
    UACP_ORACLE_E2E=1 pytest tests/e2e/test_oracle_realmodel_e2e.py -q

Models land in the HuggingFace cache (``~/.cache/huggingface``), never the repo.
The LanceDB index lives in a pytest tmp dir and is removed after the run; the
real project index dir ``.uacp/knowledge/indexes/`` is gitignored.
"""
from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

# --- Gate 1: explicit opt-in -------------------------------------------------
if __import__("os").environ.get("UACP_ORACLE_E2E") != "1":
    pytest.skip(
        "Oracle real-model e2e is opt-in: set UACP_ORACLE_E2E=1 to run "
        "(needs the [oracle-e2e] extra installed).",
        allow_module_level=True,
    )

# --- Gate 2: heavy deps must import ------------------------------------------
lancedb = pytest.importorskip("lancedb", reason="install the [oracle-e2e] extra")
pytest.importorskip("sentence_transformers", reason="install the [oracle-e2e] extra")
pytest.importorskip("httpx", reason="install the [oracle-e2e] extra")

from engines.oracle.clients.embedding import embed_texts  # noqa: E402
from engines.oracle.clients.rerank import rerank  # noqa: E402
from engines.oracle.packets import ProviderPacket, TrustClass  # noqa: E402
from engines.oracle.pipeline import (  # noqa: E402
    apply_bes_overlay,
    rrf_fuse,
    semantic_retrieve,
)
from engines.oracle.serving import RoleServing, ServingMode  # noqa: E402
from engines.oracle.store import get_store  # noqa: E402
from sentence_transformers import CrossEncoder, SentenceTransformer  # noqa: E402

# Small, real, pure-pip models (~80MB each, no compile). Downloaded once to the
# HF cache; never committed to the repo.
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_EMBED_DIM = 384

# A small slice of the REAL OKF corpus shape: a handful of governance docs, one
# clearly on-topic for the query, the rest distractors across topics.
_CORPUS: list[dict[str, Any]] = [
    {
        "id": "lesson-worktree-001",
        "type": "lesson",
        "text": (
            "Use isolation worktree on Agent tool calls that mutate files in "
            "parallel. Unchanged worktrees are auto-removed; this prevents "
            "merge conflicts between concurrent agents writing the same file."
        ),
        "domains": ["lifecycle"],
        "invariants": ["no-main-writes"],
        "bes": 0.9,
        "severity": "HIGH",
        "eligible": 6,
    },
    {
        "id": "lesson-worktree-002",
        "type": "lesson",
        "text": (
            "Parallel agents mutating the same file without an isolated working "
            "copy collide. Set worktree isolation for multi-agent file writes."
        ),
        "domains": ["lifecycle"],
        "invariants": ["no-main-writes"],
        "bes": 0.5,
        "severity": "MEDIUM",
        "eligible": 1,
    },
    {
        "id": "knowledge-council-003",
        "type": "pattern",
        "text": (
            "The Agent Council deliberates strategy and design; it is not a "
            "state database. Synthesis findings must be resolved before PLAN "
            "exits the council gate."
        ),
        "domains": ["council"],
        "invariants": ["council-gate"],
    },
    {
        "id": "knowledge-heartgate-004",
        "type": "contract",
        "text": (
            "Heartgate validates every phase transition. Direct phase-skipping "
            "is a blocker, not a warning, and fails closed."
        ),
        "domains": ["heartgate"],
        "invariants": ["triage-first"],
    },
    {
        "id": "knowledge-evidence-005",
        "type": "digest",
        "text": (
            "Done without a backing artifact and a gate-ledger entry is a "
            "Heartgate blocker. No self-attesting closures are permitted."
        ),
        "domains": ["verify"],
        "invariants": ["evidence-required"],
    },
]

# A query that is SEMANTICALLY (not lexically) close to the worktree lessons:
# it shares no rare keyword with the strongest-BES doc's distinctive phrasing,
# so a top rank is evidence the dense/semantic leg fired, not just FTS.
_QUERY = "how do concurrent agents avoid clobbering each other's edits"
_EXPECTED_TOP_DOC = "lesson-worktree-001"


# ---------------------------------------------------------------------------
# Module-scoped real models (load once; ~slow first run as HF downloads)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def embed_model() -> SentenceTransformer:
    return SentenceTransformer(_EMBED_MODEL)


@pytest.fixture(scope="module")
def rerank_model() -> CrossEncoder:
    return CrossEncoder(_RERANK_MODEL)


# ---------------------------------------------------------------------------
# Real on-disk LanceDB index built from real MiniLM vectors + native FTS index
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def lance_store(tmp_path_factory: pytest.TempPathFactory, embed_model: SentenceTransformer):
    index_path = tmp_path_factory.mktemp("oracle-index")
    db = lancedb.connect(str(index_path))

    vectors = embed_model.encode([d["text"] for d in _CORPUS], normalize_embeddings=True)
    rows = []
    for doc, vec in zip(_CORPUS, vectors, strict=True):
        row = dict(doc)
        row["vector"] = [float(x) for x in vec]
        rows.append(row)

    table = db.create_table("corpus", data=rows)
    table.create_fts_index("text")  # native FTS -> store.fts_search works for real

    # The store object the pipeline/tests drive (real LanceDBStore).
    store = get_store("lancedb", index_path=str(index_path))
    assert store.available()
    return store


# ---------------------------------------------------------------------------
# In-process OpenAI-compatible /v1/embeddings stub backed by a REAL model.
# The Oracle's real URL-mode embed_texts() (real httpx) talks to this.
# ---------------------------------------------------------------------------
def _make_embed_server(model: SentenceTransformer) -> tuple[HTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:  # silence
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            texts = body.get("input") or []
            if isinstance(texts, str):
                texts = [texts]
            vecs = model.encode(texts, normalize_embeddings=True)
            data = [
                {"object": "embedding", "index": i, "embedding": [float(x) for x in v]}
                for i, v in enumerate(vecs)
            ]
            payload = json.dumps({"object": "list", "data": data}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/v1/embeddings"


# ---------------------------------------------------------------------------
# In-process TEI-style /rerank stub backed by a REAL cross-encoder.
# The Oracle's real URL-mode rerank() (real httpx) talks to this.
# ---------------------------------------------------------------------------
def _make_rerank_server(model: CrossEncoder) -> tuple[HTTPServer, str]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: Any) -> None:
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            query = body.get("query", "")
            texts = body.get("texts") or []
            scores = model.predict([(query, t) for t in texts])
            data = [
                {"index": i, "score": float(s)} for i, s in enumerate(scores)
            ]
            payload = json.dumps(data).encode()  # TEI returns a bare list
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/rerank"


@pytest.fixture
def serve() -> Iterator[Any]:
    """Run an HTTPServer in a background thread for the duration of a test."""
    servers: list[HTTPServer] = []

    def _start(server: HTTPServer) -> None:
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()

    yield _start
    for s in servers:
        s.shutdown()
        s.server_close()


# ---------------------------------------------------------------------------
# Real adapters used to drive the real pipeline (semantic_retrieve)
# ---------------------------------------------------------------------------
class _UrlEmbedding:
    """Embedding adapter the pipeline calls .embed() on; delegates to the REAL
    URL-mode embed_texts client (real httpx -> in-process real-model stub)."""

    def __init__(self, url: str) -> None:
        self._serving = RoleServing("embedding", ServingMode.URL, model=_EMBED_MODEL, url=url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, self._serving)


class _UrlReranker:
    """Reranker adapter the pipeline calls .rerank() on; delegates to the REAL
    URL-mode rerank client (real httpx -> in-process real cross-encoder stub)."""

    def __init__(self, url: str) -> None:
        self._serving = RoleServing("rerank", ServingMode.URL, model=_RERANK_MODEL, url=url)

    def rerank(self, query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rerank(query, docs, self._serving)


# ===========================================================================
# LEG 1 — real STORE: dense / fts / rrf_hybrid against a real on-disk index
# ===========================================================================
def test_store_dense_search_real(lance_store, embed_model: SentenceTransformer) -> None:
    qvec = [float(x) for x in embed_model.encode([_QUERY], normalize_embeddings=True)[0]]
    results = lance_store.dense_search(qvec, k=5)

    assert results, "real dense_search returned nothing"
    assert "_distance" in results[0], "lancedb dense rows carry a _distance"
    # Semantic (not lexical) closeness must surface the worktree lesson on top.
    assert results[0]["id"] == _EXPECTED_TOP_DOC, (
        f"real dense retrieval should rank {_EXPECTED_TOP_DOC} first, "
        f"got order {[r['id'] for r in results]}"
    )


def test_store_fts_search_real(lance_store) -> None:
    # FTS is lexical: a distinctive corpus term must retrieve the right docs.
    results = lance_store.fts_search("worktree", k=5)
    ids = [r["id"] for r in results]
    assert "_score" in results[0], "lancedb fts rows carry a _score"
    assert "lesson-worktree-001" in ids and "lesson-worktree-002" in ids, (
        f"real FTS should retrieve the worktree lessons, got {ids}"
    )
    # A doc with no lexical 'worktree' must not be retrieved by this FTS query.
    assert "knowledge-evidence-005" not in ids


def test_store_rrf_hybrid_real(lance_store, embed_model: SentenceTransformer) -> None:
    qvec = [float(x) for x in embed_model.encode([_QUERY], normalize_embeddings=True)[0]]
    hybrid = lance_store.rrf_hybrid(qvec, _QUERY, k=5)
    assert hybrid, "rrf_hybrid (vector probe) returned nothing"
    assert hybrid[0]["id"] == _EXPECTED_TOP_DOC


# ===========================================================================
# LEG 2 — real EMBEDDING URL client (real httpx) against a real-model stub
# ===========================================================================
def test_embedding_url_client_real(serve, embed_model: SentenceTransformer) -> None:
    server, url = _make_embed_server(embed_model)
    serve(server)
    serving = RoleServing("embedding", ServingMode.URL, model=_EMBED_MODEL, url=url)

    vectors = embed_texts([_QUERY, "the cat sat on the mat"], serving)
    assert len(vectors) == 2
    assert len(vectors[0]) == _EMBED_DIM, "real model returns 384-dim vectors"
    # Cosine of the query against itself (re-embedded by the same real model)
    # must be ~1.0 — proves the real bytes round-tripped through httpx intact.
    again = embed_texts([_QUERY], serving)[0]
    dot = sum(a * b for a, b in zip(vectors[0], again, strict=True))
    assert dot > 0.99, f"re-embedding the same text should be near-identical, dot={dot}"


# ===========================================================================
# LEG 3 — real PIPELINE: semantic_retrieve over the real store + real embedding
# ===========================================================================
def test_pipeline_semantic_retrieve_real(
    lance_store, serve, embed_model: SentenceTransformer
) -> None:
    server, url = _make_embed_server(embed_model)
    serve(server)
    embedding = _UrlEmbedding(url)

    packets = semantic_retrieve(
        _QUERY,
        lance_store,
        domains=["lifecycle"],
        invariants=["no-main-writes"],
        embedding=embedding,
        reranker=None,
        k=60,
    )

    assert packets, "real pipeline returned no packets"
    assert all(isinstance(p, ProviderPacket) for p in packets)
    top = packets[0]
    assert top.payload["id"] == _EXPECTED_TOP_DOC, (
        f"pipeline should surface {_EXPECTED_TOP_DOC} first, "
        f"got {[p.payload['id'] for p in packets]}"
    )
    # The worktree lesson is a 'lesson' -> advisory trust class.
    assert top.trust_class == TrustClass.advisory


# ===========================================================================
# LEG 4 — real RRF fusion merges dense + fts rankings
# ===========================================================================
def test_rrf_fuse_merges_dense_and_fts(lance_store, embed_model: SentenceTransformer) -> None:
    qvec = [float(x) for x in embed_model.encode([_QUERY], normalize_embeddings=True)[0]]
    dense = lance_store.dense_search(qvec, k=5)
    fts = lance_store.fts_search("worktree", k=5)
    fused = rrf_fuse(dense, fts, k=60)

    fused_ids = [d["id"] for d in fused]
    # Fusion contains the union and dedupes by id.
    assert len(fused_ids) == len(set(fused_ids)), "rrf_fuse must dedupe by id"
    assert set(d["id"] for d in fts) <= set(fused_ids)
    # A doc present in BOTH legs (worktree-001) should win the fused ranking.
    assert fused_ids[0] == _EXPECTED_TOP_DOC


# ===========================================================================
# LEG 5 — BES overlay reorders lessons by composite (relevance + bes_bonus)
# ===========================================================================
def test_bes_overlay_reorders_by_composite() -> None:
    # Two lessons, equal relevance (both match domain+invariant), differing BES.
    # The high-BES/HIGH-severity lesson must outrank the low-BES one.
    high = _CORPUS[0]  # bes 0.9, HIGH -> bes_bonus 6 ; relevance 1+2=3 -> 9.0
    low = _CORPUS[1]  # bes 0.5, MEDIUM -> bes_bonus 3 ; relevance 1+2=3 -> 6.0
    scored = apply_bes_overlay(
        [low, high],  # deliberately reversed input order
        query_domains=["lifecycle"],
        query_invariants=["no-main-writes"],
    )
    ordered_ids = [doc["id"] for _score, doc in scored]
    assert ordered_ids[0] == high["id"], "higher BES lesson must rank first"
    assert scored[0][0] > scored[1][0], "composite score must reflect the BES gap"

    # A lesson with zero relevance overlap is gated OUT entirely.
    irrelevant = {**low, "id": "lesson-nomatch", "domains": ["other"], "invariants": []}
    gated = apply_bes_overlay(
        [irrelevant], query_domains=["lifecycle"], query_invariants=["no-main-writes"]
    )
    assert gated == [], "BES gate (relevance>=1) must exclude non-matching lessons"


# ===========================================================================
# LEG 6 — real RERANK URL client (real cross-encoder) reorders candidates
# ===========================================================================
def test_rerank_url_client_real(serve, rerank_model: CrossEncoder) -> None:
    server, url = _make_rerank_server(rerank_model)
    serve(server)
    serving = RoleServing("rerank", ServingMode.URL, model=_RERANK_MODEL, url=url)

    # Feed candidates in a deliberately wrong order; the real cross-encoder must
    # pull the on-topic worktree doc to the front.
    candidates = [
        {"id": "knowledge-evidence-005", "text": _CORPUS[4]["text"]},
        {"id": "knowledge-council-003", "text": _CORPUS[2]["text"]},
        {"id": "lesson-worktree-001", "text": _CORPUS[0]["text"]},
    ]
    reranked = rerank(
        "how do concurrent agents avoid clobbering each other's edits",
        candidates,
        serving,
    )
    assert [d["id"] for d in reranked][0] == "lesson-worktree-001", (
        f"real reranker should pull the worktree doc to the top, "
        f"got {[d['id'] for d in reranked]}"
    )


# ===========================================================================
# LEG 7 — full pipeline WITH real reranker wired in (dense+fts -> RRF -> rerank)
# ===========================================================================
def test_pipeline_with_real_reranker(
    lance_store, serve, embed_model: SentenceTransformer, rerank_model: CrossEncoder
) -> None:
    embed_server, embed_url = _make_embed_server(embed_model)
    rerank_server, rerank_url = _make_rerank_server(rerank_model)
    serve(embed_server)
    serve(rerank_server)

    packets = semantic_retrieve(
        _QUERY,
        lance_store,
        domains=["lifecycle"],
        invariants=["no-main-writes"],
        embedding=_UrlEmbedding(embed_url),
        reranker=_UrlReranker(rerank_url),
        k=60,
    )
    assert packets, "pipeline with reranker returned nothing"
    assert packets[0].payload["id"] == _EXPECTED_TOP_DOC

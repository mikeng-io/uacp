"""GATED real-model e2e for the Oracle INDEX-BUILD path (build_index + upsert).

WHAT THIS PROVES
----------------
The companion module ``test_oracle_realmodel_e2e.py`` proves the SEARCH path
against a hand-built table. This module proves the Oracle can BUILD its own
index end-to-end with REAL deps, then retrieve correctly from what it built:

  * GENERATE  — a deterministic synthetic OKF corpus (engines.oracle.eval.
                synthetic.generate_corpus): N valid lesson/knowledge files
                across several domains, each a distinctive topic, plus a
                (query, expected_top_id) relevance map with SEMANTIC paraphrase
                queries.
  * BUILD     — the real ``index_build.build_index`` -> real
                ``LanceDBStore.upsert`` (merge_insert by id + native FTS index),
                embedding every item via the real URL-mode ``embed_texts``
                client (real httpx) against an in-process /v1/embeddings stub
                backed by a REAL all-MiniLM-L6-v2 model.
  * RETRIEVE  — for each relevance pair, the expected item ranks TOP via the
                store's real ``dense_search`` AND via the real pipeline
                ``semantic_retrieve`` (dense + fts -> rrf_fuse -> BES overlay).
                Content + model are both deterministic, so the rankings are
                stable and asserted concretely.

GATING (core suite stays green) — same as the sibling module: SKIPS unless
``UACP_ORACLE_E2E=1`` AND lancedb + sentence_transformers + httpx import.

RUN IT
------
    uv pip install -e ".[oracle-e2e]"
    UACP_ORACLE_E2E=1 pytest tests/e2e/test_oracle_index_build_e2e.py -q
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import HTTPServer
from typing import Any

import pytest

# --- Gate 1: explicit opt-in -------------------------------------------------
if __import__("os").environ.get("UACP_ORACLE_E2E") != "1":
    pytest.skip(
        "Oracle index-build e2e is opt-in: set UACP_ORACLE_E2E=1 to run "
        "(needs the [oracle-e2e] extra installed).",
        allow_module_level=True,
    )

# --- Gate 2: heavy deps must import ------------------------------------------
pytest.importorskip("lancedb", reason="install the [oracle-e2e] extra")
pytest.importorskip("sentence_transformers", reason="install the [oracle-e2e] extra")
pytest.importorskip("httpx", reason="install the [oracle-e2e] extra")

from engines.oracle.eval.synthetic import generate_corpus  # noqa: E402
from engines.oracle.index_build import build_index  # noqa: E402
from engines.oracle.pipeline import semantic_retrieve  # noqa: E402
from engines.oracle.serving import RoleServing, ServingMode  # noqa: E402
from engines.oracle.store import get_store  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from tests.e2e._oracle_e2e_support import (  # noqa: E402
    EMBED_MODEL,
    UrlEmbedding,
    make_embed_server,
)

_N = 8  # one item per distinctive topic in the synthetic table
_SEED = 13


@pytest.fixture(scope="module")
def embed_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


@pytest.fixture
def serve() -> Iterator[Any]:
    servers: list[HTTPServer] = []

    def _start(server: HTTPServer) -> None:
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()

    yield _start
    for s in servers:
        s.shutdown()
        s.server_close()


@pytest.fixture
def built_index(tmp_path, serve, embed_model: SentenceTransformer):
    """Generate a synthetic corpus, then BUILD the real index from it.

    Returns (corpus_spec, store, index_path). The index is built with the real
    build_index -> real upsert, embedding via the real URL client + real model.
    """
    corpus_root = tmp_path / "uacp"
    spec = generate_corpus(corpus_root, n=_N, seed=_SEED)

    server, url = make_embed_server(embed_model)
    serve(server)
    serving = RoleServing("embedding", ServingMode.URL, model=EMBED_MODEL, url=url)

    index_path = tmp_path / "index"
    count = build_index(spec.root, embedding_serving=serving, index_path=index_path)
    assert count == len(spec.items), f"expected {len(spec.items)} indexed, got {count}"

    store = get_store("lancedb", index_path=str(index_path))
    assert store.available()
    return spec, store, index_path


def test_build_populates_table_and_fts(built_index, embed_model: SentenceTransformer):
    spec, store, index_path = built_index

    # N rows landed.
    import lancedb

    db = lancedb.connect(str(index_path))
    table = db.open_table("corpus")
    assert table.count_rows() == len(spec.items)

    # FTS index works: a distinctive body word retrieves something with a score.
    fts = store.fts_search("isolated", k=5)
    assert fts, "FTS search returned nothing — native index missing?"
    assert "_score" in fts[0], "lancedb FTS rows carry a _score"


def test_dense_search_ranks_expected_top(built_index, embed_model: SentenceTransformer):
    spec, store, _ = built_index
    for query, expected_id in spec.relevance:
        qvec = [float(x) for x in embed_model.encode([query], normalize_embeddings=True)[0]]
        results = store.dense_search(qvec, k=len(spec.items))
        assert results, f"dense_search empty for query {query!r}"
        assert results[0]["id"] == expected_id, (
            f"dense retrieval should rank {expected_id} top for {query!r}, "
            f"got order {[r['id'] for r in results]}"
        )


def test_pipeline_semantic_retrieve_ranks_expected_top(built_index, serve, embed_model):
    spec, store, _ = built_index
    server, url = make_embed_server(embed_model)
    serve(server)
    embedding = UrlEmbedding(url)

    # Map id -> (domain, invariant) so we can pass the right BES filter and keep
    # the expected lesson from being gated out of the BES overlay.
    by_id = {i.id: i for i in spec.items}

    for query, expected_id in spec.relevance:
        item = by_id[expected_id]
        packets = semantic_retrieve(
            query,
            store,
            domains=[item.domain],
            invariants=[item.invariant],
            embedding=embedding,
            reranker=None,
            k=60,
        )
        assert packets, f"pipeline returned nothing for {query!r}"
        assert packets[0].payload["id"] == expected_id, (
            f"pipeline should surface {expected_id} first for {query!r}, "
            f"got {[p.payload['id'] for p in packets]}"
        )


def test_rebuild_is_idempotent_upsert(built_index, serve, embed_model):
    """A second build over the same corpus must NOT duplicate rows (merge by id)."""
    spec, store, index_path = built_index

    server, url = make_embed_server(embed_model)
    serve(server)
    serving = RoleServing("embedding", ServingMode.URL, model=EMBED_MODEL, url=url)

    count = build_index(spec.root, embedding_serving=serving, index_path=index_path)
    assert count == len(spec.items)

    import lancedb

    db = lancedb.connect(str(index_path))
    table = db.open_table("corpus")
    assert table.count_rows() == len(spec.items), "rebuild must upsert, not append"

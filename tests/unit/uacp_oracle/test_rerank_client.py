"""Tests for the oracle rerank client (URL + embedded modes).

URL mode posts the TEI-style {query, texts} shape to a /rerank endpoint via a
lazily imported httpx client (monkeypatched — no network) and reorders docs by
returned score desc. Cohere/vLLM /v1/rerank is a config-selected variant of the
same client. Embedded mode is lazy + guarded. FLOOR raises RerankUnavailable so
the pipeline keeps the RRF-fused order.
"""
from __future__ import annotations

import pytest

from engines.oracle.clients.rerank import RerankUnavailable, rerank
from engines.oracle.serving import RoleServing, ServingMode


def test_floor_raises_rerank_unavailable():
    docs = [{"id": "a"}, {"id": "b"}]
    with pytest.raises(RerankUnavailable):
        rerank("q", docs, RoleServing("rerank", ServingMode.FLOOR))


def test_url_mode_tei_shape_reorders_by_score(monkeypatch):
    seen = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"index": 1, "score": 0.9}, {"index": 0, "score": 0.1}]

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json, headers=None):
            seen["url"] = url
            seen["json"] = json
            return _Resp()

    import engines.oracle.clients.rerank as rr

    monkeypatch.setattr(rr, "_httpx_client", lambda *a, **k: _Client())
    out = rerank(
        "q",
        [{"id": "a"}, {"id": "b"}],
        RoleServing("rerank", ServingMode.URL, model="bge-reranker-v2-m3", url="http://x/rerank"),
    )
    assert [d["id"] for d in out] == ["b", "a"]
    assert "query" in seen["json"] and "texts" in seen["json"]


def test_url_mode_handles_results_envelope(monkeypatch):
    # vLLM/Cohere /v1/rerank returns {"results": [{index, relevance_score}]}.
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"index": 0, "relevance_score": 0.8}, {"index": 1, "relevance_score": 0.2}]}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json, headers=None):
            return _Resp()

    import engines.oracle.clients.rerank as rr

    monkeypatch.setattr(rr, "_httpx_client", lambda *a, **k: _Client())
    out = rerank(
        "q",
        [{"id": "a"}, {"id": "b"}],
        RoleServing("rerank", ServingMode.URL, url="http://x/v1/rerank"),
    )
    assert [d["id"] for d in out] == ["a", "b"]


def test_url_mode_unavailable_when_httpx_absent(monkeypatch):
    import engines.oracle.clients.rerank as rr

    monkeypatch.setattr(rr, "_httpx_client", lambda *a, **k: None)
    with pytest.raises(RerankUnavailable):
        rerank("q", [{"id": "a"}], RoleServing("rerank", ServingMode.URL, url="http://x/rerank"))


def test_embedded_mode_unavailable_without_binding(monkeypatch):
    import engines.oracle.clients.rerank as rr

    monkeypatch.setattr(rr, "_load_embedded_reranker", lambda model: None)
    with pytest.raises(RerankUnavailable):
        rerank("q", [{"id": "a"}], RoleServing("rerank", ServingMode.EMBEDDED, model="qwen3-reranker-0.6b"))


def test_embedded_mode_uses_binding_when_present(monkeypatch):
    import engines.oracle.clients.rerank as rr

    class _RR:
        def score(self, query, texts):
            # higher score for the second doc -> it should sort first
            return [0.1, 0.9]

    monkeypatch.setattr(rr, "_load_embedded_reranker", lambda model: _RR())
    out = rerank(
        "q",
        [{"id": "a"}, {"id": "b"}],
        RoleServing("rerank", ServingMode.EMBEDDED, model="qwen3-reranker-0.6b"),
    )
    assert [d["id"] for d in out] == ["b", "a"]


# ---------------------------------------------------------------------------
# Embedded loader: model-name → repo-id resolution + family dispatch + caching.
# These exercise the loader without the heavy ML deps installed: with the deps
# absent the adapter __init__ raises ImportError, which the loader maps to None
# (graceful degradation). The dispatch/resolution logic runs regardless.
# ---------------------------------------------------------------------------


def test_resolve_repo_id_maps_aliases_and_passes_full_ids():
    import engines.oracle.clients.rerank as rr

    assert rr._resolve_repo_id("qwen3-reranker-0.6b") == "Qwen/Qwen3-Reranker-0.6B"
    assert rr._resolve_repo_id("bge-reranker-v2-m3") == "BAAI/bge-reranker-v2-m3"
    # A full org/repo id passes through untouched.
    assert rr._resolve_repo_id("BAAI/bge-reranker-base") == "BAAI/bge-reranker-base"
    # Unknown short name passes through (best-effort).
    assert rr._resolve_repo_id("mystery-model") == "mystery-model"


def test_load_embedded_reranker_returns_none_when_deps_absent():
    """Without sentence-transformers/transformers installed, load → None (degrade)."""
    import engines.oracle.clients.rerank as rr

    rr._reset_embedded_cache()
    # If the heavy deps happen to be installed in this env, the loader returns an
    # adapter instead of None; either outcome is contractually valid. We only
    # assert it never raises and that absence yields None.
    result = rr._load_embedded_reranker("bge-reranker-v2-m3")
    if result is None:
        # deps absent: nothing was cached
        assert "bge-reranker-v2-m3" not in rr._EMBEDDED_CACHE
    else:
        assert hasattr(result, "score")
    rr._reset_embedded_cache()


def test_load_embedded_reranker_caches_successful_load(monkeypatch):
    """A successful load is memoized: a second call does not rebuild the adapter."""
    import engines.oracle.clients.rerank as rr

    rr._reset_embedded_cache()
    builds = {"n": 0}

    class _Stub:
        def __init__(self, repo_id):
            builds["n"] += 1

        def score(self, q, texts):
            return [0.0] * len(texts)

    # Force the cross-encoder branch to use our stub adapter.
    monkeypatch.setattr(rr, "_CrossEncoderReranker", _Stub)
    first = rr._load_embedded_reranker("bge-reranker-v2-m3")
    second = rr._load_embedded_reranker("bge-reranker-v2-m3")
    assert first is second
    assert builds["n"] == 1  # built once, served from cache thereafter
    rr._reset_embedded_cache()


def test_load_embedded_reranker_dispatches_qwen3_to_generative(monkeypatch):
    """The qwen3-reranker family routes to the generative (yes/no-logit) adapter."""
    import engines.oracle.clients.rerank as rr

    rr._reset_embedded_cache()
    picked = {}

    class _Gen:
        def __init__(self, repo_id):
            picked["family"] = "generative"

        def score(self, q, texts):
            return [0.0] * len(texts)

    class _CE:
        def __init__(self, repo_id):
            picked["family"] = "cross-encoder"

        def score(self, q, texts):
            return [0.0] * len(texts)

    monkeypatch.setattr(rr, "_Qwen3GenerativeReranker", _Gen)
    monkeypatch.setattr(rr, "_CrossEncoderReranker", _CE)

    rr._load_embedded_reranker("qwen3-reranker-0.6b")
    assert picked["family"] == "generative"
    rr._reset_embedded_cache()
    rr._load_embedded_reranker("bge-reranker-v2-m3")
    assert picked["family"] == "cross-encoder"
    rr._reset_embedded_cache()

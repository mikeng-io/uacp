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

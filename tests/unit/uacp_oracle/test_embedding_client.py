"""Tests for the oracle embedding client (URL + embedded modes).

URL mode posts to an OpenAI-style /v1/embeddings endpoint via a lazily-imported
httpx client (monkeypatched in tests — no network). Embedded mode uses a lazy
llama.cpp binding and degrades cleanly (EmbeddingUnavailable) when absent. FLOOR
always raises EmbeddingUnavailable so the pipeline falls back to the keyword leg.
"""
from __future__ import annotations

import pytest

from engines.oracle.clients.embedding import EmbeddingUnavailable, embed_texts
from engines.oracle.serving import RoleServing, ServingMode


def test_floor_mode_has_no_embeddings():
    with pytest.raises(EmbeddingUnavailable):
        embed_texts(["hi"], RoleServing("embedding", ServingMode.FLOOR))


def test_url_mode_posts_to_endpoint(monkeypatch):
    calls = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [0.1, 0.2]}]}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json, headers=None):
            calls["url"] = url
            calls["json"] = json
            calls["headers"] = headers
            return _Resp()

    import engines.oracle.clients.embedding as em

    monkeypatch.setattr(em, "_httpx_client", lambda *a, **k: _Client())
    out = embed_texts(
        ["hi"],
        RoleServing("embedding", ServingMode.URL, model="bge-m3", url="http://x/v1/embeddings"),
    )
    assert out == [[0.1, 0.2]]
    assert calls["url"].endswith("/v1/embeddings")
    assert calls["json"]["input"] == ["hi"]
    assert calls["json"]["model"] == "bge-m3"


def test_url_mode_unavailable_when_httpx_absent(monkeypatch):
    import engines.oracle.clients.embedding as em

    monkeypatch.setattr(em, "_httpx_client", lambda *a, **k: None)
    with pytest.raises(EmbeddingUnavailable):
        embed_texts(["hi"], RoleServing("embedding", ServingMode.URL, url="http://x/v1/embeddings"))


def test_url_mode_reads_api_key_from_env_only(monkeypatch):
    seen = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [{"embedding": [1.0]}]}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json, headers=None):
            seen["headers"] = headers or {}
            return _Resp()

    import engines.oracle.clients.embedding as em

    monkeypatch.setattr(em, "_httpx_client", lambda *a, **k: _Client())
    monkeypatch.setenv("MY_EMBED_KEY", "secret-token")
    embed_texts(
        ["hi"],
        RoleServing("embedding", ServingMode.URL, url="http://x/v1/embeddings"),
        api_key_env="MY_EMBED_KEY",
    )
    assert seen["headers"].get("Authorization") == "Bearer secret-token"


def test_embedded_mode_unavailable_without_binding(monkeypatch):
    import engines.oracle.clients.embedding as em

    monkeypatch.setattr(em, "_load_embedded_model", lambda model: None)
    with pytest.raises(EmbeddingUnavailable):
        embed_texts(["hi"], RoleServing("embedding", ServingMode.EMBEDDED, model="bge-m3"))


def test_embedded_mode_uses_binding_when_present(monkeypatch):
    import engines.oracle.clients.embedding as em

    class _Model:
        def embed(self, texts):
            return [[0.5] * 3 for _ in texts]

    monkeypatch.setattr(em, "_load_embedded_model", lambda model: _Model())
    out = embed_texts(["a", "b"], RoleServing("embedding", ServingMode.EMBEDDED, model="bge-m3"))
    assert out == [[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]]

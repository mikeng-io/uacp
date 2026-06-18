"""Non-gated unit tests for the Oracle index-build orchestrator.

These exercise the FLOOR no-op + the dep-absent degrade paths WITHOUT any heavy
deps (no lancedb / embedding model / network). The real build+retrieve proof is
the gated e2e (tests/e2e/test_oracle_index_build_e2e.py).
"""
from __future__ import annotations

import sys

import pytest

from engines.oracle.eval.synthetic import generate_corpus
from engines.oracle.index_build import (
    IndexBuildUnavailable,
    build_index,
    item_text,
)
from engines.oracle.serving import RoleServing, ServingMode


def test_floor_serving_builds_nothing(tmp_path):
    spec = generate_corpus(tmp_path / "c", n=6, seed=1)
    floor = RoleServing("embedding", ServingMode.FLOOR)
    # FLOOR -> no vector index, clean no-op returning 0 (not an error).
    assert build_index(spec.root, embedding_serving=floor) == 0


def test_empty_corpus_returns_zero(tmp_path):
    # Non-FLOOR serving but empty corpus dirs -> 0, no embedding attempted.
    (tmp_path / "lessons").mkdir()
    (tmp_path / "knowledge").mkdir()
    url = RoleServing("embedding", ServingMode.URL, model="x", url="http://127.0.0.1:0/")
    assert build_index(tmp_path, embedding_serving=url) == 0


def test_store_dep_absent_raises_index_build_unavailable(tmp_path, monkeypatch):
    # Embedding "works" (monkeypatched) but lancedb is poisoned -> the store
    # upsert raises StoreUnavailable, surfaced as IndexBuildUnavailable.
    spec = generate_corpus(tmp_path / "c", n=4, seed=2)
    monkeypatch.setitem(sys.modules, "lancedb", None)

    import engines.oracle.index_build as ib

    def _fake_embed(texts, serving, **kw):
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(
        "engines.oracle.clients.embedding.embed_texts", _fake_embed, raising=True
    )

    url = RoleServing("embedding", ServingMode.URL, model="x", url="http://127.0.0.1:0/")
    with pytest.raises(IndexBuildUnavailable):
        ib.build_index(spec.root, embedding_serving=url)


def test_item_text_combines_title_and_body(tmp_path):
    from engines.domain.corpus import Lesson

    lesson = Lesson(id="x", title="My Title", project="p", body="The body text.")
    txt = item_text(lesson)
    assert "My Title" in txt and "The body text." in txt

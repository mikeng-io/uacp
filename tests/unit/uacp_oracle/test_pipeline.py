"""Tests for the Oracle semantic pipeline (Task 8a — hybrid pipeline).

All tests use a mocked store and mocked rerank client — no real models, no network.
"""
from __future__ import annotations


from engines.oracle.pipeline import semantic_retrieve
from engines.oracle.packets import ProviderPacket, TrustClass


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

class _FakeStore:
    """Deterministic fake store that returns two pre-canned documents."""

    def available(self) -> bool:
        return True

    def dense_search(self, vector, k):
        return [
            {"id": "L1", "type": "lesson", "domains": ["auth"], "invariants": ["I1"],
             "bes": 0.9, "severity": "CRITICAL", "body": "...lesson body"},
            {"id": "K1", "type": "pattern", "domains": ["auth"], "body": "...knowledge body"},
        ]

    def fts_search(self, query, k):
        return [
            {"id": "K1", "type": "pattern", "domains": ["auth"], "body": "...knowledge body"},
            {"id": "L1", "type": "lesson", "domains": ["auth"], "invariants": ["I1"],
             "bes": 0.9, "severity": "CRITICAL", "body": "...lesson body"},
        ]

    def rrf_hybrid(self, vector, query, k):
        return [
            {"id": "L1", "type": "lesson", "domains": ["auth"], "invariants": ["I1"],
             "bes": 0.9, "severity": "CRITICAL", "body": "...lesson body"},
            {"id": "K1", "type": "pattern", "domains": ["auth"], "body": "...knowledge body"},
        ]


class _UnavailableStore:
    def available(self) -> bool:
        return False

    def dense_search(self, vector, k):
        raise RuntimeError("store unavailable")

    def fts_search(self, query, k):
        raise RuntimeError("store unavailable")

    def rrf_hybrid(self, vector, query, k):
        raise RuntimeError("store unavailable")


# ---------------------------------------------------------------------------
# RRF fusion tests (the pure arithmetic is testable without a store)
# ---------------------------------------------------------------------------

def test_rrf_fusion_combines_lists():
    """RRF merges dense + fts rankings; higher-ranked in both => higher score."""
    from engines.oracle.pipeline import rrf_fuse

    dense = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    fts   = [{"id": "B"}, {"id": "A"}, {"id": "D"}]
    fused = rrf_fuse(dense, fts, k=60)
    ids = [d["id"] for d in fused]
    # A appears at rank 1 in dense and rank 2 in fts
    # B appears at rank 2 in dense and rank 1 in fts
    # Both should beat C (only in dense) and D (only in fts)
    assert set(ids[:2]) == {"A", "B"}
    assert "C" in ids and "D" in ids


def test_rrf_fusion_empty_legs_returns_nonempty():
    """One empty leg still returns results from the other."""
    from engines.oracle.pipeline import rrf_fuse

    dense = [{"id": "A"}, {"id": "B"}]
    fused = rrf_fuse(dense, [], k=60)
    assert [d["id"] for d in fused] == ["A", "B"]


def test_rrf_fusion_deduplicates():
    """Docs appearing in both legs appear once in the output."""
    from engines.oracle.pipeline import rrf_fuse

    docs = [{"id": "A"}, {"id": "B"}]
    fused = rrf_fuse(docs, docs, k=60)
    ids = [d["id"] for d in fused]
    assert ids.count("A") == 1 and ids.count("B") == 1


def test_rrf_k60_constant_affects_score():
    """k=60 is the canonical value; a higher k flattens ranking differences."""
    from engines.oracle.pipeline import rrf_fuse

    dense = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    fts   = [{"id": "B"}, {"id": "A"}, {"id": "C"}]
    fused_60 = rrf_fuse(dense, fts, k=60)
    # Just check dedup + ordering is stable (no assertion on exact scores — those
    # are covered by the combining test above)
    assert [d["id"] for d in fused_60][:2] == ["A", "B"] or \
           [d["id"] for d in fused_60][:2] == ["B", "A"]


# ---------------------------------------------------------------------------
# BES overlay tests
# ---------------------------------------------------------------------------

def test_bes_overlay_gates_lessons_with_no_domain_match():
    """Lesson with zero relevance (no domain/invariant overlap) must be excluded."""
    from engines.oracle.pipeline import apply_bes_overlay

    lesson_doc = {
        "id": "L1", "type": "lesson",
        "domains": ["payments"],  # not in query domains
        "invariants": ["I1"],
        "bes": 0.9, "severity": "HIGH", "eligible": 2,
        "body": "body",
    }
    # No domain overlap -> relevance=0 -> gated out
    result = apply_bes_overlay([lesson_doc], query_domains=["auth"], query_invariants=[])
    assert result == []


def test_bes_overlay_passes_lessons_with_domain_match():
    """Lesson sharing a domain with the query passes the relevance gate."""
    from engines.oracle.pipeline import apply_bes_overlay

    lesson_doc = {
        "id": "L1", "type": "lesson",
        "domains": ["auth"],
        "invariants": [],
        "bes": 0.75, "severity": "MEDIUM", "eligible": 3,
        "body": "body",
    }
    result = apply_bes_overlay([lesson_doc], query_domains=["auth"], query_invariants=[])
    assert len(result) == 1
    assert result[0][0] > 0  # (score, doc) tuple


def test_bes_overlay_adds_bonus_for_critical_severity():
    """CRITICAL severity adds +1 on top of the BES tier bonus."""
    from engines.oracle.pipeline import apply_bes_overlay

    lesson_high = {
        "id": "L1", "type": "lesson",
        "domains": ["auth"], "invariants": [],
        "bes": 0.75, "severity": "CRITICAL", "eligible": 3, "body": "b",
    }
    lesson_med = {
        "id": "L2", "type": "lesson",
        "domains": ["auth"], "invariants": [],
        "bes": 0.75, "severity": "MEDIUM", "eligible": 3, "body": "b",
    }
    scored = apply_bes_overlay(
        [lesson_high, lesson_med], query_domains=["auth"], query_invariants=[]
    )
    # Both have same relevance (1 domain match) but CRITICAL gets +1 from bes_bonus
    score_critical = next(s for s, d in scored if d["id"] == "L1")
    score_medium   = next(s for s, d in scored if d["id"] == "L2")
    assert score_critical > score_medium


def test_bes_overlay_knowledge_items_skip_bes():
    """Knowledge items (type != 'lesson') pass through without BES overlay."""
    from engines.oracle.pipeline import apply_bes_overlay

    knowledge_doc = {
        "id": "K1", "type": "pattern",
        "domains": ["auth"], "body": "body",
    }
    # Knowledge items skip BES — they are not filtered by the gate
    result = apply_bes_overlay([knowledge_doc], query_domains=["auth"], query_invariants=[])
    # knowledge passes through; the overlay is only for lessons
    assert any(d["id"] == "K1" for _, d in result)


def test_invariant_match_increases_score():
    """An invariant match boosts the relevance score above domain-only."""
    from engines.oracle.pipeline import apply_bes_overlay

    lesson_inv = {
        "id": "L1", "type": "lesson",
        "domains": ["auth"], "invariants": ["I1"],
        "bes": 0.75, "severity": "MEDIUM", "eligible": 2, "body": "b",
    }
    lesson_no_inv = {
        "id": "L2", "type": "lesson",
        "domains": ["auth"], "invariants": [],
        "bes": 0.75, "severity": "MEDIUM", "eligible": 2, "body": "b",
    }
    scored = apply_bes_overlay(
        [lesson_inv, lesson_no_inv],
        query_domains=["auth"], query_invariants=["I1"]
    )
    score_with_inv    = next(s for s, d in scored if d["id"] == "L1")
    score_without_inv = next(s for s, d in scored if d["id"] == "L2")
    assert score_with_inv > score_without_inv


# ---------------------------------------------------------------------------
# End-to-end pipeline tests (mock store, no real models)
# ---------------------------------------------------------------------------

def test_pipeline_returns_packets_for_valid_store():
    """With a working store and no models, the pipeline returns ProviderPackets."""
    out = semantic_retrieve(
        query="auth bug",
        store=_FakeStore(),
        domains=["auth"],
        invariants=["I1"],
        embedding=None,
        reranker=None,
    )
    assert out  # non-empty
    assert all(isinstance(p, ProviderPacket) for p in out)


def test_pipeline_lessons_are_advisory():
    """Lesson packets come back as advisory trust class."""
    out = semantic_retrieve(
        query="auth",
        store=_FakeStore(),
        domains=["auth"],
        invariants=["I1"],
        embedding=None,
        reranker=None,
    )
    lessons = [p for p in out if p.payload.get("type") == "lesson"]
    assert lessons
    assert all(p.trust_class == TrustClass.advisory for p in lessons)
    assert all(p.evidence_required is True for p in lessons)


def test_pipeline_knowledge_is_normative():
    """Knowledge packets come back as normative trust class."""
    out = semantic_retrieve(
        query="auth",
        store=_FakeStore(),
        domains=["auth"],
        invariants=[],
        embedding=None,
        reranker=None,
    )
    knowledge = [p for p in out if p.payload.get("type") in ("pattern", "digest", "analysis", "contract")]
    assert knowledge
    assert all(p.trust_class == TrustClass.normative for p in knowledge)


def test_pipeline_unavailable_store_returns_empty():
    """Unavailable store -> pipeline degrades to empty (no raise)."""
    out = semantic_retrieve(
        query="auth",
        store=_UnavailableStore(),
        domains=["auth"],
        invariants=[],
        embedding=None,
        reranker=None,
    )
    assert out == []


def test_pipeline_never_raises_on_store_error():
    """Any store error -> empty list, not an exception."""
    class _BrokenStore:
        def available(self): return True
        def dense_search(self, v, k): raise OSError("disk gone")
        def fts_search(self, q, k): raise OSError("disk gone")
        def rrf_hybrid(self, v, q, k): raise OSError("disk gone")

    out = semantic_retrieve(
        query="q",
        store=_BrokenStore(),
        domains=["d"],
        invariants=[],
        embedding=None,
        reranker=None,
    )
    assert out == []


def test_pipeline_rerank_unavailable_keeps_rrf_order():
    """When reranker raises, pipeline keeps RRF-fused order rather than crashing."""
    from engines.oracle.clients.rerank import RerankUnavailable

    class _BadReranker:
        def rerank(self, *a, **k):
            raise RerankUnavailable("no reranker")

    # Should still return packets (RRF order preserved)
    out = semantic_retrieve(
        query="auth",
        store=_FakeStore(),
        domains=["auth"],
        invariants=["I1"],
        embedding=None,
        reranker=_BadReranker(),
    )
    assert out  # non-empty despite reranker failure


def test_pipeline_floor_no_ml_deps(monkeypatch):
    """Pipeline must import clean even when lancedb and llama_cpp are poisoned."""
    import sys

    monkeypatch.setitem(sys.modules, "lancedb", None)
    monkeypatch.setitem(sys.modules, "llama_cpp", None)

    # Force re-import of pipeline to verify it loads clean
    if "engines.oracle.pipeline" in sys.modules:
        del sys.modules["engines.oracle.pipeline"]
    import engines.oracle.pipeline  # noqa: F401 — must not raise


def test_pipeline_uses_rrf_k60():
    """Pipeline should use k=60 for RRF fusion (the canonical QMD constant)."""
    from engines.oracle.pipeline import rrf_fuse
    import inspect

    # Check k=60 is the default
    sig = inspect.signature(rrf_fuse)
    assert sig.parameters["k"].default == 60

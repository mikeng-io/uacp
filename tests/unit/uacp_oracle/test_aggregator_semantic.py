"""Task 8b tests — semantic wiring in the Oracle aggregator.

Verifies:
  - _semantic_packets real implementation runs the pipeline
  - store unavailable (deps absent / enabled=false) → sources_skipped contains 'semantic', no raise
  - retrieval-led phases get semantic packets when store is available
  - poison-dep floor path: lancedb+llama_cpp+httpx poisoned → floor packets only,
    semantic in sources_skipped, NO raise
"""

from __future__ import annotations

import sys

import pytest

import engines.oracle.aggregator as agg
from engines.oracle.packets import ProviderPacket  # noqa: F401 — used in isinstance check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enabled_cfg(extra: dict | None = None) -> dict:
    base = {
        "enabled": True,
        "store": "lancedb",
        "index_path": ".uacp/knowledge/indexes/",
        "embedding": {"url": "", "model": "bge-m3"},
        "rerank": {"url": "", "model": "qwen3-reranker-0.6b"},
    }
    if extra:
        base.update(extra)
    return base


# ---------------------------------------------------------------------------
# _semantic_packets unit (wiring without going through oracle_query)
# ---------------------------------------------------------------------------


def test_semantic_packets_returns_list_of_provider_packets(monkeypatch, tmp_path) -> None:
    """With a working fake store, _semantic_packets returns ProviderPackets."""

    class _FakeStore:
        def available(self) -> bool:
            return True

        def dense_search(self, v, k):
            return []

        def fts_search(self, q, k):
            return [
                {
                    "id": "L1",
                    "type": "lesson",
                    "domains": ["auth"],
                    "invariants": ["I1"],
                    "bes": 0.8,
                    "severity": "HIGH",
                    "eligible": 2,
                    "body": "body text",
                },
            ]

        def rrf_hybrid(self, v, q, k):
            return self.fts_search(q, k)

    monkeypatch.setattr(
        "engines.oracle.aggregator._get_oracle_store",
        lambda *a, **k: _FakeStore(),
    )

    packets = agg._semantic_packets(
        workspace=tmp_path,
        phase="propose",
        project="p",
        domains=["auth"],
        query="auth bug",
        oracle_cfg=_enabled_cfg(),
    )
    assert isinstance(packets, list)
    assert all(isinstance(p, ProviderPacket) for p in packets)


def test_semantic_packets_store_unavailable_raises(monkeypatch, tmp_path) -> None:
    """When the store is not available, _semantic_packets raises.

    The plan specifies: store unavailable -> records 'semantic' in sources_skipped.
    The mechanism: _semantic_packets raises _SemanticUnavailable, aggregator catches
    Exception, appends 'semantic' to sources_skipped. This is not an error — it is
    the designed graceful-degradation signal.
    """
    # Poison lancedb via monkeypatch (auto-restored; no reload needed)
    monkeypatch.setitem(sys.modules, "lancedb", None)

    with pytest.raises(Exception):
        agg._semantic_packets(
            workspace=tmp_path,
            phase="propose",
            project="p",
            domains=["auth"],
            query="auth bug",
            oracle_cfg=_enabled_cfg(),
        )


def test_semantic_packets_oracle_disabled_returns_empty(tmp_path) -> None:
    """oracle_cfg enabled=false -> _semantic_packets returns [] immediately."""
    packets = agg._semantic_packets(
        workspace=tmp_path,
        phase="propose",
        project="p",
        domains=["auth"],
        query="q",
        oracle_cfg={"enabled": False},
    )
    assert packets == []


def test_oracle_query_semantic_exception_recorded_in_skipped(monkeypatch, tmp_path) -> None:
    """Any exception from _semantic_packets -> 'semantic' in sources_skipped, no raise.

    The aggregator wraps the semantic call in try/except — failures are absorbed.
    """
    monkeypatch.setattr(
        "engines.oracle.aggregator._get_oracle_store",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("blown up")),
    )
    # oracle_query must NOT raise; must record semantic in sources_skipped
    result = agg.oracle_query(
        workspace=tmp_path,
        phase="propose",
        project="p",
        query="q",
        oracle_cfg=_enabled_cfg(),
    )
    assert "semantic" in result["metadata"]["sources_skipped"]
    assert "packets" in result


# ---------------------------------------------------------------------------
# oracle_query integration — semantic wired end-to-end
# ---------------------------------------------------------------------------


def test_oracle_query_retrieval_led_phase_gets_semantic_packets(monkeypatch, tmp_path) -> None:
    """For a retrieval-led phase with a working store, semantic packets appear in results."""

    class _FakeStore:
        def available(self):
            return True

        def dense_search(self, v, k):
            return []

        def fts_search(self, q, k):
            return [
                {
                    "id": "L1",
                    "type": "lesson",
                    "domains": ["auth"],
                    "invariants": [],
                    "bes": 0.7,
                    "severity": "MEDIUM",
                    "eligible": 1,
                    "body": "body",
                }
            ]

        def rrf_hybrid(self, v, q, k):
            return self.fts_search(q, k)

    monkeypatch.setattr(
        "engines.oracle.aggregator._get_oracle_store",
        lambda *a, **k: _FakeStore(),
    )

    result = agg.oracle_query(
        workspace=tmp_path,
        phase="propose",
        project="p",
        domains=["auth"],
        query="auth bug",
        oracle_cfg=_enabled_cfg(),
    )
    semantic_packets = [p for p in result["packets"] if p.source == "corpus"]
    assert semantic_packets, "expected corpus packets from semantic pipeline"
    assert "semantic" not in result["metadata"]["sources_skipped"]


def test_floor_backfills_under_semantic_without_starving(monkeypatch, tmp_path) -> None:
    """#148 council MAJOR: on the ENABLED path the deterministic floor must LAYER UNDER the
    semantic tier (backfill remaining budget, deduped) — never fill the whole limit and
    starve the ML-ranked results. With a working store AND a seeded corpus, both semantic
    ('corpus') and floor ('corpus-floor') packets appear, and a doc surfaced by both is
    deduped."""
    from engines.domain.corpus import Lesson

    lessons_dir = tmp_path / ".uacp" / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    # Extra corpus docs so the floor has content, + one whose id the semantic tier also returns.
    for i in range(3):
        les = Lesson(id=f"floor-{i}", title="t", project="p", domains=["auth"], bes=0.6)
        (lessons_dir / f"{les.id}.md").write_text(les.to_okf(), encoding="utf-8")
    dup = Lesson(id="L1", title="dup", project="p", domains=["auth"])
    (lessons_dir / "L1.md").write_text(dup.to_okf(), encoding="utf-8")

    class _FakeStore:
        def available(self):
            return True

        def dense_search(self, v, k):
            return []

        def fts_search(self, q, k):
            return [
                {
                    "id": "L1",
                    "type": "lesson",
                    "domains": ["auth"],
                    "invariants": [],
                    "bes": 0.7,
                    "severity": "MEDIUM",
                    "eligible": 1,
                    "body": "body",
                }
            ]

        def rrf_hybrid(self, v, q, k):
            return self.fts_search(q, k)

    monkeypatch.setattr("engines.oracle.aggregator._get_oracle_store", lambda *a, **k: _FakeStore())

    result = agg.oracle_query(
        workspace=tmp_path,
        phase="propose",
        project="p",
        domains=["auth"],
        query="auth",
        oracle_cfg=_enabled_cfg(),
    )
    sources = [p.source for p in result["packets"]]
    assert "corpus" in sources, f"semantic tier starved by the floor: {sources}"
    assert "corpus-floor" in sources, f"floor absent on the enabled path: {sources}"
    ids = [p.payload["id"] for p in result["packets"] if isinstance(p.payload, dict)]
    assert ids.count("L1") == 1, f"doc surfaced by both tiers not deduped: {ids}"


def test_oracle_query_semantic_skipped_when_store_unavailable(monkeypatch, tmp_path) -> None:
    """Store unavailable (no lancedb) -> semantic in sources_skipped, no raise."""
    monkeypatch.setitem(sys.modules, "lancedb", None)

    result = agg.oracle_query(
        workspace=tmp_path,
        phase="propose",
        project="p",
        query="q",
        oracle_cfg=_enabled_cfg(),
    )
    assert "semantic" in result["metadata"]["sources_skipped"]
    assert "packets" in result


# ---------------------------------------------------------------------------
# Poison-dep floor path (the load-bearing floor claim)
# ---------------------------------------------------------------------------


def test_poisoned_deps_floor_path_no_raise(monkeypatch, tmp_path) -> None:
    """With lancedb+llama_cpp+httpx poisoned, oracle_query for a retrieval-led phase:
    - 'semantic' in sources_skipped
    - does NOT raise
    """
    monkeypatch.setitem(sys.modules, "lancedb", None)
    monkeypatch.setitem(sys.modules, "llama_cpp", None)
    monkeypatch.setitem(sys.modules, "httpx", None)

    result = agg.oracle_query(
        workspace=tmp_path,
        phase="propose",
        project="p",
        query="auth bug",
        oracle_cfg=_enabled_cfg(),
    )

    assert "semantic" in result["metadata"]["sources_skipped"], (
        f"semantic not in sources_skipped: {result['metadata']['sources_skipped']}"
    )
    assert "packets" in result
    # Must have succeeded (no exception reaching here)


def test_poisoned_deps_floor_import_clean(monkeypatch) -> None:
    """The aggregator module must import cleanly even with ML deps poisoned."""
    monkeypatch.setitem(sys.modules, "lancedb", None)
    monkeypatch.setitem(sys.modules, "llama_cpp", None)

    # Re-import aggregator with poisoned modules; must not raise
    if "engines.oracle.aggregator" in sys.modules:
        del sys.modules["engines.oracle.aggregator"]
    import engines.oracle.aggregator  # noqa: F401 — must import clean

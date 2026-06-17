"""Tests for the oracle vector+FTS store interface and LanceDB impl.

The store dep (lancedb) is OPTIONAL + lazily imported. available() is the single
gate the resolver/pipeline checks before using semantic legs. The floor must run
with the dep absent: poisoning sys.modules['lancedb'] must NOT crash imports.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from engines.oracle.store import StoreUnavailable, VectorStore, get_store

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"


def test_store_interface_has_required_methods():
    for m in ("upsert", "dense_search", "fts_search", "rrf_hybrid", "available"):
        assert hasattr(VectorStore, m)


def test_lancedb_store_reports_unavailable_when_dep_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "lancedb", None)  # simulate not installed
    store = get_store("lancedb", index_path="/tmp/does-not-matter")
    assert store.available() is False


def test_lancedb_store_reports_available_when_dep_present(monkeypatch):
    import types

    fake = types.ModuleType("lancedb")
    monkeypatch.setitem(sys.modules, "lancedb", fake)
    store = get_store("lancedb", index_path="/tmp/x")
    assert store.available() is True


def test_get_store_unknown_backend_raises():
    with pytest.raises(StoreUnavailable):
        get_store("redis-vector", index_path="/tmp/x")


def test_sqlite_vec_is_documented_alternate_behind_interface():
    # sqlite-vec is the lighter swap-in; only available() needs to work (stub).
    store = get_store("sqlite-vec", index_path="/tmp/x")
    assert store.available() is False


def test_floor_path_does_not_require_store():
    # The store module must import with no ML deps present. Use a fresh
    # subprocess so a reload can't rebind StoreUnavailable for sibling tests.
    import subprocess

    code = (
        "import sys; sys.modules['lancedb'] = None; "
        "import engines.oracle.store as s; "
        "assert s.get_store('lancedb', index_path='/tmp/x').available() is False; "
        "print('floor imports clean')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(_CORE_SCRIPTS)},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "floor imports clean" in proc.stdout


def test_query_shaping_maps_rows_to_dicts(monkeypatch):
    # Pure logic: rrf_hybrid shapes a fake store's native rows into plain dicts.
    import types

    captured = {}

    class _FakeTable:
        def search(self, *a, **k):
            captured["search"] = (a, k)
            return self

        def limit(self, k):
            captured["limit"] = k
            return self

        def to_list(self):
            return [
                {"id": "L1", "domains": ["auth"], "_distance": 0.1, "extra": 1},
                {"id": "K1", "domains": ["auth"], "_relevance_score": 0.9},
            ]

    class _FakeDB:
        def open_table(self, name):
            return _FakeTable()

    fake = types.ModuleType("lancedb")
    fake.connect = lambda path: _FakeDB()  # noqa: ARG005
    monkeypatch.setitem(sys.modules, "lancedb", fake)

    store = get_store("lancedb", index_path="/tmp/x")
    rows = store.rrf_hybrid(vector=[0.1, 0.2], query="auth", k=5)
    assert [r["id"] for r in rows] == ["L1", "K1"]
    assert all(isinstance(r, dict) for r in rows)


def test_dense_search_raises_when_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "lancedb", None)
    store = get_store("lancedb", index_path="/tmp/x")
    with pytest.raises(StoreUnavailable):
        store.dense_search([0.1], k=5)

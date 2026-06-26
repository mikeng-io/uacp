"""E2E (capsule #3 follow-on): the code-INDEX builder (design node 32 production).

UACP consumes the SCIP index (CF-D9); this thin wrapper PRODUCES it by running Codeflair's
tree-sitter ingest into the conventioned per-run path. Fail-closed when the optional ingester dep is
absent (no crash, no partial db). Where the dep is present, the built index resolves real symbols
through the slice-3 code plane end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from engines.code_index_build import build_code_index
from engines.code_plane import index_path, resolve_symbol


def test_build_writes_to_the_conventioned_index_path(tmp_path: Path):
    # the builder MUST target where engines.code_plane reads — the producer/consumer contract.
    res = build_code_index(tmp_path, tmp_path)
    assert res["index"] == str(index_path(tmp_path))


def test_build_is_fail_closed_when_ingester_unavailable(tmp_path: Path, monkeypatch):
    # simulate the REAL optional dep (tree_sitter_languages) being absent — NOT all of codeflair
    # (codeflair.store is always present): build is a no-op with status, never a crash, never a
    # partial db -> the code plane then ERRORs (fail-closed), never a false pass.
    import builtins

    real_import = builtins.__import__

    def _no_treesitter(name, *a, **k):
        if name == "tree_sitter_languages" or name.startswith("tree_sitter_languages."):
            raise ImportError("simulated: tree-sitter optional dep absent")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_treesitter)
    res = build_code_index(tmp_path, tmp_path)
    assert res["ok"] is False and "unavailable" in res["reason"]
    assert not index_path(tmp_path).exists()  # no partial index left behind


def _install_fake_ingester(monkeypatch, fn):
    # codeflair.treesitter_ingest can't import here (tree-sitter dep absent), so inject a fake
    # module exposing a controllable index_repo_tree_sitter; build_code_index uses the REAL Store.
    import sys
    import types

    mod = types.ModuleType("codeflair.treesitter_ingest")
    mod.index_repo_tree_sitter = fn
    monkeypatch.setitem(sys.modules, "codeflair.treesitter_ingest", mod)


def test_build_exception_leaves_no_partial_index(tmp_path: Path, monkeypatch):
    # Council BLOCKER: a crash mid-ingest must NOT publish a partial db the resolver reads as truth.
    from codeflair.store import Store, Symbol

    def _crash(store: Store, repo_path: str, **_):
        store.add_symbol(Symbol(symbol="scip . . `foo`().", lang="python", file="a.py", name="foo"))
        store.con.commit()
        raise RuntimeError("boom mid-ingest")

    _install_fake_ingester(monkeypatch, _crash)
    res = build_code_index(tmp_path, tmp_path)
    assert res["ok"] is False and "boom" in res["reason"]
    assert not index_path(tmp_path).exists()  # nothing published at the canonical path
    assert resolve_symbol(tmp_path, "foo")[0] == "ERROR"  # fail-closed, no partial-db false resolve


def test_rebuild_is_fresh_not_appended(tmp_path: Path, monkeypatch):
    # Council HIGH: a rebuild fully REPLACES the prior index — a since-removed symbol must not stay.
    from types import SimpleNamespace

    from codeflair.store import Store, Symbol

    def _ingest(name):
        def _fn(store: Store, repo_path: str, **_):
            store.add_symbol(
                Symbol(symbol=f"scip . . `{name}`().", lang="python", file="a.py", name=name)
            )
            store.con.commit()
            return SimpleNamespace(files=1, symbols=1, edges=0)

        return _fn

    _install_fake_ingester(monkeypatch, _ingest("old_func"))
    assert build_code_index(tmp_path, tmp_path)["ok"] is True
    assert resolve_symbol(tmp_path, "old_func")[0] == "PASS"
    _install_fake_ingester(monkeypatch, _ingest("new_func"))  # rebuild ingesting a DIFFERENT symbol
    assert build_code_index(tmp_path, tmp_path)["ok"] is True
    assert resolve_symbol(tmp_path, "new_func")[0] == "PASS"
    assert resolve_symbol(tmp_path, "old_func")[0] == "FAIL"  # stale symbol purged, not appended


def test_built_index_resolves_a_real_symbol_end_to_end(tmp_path: Path):
    # the real path — exercised only where codeflair's tree-sitter dep is installed.
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def settle_route():\n    return 1\n", encoding="utf-8")
    res = build_code_index(tmp_path, repo)
    assert res["ok"] is True and res["symbols"] >= 1, res
    # the slice-3 resolver now finds the real symbol in the produced index.
    assert resolve_symbol(tmp_path, "settle_route")[0] == "PASS"
    assert resolve_symbol(tmp_path, "does_not_exist")[0] == "FAIL"

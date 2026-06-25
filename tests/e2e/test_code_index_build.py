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
    # simulate the optional dep being absent: build is a no-op with status, never a crash, never a
    # partial db -> the code plane then ERRORs (fail-closed), never a false pass.
    import builtins

    real_import = builtins.__import__

    def _no_codeflair(name, *a, **k):
        if name.startswith("codeflair"):
            raise ImportError("simulated: codeflair tree-sitter ingester unavailable")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_codeflair)
    res = build_code_index(tmp_path, tmp_path)
    assert res["ok"] is False and "unavailable" in res["reason"]
    assert not index_path(tmp_path).exists()  # no partial index left behind


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

"""Freshness substrate (P1): watermark, per-file/per-source population at ingest,
per-file hash compare, and per-worktree store keying (OD-4).

Detection only — no live/unreconciled overlay tags (those are P2).
"""

from pathlib import Path

import pytest

from codeflair import Store, compare_file, content_hash, default_store_path
from codeflair.scip_ingest import SCIP_TOOL_VERSION, ingest_scip_json

# A tiny SCIP index over two real repo files plus one stdlib doc (which must be skipped).
M = "scip-go gomod example.com/m v1.0.0 `example.com/m/p`"
FOO, BAR = f"{M}/Foo().", f"{M}/Bar()."
_DEF, _REF = 1, 0


def _occ(symbol: str, line: int, role: int) -> dict:
    return {"symbol": symbol, "range": [line, 0, 10], "symbol_roles": role}


def _scip_index() -> dict:
    # a.go defines Foo and references Bar; b.go defines Bar. Plus a stdlib doc that
    # ingest skips (absolute path) — it must NOT get a freshness row.
    return {
        "documents": [
            {
                "relative_path": "a.go",
                "occurrences": [_occ(FOO, 10, _DEF), _occ(BAR, 12, _REF)],
            },
            {"relative_path": "b.go", "occurrences": [_occ(BAR, 5, _DEF)]},
            {
                "relative_path": "/usr/local/go/src/fmt/print.go",
                "occurrences": [_occ(FOO, 1, _DEF)],
            },
        ]
    }


# -- watermark ---------------------------------------------------------------
def test_unset_watermark_is_none():
    assert Store().watermark() is None


def test_watermark_round_trips_and_stays_single_row():
    s = Store()
    s.set_watermark("commit-aaa", "2026-01-01T00:00:00Z")
    assert s.watermark() == ("commit-aaa", "2026-01-01T00:00:00Z")
    # re-stamping replaces in place — it is a store-level single row, not an append log
    s.set_watermark("commit-bbb", "2026-02-02T00:00:00Z")
    assert s.watermark() == ("commit-bbb", "2026-02-02T00:00:00Z")
    assert s.con.execute("SELECT COUNT(*) FROM watermark").fetchone()[0] == 1


# -- population at ingest (SCIP — the path exercised without the tree-sitter dep) ----
def test_scip_ingest_populates_freshness_from_real_bytes(tmp_path: Path):
    """After a SCIP ingest with file bytes, watermark + per-source freshness rows EXIST
    and match the ACTUALLY-INGESTED files, with hashes derived from real content (not
    hand-inserted). Non-vacuity: each stored hash equals sha256 of the on-disk bytes."""
    (tmp_path / "a.go").write_bytes(b"package p\nfunc Foo() { Bar() }\n")
    (tmp_path / "b.go").write_bytes(b"package p\nfunc Bar() {}\n")
    file_contents = {
        "a.go": (tmp_path / "a.go").read_bytes(),
        "b.go": (tmp_path / "b.go").read_bytes(),
    }

    s = Store()
    s.set_watermark("commit-xyz", "2026-06-27T00:00:00Z")
    ingest_scip_json(s, _scip_index(), file_contents=file_contents, commit_sha="commit-xyz")

    rows = dict(
        (file, (src, ch, csha, tv))
        for file, src, ch, csha, tv in s.con.execute(
            "SELECT file, source, content_hash, commit_sha, tool_version FROM freshness"
        ).fetchall()
    )
    # exactly the two ingested repo files — the skipped stdlib doc gets NO row
    assert set(rows) == {"a.go", "b.go"}
    for file in ("a.go", "b.go"):
        src, ch, csha, tv = rows[file]
        assert src == "scip"
        assert ch == content_hash(file_contents[file])  # hash IS of the real bytes
        assert csha == "commit-xyz"  # commit threaded through
        assert tv == SCIP_TOOL_VERSION
    # files table mirrors the per-file hash; watermark commit matches the freshness commit
    assert s.file_hash("a.go") == content_hash(file_contents["a.go"])
    assert s.watermark()[0] == rows["a.go"][2]  # repo_commit == freshness commit_sha


def test_scip_ingest_without_bytes_writes_no_freshness():
    """Backward compatible: ingesting without file_contents records no freshness rows
    (the existing hermetic SCIP tests still pass), so a row only ever means real bytes."""
    s = Store()
    ingest_scip_json(s, _scip_index())
    assert s.con.execute("SELECT COUNT(*) FROM freshness").fetchone()[0] == 0
    assert s.con.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 0


def test_freshness_skips_bytes_for_non_ingested_paths():
    """A path supplied in file_contents but NOT an ingested repo doc gets no row — rows
    track what was ACTUALLY ingested, not whatever bytes the caller happened to pass."""
    s = Store()
    contents = {"a.go": b"x", "b.go": b"y", "ghost.go": b"never ingested"}
    ingest_scip_json(s, _scip_index(), file_contents=contents)
    files = {r[0] for r in s.con.execute("SELECT file FROM freshness").fetchall()}
    assert files == {"a.go", "b.go"}  # ghost.go absent


# -- per-file hash compare (detection only) ----------------------------------
def test_compare_file_detects_clean_stale_unknown():
    s = Store()
    original = b"package p\nfunc Foo() {}\n"
    ingest_scip_json(
        s,
        {"documents": [{"relative_path": "a.go", "occurrences": [_occ(FOO, 1, _DEF)]}]},
        file_contents={"a.go": original},
    )
    assert compare_file(s, "a.go", original) == "clean"  # matches the indexed hash
    assert compare_file(s, "a.go", original + b"// edited\n") == "stale"  # diverged
    assert compare_file(s, "never_indexed.go", b"anything") == "unknown"  # not in index


def test_record_freshness_rejects_overlay_and_coupling_sources():
    """Freshness is per persisted EDGE source; lsp (overlay) / grep (coupling) are not
    persisted sources, so they can never carry a freshness row."""
    s = Store()
    for bad in ("lsp", "grep", "co_change"):
        with pytest.raises(ValueError, match="unknown freshness source"):
            s.record_freshness(bad, "a.go", "deadbeef")


# -- per-worktree store keying (OD-4) ----------------------------------------
def test_default_store_path_resolves_under_worktree_root(tmp_path: Path):
    p = Path(default_store_path(tmp_path))
    assert p == tmp_path / ".codeflair" / "index.db"
    assert tmp_path in p.parents  # genuinely under the given worktree root
    assert not p.parent.exists()  # no side effect without create=True

    created = Path(default_store_path(tmp_path, create=True))
    assert created.parent.is_dir()  # .codeflair/ made on demand


def test_default_store_path_keys_distinct_worktrees_apart(tmp_path: Path):
    a, b = tmp_path / "wt-a", tmp_path / "wt-b"
    assert default_store_path(a) != default_store_path(b)


def test_codeflair_cache_dir_is_gitignored():
    """`.codeflair/` must be gitignored (10-freshness hygiene). Find the nearest ancestor
    .gitignore and assert it ignores the cache dir."""
    here = Path(__file__).resolve()
    ignored = False
    for parent in here.parents:
        gi = parent / ".gitignore"
        if gi.exists() and any(
            line.strip().rstrip("/") == ".codeflair" for line in gi.read_text().splitlines()
        ):
            ignored = True
            break
    assert ignored, ".codeflair/ is not ignored by any ancestor .gitignore"


# -- tree-sitter population (gated: optional dep absent in the default dev venv) ------
def test_tree_sitter_ingest_populates_freshness():
    pytest.importorskip("tree_sitter_languages")
    from codeflair.treesitter_ingest import (  # noqa: PLC0415
        TREE_SITTER_TOOL_VERSION,
        ingest_tree_sitter,
    )

    py = b"def helper():\n    return 1\n"
    s = Store()
    ingest_tree_sitter(s, {"m.py": ("python", py), "x.rb": ("ruby", b"def f; end")})
    rows = {
        file: (src, ch, tv)
        for file, src, ch, tv in s.con.execute(
            "SELECT file, source, content_hash, tool_version FROM freshness"
        ).fetchall()
    }
    # only the supported-language file is ingested → only it gets a row
    assert set(rows) == {"m.py"}
    assert rows["m.py"] == ("tree_sitter", content_hash(py), TREE_SITTER_TOOL_VERSION)
    assert compare_file(s, "m.py", py) == "clean"
    assert compare_file(s, "m.py", py + b"# edit\n") == "stale"

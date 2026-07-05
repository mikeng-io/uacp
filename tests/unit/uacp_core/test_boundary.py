"""Unit tests for the shared glob-aware file boundary (design node 04).

``FileBoundary`` is the ONE predicate both the diff-containment outcome side and the
cascade-forecast prediction side use. These lock its semantics directly (the e2e
diff-containment teeth in test_scope_conformance.py are the broader regression net)."""

from __future__ import annotations

from pathlib import Path

from engines.domain.boundary import FileBoundary, is_contained, resolve_under_root


def test_glob_free_write_path_allows_whole_subtree():
    b = FileBoundary(Path("/repo"), ["src"])
    # A glob-free dir allows its entire subtree (directory-prefix containment).
    assert b.is_out_of_boundary("src/pkg/mod.py") is False
    assert b.is_out_of_boundary("other/mod.py") is True


def test_glob_write_path_constrains_suffix():
    b = FileBoundary(Path("/repo"), ["docs/*.md"])
    assert b.is_out_of_boundary("docs/guide.md") is False
    # A .py under a *.md glob is out of boundary — the suffix constraint must hold.
    assert b.is_out_of_boundary("docs/rogue.py") is True


def test_double_star_matches_deep():
    b = FileBoundary(Path("/repo"), ["src/**"])
    assert b.is_out_of_boundary("src/a/b/c.py") is False
    assert b.is_out_of_boundary("rogue.py") is True


def test_governed_namespace_is_in_boundary(tmp_path: Path):
    # base_dir(root) resolves .uacp/ — governed-writer territory is always in-boundary.
    b = FileBoundary(tmp_path, [])
    assert b.is_out_of_boundary(".uacp/state/x.yaml") is False
    assert b.is_out_of_boundary("rogue.py") is True


def test_codeflair_cache_exempt():
    b = FileBoundary(Path("/repo"), ["src/**"])
    assert b.is_out_of_boundary(".codeflair/index.db") is False


def test_escape_is_out_of_boundary(tmp_path: Path):
    # A path that resolves OUTSIDE the workspace (traversal) is an escape.
    b = FileBoundary(tmp_path, ["src/**"])
    assert b.is_out_of_boundary("../evil.py") is True


def test_offenders_preserves_input_order():
    b = FileBoundary(Path("/repo"), ["src/**"])
    rels = ["src/ok.py", "a.py", "src/deep/ok2.py", "b.py"]
    assert b.offenders(rels) == ["a.py", "b.py"]


def test_resolve_under_root_and_is_contained(tmp_path: Path):
    root = tmp_path.resolve()
    assert resolve_under_root(root, "sub/x.py") == root / "sub" / "x.py"
    assert resolve_under_root(root, "../escape") is None
    assert is_contained(root / "a" / "b", root / "a") is True
    assert is_contained(root / "a", root / "a" / "b") is False

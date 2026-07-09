"""Unit tests for uacp-core filesystem utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from filesystem import _resolve_uacp_path, _write_uacp_file


class TestResolveUacpPath:
    """Tests for _resolve_uacp_path boundary enforcement."""

    def test_resolves_relative_path(self, temp_uacp_root: Path):
        root = temp_uacp_root
        result = _resolve_uacp_path("state/runs/test.yaml", root)
        assert result.resolve() == (root / "state" / "runs" / "test.yaml").resolve()

    def test_rejects_absolute_path(self, temp_uacp_root: Path):
        root = temp_uacp_root
        with pytest.raises(ValueError, match="must be UACP-root-relative"):
            _resolve_uacp_path("/etc/passwd", root)

    def test_rejects_parent_traversal(self, temp_uacp_root: Path):
        root = temp_uacp_root
        with pytest.raises(ValueError, match="parent path segments"):
            _resolve_uacp_path("../etc/passwd", root)

    def test_rejects_empty_segments(self, temp_uacp_root: Path):
        root = temp_uacp_root
        # POSIX pathlib normalizes '.' and empty segments, so the only
        # segment that survives and poses a security risk is '..'.
        with pytest.raises(ValueError, match="parent path segments"):
            _resolve_uacp_path("state/../runs", root)

    def test_rejects_symlink_traversal(self, temp_uacp_root: Path):
        root = temp_uacp_root
        # Create a symlink inside UACP_ROOT that points outside. These tests
        # exercise the layout-agnostic _resolve_uacp_path primitive against an
        # arbitrary subdir under root, so create it explicitly (the fixture's
        # standard dirs now live under .uacp/).
        (root / "state").mkdir(parents=True, exist_ok=True)
        symlink_dir = root / "state" / "evil"
        symlink_dir.symlink_to("/tmp")
        with pytest.raises(ValueError, match="symlink"):
            _resolve_uacp_path("state/evil/file.yaml", root)

    def test_rejects_root_itself(self, temp_uacp_root: Path):
        root = temp_uacp_root
        with pytest.raises(ValueError, match="must point to a file"):
            _resolve_uacp_path("", root)

    def test_rejects_escape_via_deep_traversal(self, temp_uacp_root: Path):
        root = temp_uacp_root
        with pytest.raises(ValueError):
            _resolve_uacp_path("state/runs/../../etc/passwd", root)


class TestWriteUacpFile:
    """Tests for _write_uacp_file atomic writes."""

    def test_writes_file(self, temp_uacp_root: Path):
        root = temp_uacp_root
        target = root / "state" / "test.txt"
        _write_uacp_file(target, "hello world")
        assert target.read_text() == "hello world"

    def test_creates_parent_directories(self, temp_uacp_root: Path):
        root = temp_uacp_root
        target = root / "state" / "deep" / "nested" / "file.txt"
        _write_uacp_file(target, "content")
        assert target.exists()
        assert target.read_text() == "content"

    def test_overwrites_existing(self, temp_uacp_root: Path):
        root = temp_uacp_root
        target = root / "state" / "existing.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("old")
        _write_uacp_file(target, "new")
        assert target.read_text() == "new"

    def test_leaves_no_temp_file_after_success(self, temp_uacp_root: Path):
        """The atomic temp file is renamed onto the target — none is left behind."""
        root = temp_uacp_root
        target = root / "state" / "clean.yaml"
        _write_uacp_file(target, "kind: uacp.scope\nstatus: ready\n")
        strays = [p.name for p in target.parent.iterdir() if p.name != "clean.yaml"]
        assert strays == [], strays

    def test_write_is_atomic_on_failure(self, temp_uacp_root: Path, monkeypatch):
        """#103-W1: if the atomic rename fails, the EXISTING target is left intact
        (never truncated/partial) and no temp file is orphaned."""
        import os as _os

        root = temp_uacp_root
        target = root / "state" / "atomic.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ORIGINAL")

        def _boom(_src, _dst):
            raise OSError("replace boom")

        monkeypatch.setattr(_os, "replace", _boom)
        with pytest.raises(OSError, match="replace boom"):
            _write_uacp_file(target, "NEW PARTIAL")
        # The old content survives untouched (no truncation) ...
        assert target.read_text() == "ORIGINAL"
        # ... and the failed write left no stray temp file.
        strays = [p.name for p in target.parent.iterdir() if p.name != "atomic.txt"]
        assert strays == [], strays

    def test_malformed_yaml_writes_nothing(self, temp_uacp_root: Path):
        """Fail-closed validation runs BEFORE any file is created — a malformed .yaml
        never reaches disk and leaves no temp."""
        root = temp_uacp_root
        target = root / "state" / "bad.yaml"
        with pytest.raises(Exception):
            _write_uacp_file(target, "::: not: valid: yaml: [[[")
        assert not target.exists()
        # Validation precedes even the parent mkdir, so nothing was created at all.
        state_dir = root / "state"
        assert not state_dir.exists() or list(state_dir.iterdir()) == []

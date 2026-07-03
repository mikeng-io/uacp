"""Unit tests for the forecast-record atomic writer (design node 04 / K2) and the
default-branch merge-base audit helper (K3).

``write_forecast_record`` writes via a same-dir temp file + ``os.replace`` (atomic), so a
half-written record can never be observed and a failed write leaves NO partial file.
``default_branch_merge_base`` returns the merge-base audit stamp, or None when unresolvable.
Neither ever raises."""

from __future__ import annotations

import os
from pathlib import Path

import engines.io.forecastio as forecastio
from engines.io import default_branch_merge_base
from engines.io.forecastio import (
    forecast_record_path,
    load_forecast_record,
    write_forecast_record,
)

_RUN = "run-forecast-io"


def test_write_then_load_roundtrips(tmp_path: Path):
    assert write_forecast_record(tmp_path, _RUN, {"predicted": ["a.py"], "n": 1}) is True
    rec, err = load_forecast_record(tmp_path, _RUN)
    assert err is None
    assert rec == {"predicted": ["a.py"], "n": 1}


def test_replace_failure_returns_false_and_leaves_no_partial(tmp_path: Path, monkeypatch):
    """An os.replace failure -> False, the temp is cleaned, and NO partial target file is
    left (partial-file impossible by construction: only an atomic rename ever creates it)."""

    def _boom(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr(forecastio.os, "replace", _boom)
    assert write_forecast_record(tmp_path, _RUN, {"predicted": ["a.py"]}) is False

    path = forecast_record_path(tmp_path, _RUN)
    assert path is not None and not path.exists(), "no partial target file"
    # No leftover temp files in the verification dir.
    leftovers = [p for p in path.parent.iterdir() if p.name.startswith(f".{path.name}.")]
    assert leftovers == [], f"temp files must be cleaned, found: {leftovers}"


def test_replace_failure_does_not_corrupt_an_existing_record(tmp_path: Path, monkeypatch):
    """A failed rewrite leaves the PRIOR record intact (the old file is never truncated —
    the write goes to a temp and only an atomic replace would swap it in)."""
    assert write_forecast_record(tmp_path, _RUN, {"predicted": ["first"]}) is True

    monkeypatch.setattr(forecastio.os, "replace", lambda _s, _d: (_ for _ in ()).throw(OSError()))
    assert write_forecast_record(tmp_path, _RUN, {"predicted": ["second"]}) is False

    rec, err = load_forecast_record(tmp_path, _RUN)
    assert err is None
    assert rec == {"predicted": ["first"]}, "the prior record survives a failed rewrite"


def _git(root: Path, *args: str) -> None:
    import subprocess

    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _head(root: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_merge_base_none_without_default_branch(tmp_path: Path):
    # A repo on a non-default branch with no main/master ref -> no candidate resolves -> None.
    _git(tmp_path, "init", "-q", "-b", "wip")
    (tmp_path / "f.txt").write_text("x\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "c")
    assert default_branch_merge_base(tmp_path) is None


def test_merge_base_none_when_not_a_repo(tmp_path: Path):
    assert default_branch_merge_base(tmp_path) is None


def test_merge_base_is_fork_point_when_head_advanced(tmp_path: Path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "f.txt").write_text("x\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "c0")
    fork = _head(tmp_path)
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "g.txt").write_text("y\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "c1")
    assert _head(tmp_path) != fork
    assert default_branch_merge_base(tmp_path) == fork

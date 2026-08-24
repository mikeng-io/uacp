"""Unit tests for the gitio substrate-production primitive (design/grounded-governance/01).

``diff_content`` extends the git witness from name-only (``changed_files``) to the FULL
unified diff CONTENT over the run's true ``merge-base(default, HEAD)..HEAD`` range — the review
substrate a correctness screening precipitates defects against. It reuses the SAME merge-base
logic as ``changed_files`` / ``default_branch_merge_base`` so the review diff and the containment
witness can never disagree about the range, and (like ``changed_files``) NEVER raises.

Fixtures use a REAL git-init'd tmp repo: a base commit on the default branch (``main``) and the
change committed on a feature branch that is HEAD, so ``merge-base(main, HEAD)`` is the base and
the diff carries the change hunk.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from engines.io import DiffContentResult, diff_content


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, rel: str, body: str, msg: str) -> None:
    f = path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    _git(path, "add", rel)
    _git(path, "commit", "-q", "-m", msg)


def test_non_repo_is_not_repo(tmp_path):
    # A plain dir (no .git) -> is_repo=False, no error, no text.
    res = diff_content(tmp_path)
    assert res == DiffContentResult(is_repo=False)
    assert res.is_repo is False
    assert res.text == ""
    assert res.error is None


def test_no_merge_base_reports_error(tmp_path):
    # A repo with a commit but NO default branch (only a uniquely-named branch, no main/master/
    # origin) -> is_repo=True with error="no merge-base"; a substrate cannot be produced.
    _init(tmp_path)
    _git(tmp_path, "checkout", "-q", "-b", "topic-only")
    _commit(tmp_path, "src/mod.py", "def x():\n    return 1\n", "base")
    res = diff_content(tmp_path)
    assert res.is_repo is True
    assert res.error == "no merge-base"
    assert res.text == ""
    # HEAD still resolves even without a merge-base.
    assert res.head_commit is not None and len(res.head_commit) == 40


def test_diff_content_returns_change_hunk(tmp_path):
    # Base commit A on main; the change committed as B on a feature branch that is HEAD, so
    # merge-base(main, HEAD)=A and the diff A..B carries the change CONTENT (not name-only).
    _init(tmp_path)
    _git(tmp_path, "checkout", "-q", "-b", "main")
    _commit(tmp_path, "src/mod.py", "def x():\n    return 1\n", "base")
    _git(tmp_path, "checkout", "-q", "-b", "feature")
    _commit(tmp_path, "src/mod.py", "def x():\n    return 999\n", "change")

    res = diff_content(tmp_path)
    assert res.is_repo is True
    assert res.error is None
    # base != head (the whole point — HEAD is ahead of the default branch).
    assert res.base_commit is not None and len(res.base_commit) == 40
    assert res.head_commit is not None and len(res.head_commit) == 40
    assert res.base_commit != res.head_commit
    # The FULL unified diff content: the hunk header + both the removed and added lines.
    assert "src/mod.py" in res.text
    assert "+    return 999" in res.text
    assert "-    return 1" in res.text
    assert "@@" in res.text  # a real unified-diff hunk, not --name-only


def test_never_raises_on_broken_gitfile(tmp_path):
    # A .git gitfile pointing at a nonexistent gitdir must be RETURNED as an error, never raised
    # (same defensive contract as changed_files).
    (tmp_path / ".git").write_text("gitdir: /nonexistent/broken-gitdir\n")
    res = diff_content(tmp_path)
    assert res.is_repo is True
    assert res.error is not None

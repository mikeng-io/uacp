"""Tests for skills/uacp-council/scripts/review_sandbox.sh.

The review sandbox provisions a disposable, isolated worktree so an `inspect`
reviewer's writes never reach the live tree (uacp-bridge Review Containment, Tier 2).
These tests prove the *isolation* and *fail-closed* behavior, not just that it runs.
"""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "uacp-council" / "scripts" / "review_sandbox.sh"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway git repo with one committed file."""
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "t@t.t", cwd=tmp_path)
    _git("config", "user.name", "t", cwd=tmp_path)
    (tmp_path / "tracked.txt").write_text("original\n")
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-qm", "init", cwd=tmp_path)
    return tmp_path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)


def test_script_exists_and_executable():
    assert SCRIPT.exists(), SCRIPT
    assert SCRIPT.stat().st_mode & 0o111, "review_sandbox.sh must be executable"


def test_provision_creates_isolated_sandbox(repo: Path):
    res = _run(repo, "provision", "sess-1")
    assert res.returncode == 0, res.stderr
    sandbox = Path(res.stdout.strip())
    assert sandbox.is_dir(), f"sandbox not created: {res.stdout!r} / {res.stderr!r}"
    assert sandbox == repo / ".worktrees" / "review-sess-1"
    # the committed scope is present in the sandbox
    assert (sandbox / "tracked.txt").read_text() == "original\n"

    # ISOLATION: a stray write in the sandbox must NOT reach the live tree
    (sandbox / "stray_write.txt").write_text("reviewer should not be able to do this to the real tree")
    (sandbox / "tracked.txt").write_text("MUTATED by reviewer\n")
    assert not (repo / "stray_write.txt").exists(), "sandbox write leaked to the live tree"
    assert (repo / "tracked.txt").read_text() == "original\n", "sandbox edit mutated the live tree"


def test_teardown_removes_sandbox(repo: Path):
    sandbox = Path(_run(repo, "provision", "sess-2").stdout.strip())
    assert sandbox.is_dir()
    res = _run(repo, "teardown", "sess-2")
    assert res.returncode == 0, res.stderr
    assert not sandbox.exists(), "teardown left the sandbox behind"


def test_provision_is_idempotent(repo: Path):
    a = _run(repo, "provision", "sess-3").stdout.strip()
    b = _run(repo, "provision", "sess-3").stdout.strip()
    assert a == b and Path(a).is_dir()


def test_missing_session_id_fails_closed(repo: Path):
    res = _run(repo, "provision")  # no session id
    assert res.returncode == 2, "must fail-closed (exit 2) on missing session id, not provision silently"


def test_session_id_is_path_sanitized(repo: Path):
    # A traversal-style id must be stripped to a safe segment under .worktrees/, never escape.
    res = _run(repo, "provision", "../../evil")
    assert res.returncode == 0, res.stderr
    sandbox = Path(res.stdout.strip())
    assert sandbox.parent == repo / ".worktrees", f"sandbox escaped containment dir: {sandbox}"
    assert ".." not in sandbox.name

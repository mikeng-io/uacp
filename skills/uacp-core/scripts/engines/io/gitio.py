"""Git read-access for the engines — ground truth for the diff-containment witness.

Same doctrine as :mod:`engines.io.loaders`: this module NEVER raises. Every
failure mode (git binary absent, unreadable repo, timeout, garbled output) is
returned inside :class:`GitDiffResult` so the calling engine converts it into
the right ``Violation`` instead of crashing the sweep.

Scope of the observation (v1, advisory):

* ``is_repo`` is decided by the presence of a ``.git`` entry AT the workspace
  root (dir for a normal checkout, file for a linked worktree). A workspace
  that is not itself a repo root returns ``is_repo=False`` — the engine treats
  that as a documented no-op, mirroring the absent-scope precedent.
* The changed set is the union of the UNCOMMITTED changes (``git status
  --porcelain``, which includes untracked-but-not-ignored files) and the
  COMMITTED-on-branch changes (``git diff --name-only <merge-base(default,
  HEAD)> HEAD`` where the default branch is the first of ``main``/``master``
  that resolves). The committed half self-disables when no default branch or
  merge-base exists (fresh repo, orphan branch); the uncommitted half is
  always observed. Ignored files are invisible by construction.
* Paths are repo-toplevel-relative as git prints them; because ``is_repo``
  requires ``.git`` at the workspace root, toplevel == workspace root.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_GIT_TIMEOUT_SECONDS = 10.0
# Default-branch baseline candidates for the committed-on-branch half, in priority
# order (design node 02 / K4): a linked worktree cut from a remote may carry only
# ``origin/*`` refs and NO local ``main``/``master`` — resolving those first stops the
# committed half from silently self-disabling and dropping committed changes. Each is
# tried with ``rev-parse --verify --quiet``; ``origin/HEAD`` resolves to its symbolic
# target automatically. (The same list is mirrored codeflair-side, fixed separately.)
_DEFAULT_BRANCH_CANDIDATES = (
    "origin/HEAD",
    "origin/main",
    "origin/master",
    "main",
    "master",
)


def _scrubbed_env() -> dict[str, str]:
    """A child environment with ``GIT_*`` and ``PYTHON*`` keys removed (``PATH`` kept).

    The engines' subprocess observations must not be steerable through inherited env
    (``GIT_DIR`` / ``GIT_CONFIG_*`` redirecting git; ``PYTHONPATH`` injection into a
    Python child). ``PATH`` is preserved so bare-name executables still resolve."""
    return {
        k: v for k, v in os.environ.items() if not (k.startswith("GIT_") or k.startswith("PYTHON"))
    }


@dataclass(frozen=True)
class GitDiffResult:
    """Outcome of observing a workspace's actual change set.

    is_repo — a ``.git`` entry exists at the workspace root.
    files   — workspace-relative changed paths (sorted, deduped). Only
              meaningful when ``is_repo`` and ``error is None``.
    error   — human-readable failure when the repo exists but could not be
              observed; the engine must surface this (fail-closed), never
              treat it as "no changes".
    """

    is_repo: bool
    files: tuple[str, ...] = ()
    error: str | None = None


def _run_git(root: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
        env=_scrubbed_env(),
    )
    return proc.returncode, proc.stdout, proc.stderr


def default_branch_merge_base(root: Path) -> str | None:
    """``merge-base(<default branch>, HEAD)`` using the SAME default-branch candidates as
    :func:`changed_files` (``origin/HEAD``, ``origin/main``, ``origin/master``, ``main``,
    ``master``, in order — the first that resolves).

    Returns the merge-base sha, or None when no default branch resolves / there is no
    merge-base (orphan branch) / the workspace is not a readable git repo. Design node 04
    (K3): this is the forecast record's ``base_commit`` — an AUDIT field (a record whose
    ``graph_stamp.commit`` differs from ``base_commit`` means HEAD advanced past the branch
    point before plan_exit, so the forecast may be hindsight). It is never a gate input.
    Never raises."""
    try:
        for candidate in _DEFAULT_BRANCH_CANDIDATES:
            rc, _, _ = _run_git(root, "rev-parse", "--verify", "--quiet", candidate)
            if rc != 0:
                continue
            rc, mb_out, _ = _run_git(root, "merge-base", candidate, "HEAD")
            mb = mb_out.strip()
            return mb if (rc == 0 and mb) else None
        return None
    except Exception:
        return None


def _porcelain_path(line: str) -> str | None:
    """Extract the path from one ``git status --porcelain`` line.

    Format: two status chars + space + path; renames/copies are
    ``XY old -> new`` (the NEW path is the live one). Git C-quotes paths with
    special characters — strip the quotes; embedded escapes are left as-is
    (containment on a slightly-off name still resolves its parent dirs)."""
    if len(line) < 4:
        return None
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    path = path.strip()
    if len(path) >= 2 and path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path or None


def changed_files(root: Path) -> GitDiffResult:
    """Observe the workspace's actual change set. Never raises."""
    try:
        if not (root / ".git").exists():
            return GitDiffResult(is_repo=False)
    except Exception as exc:
        return GitDiffResult(is_repo=False, error=f"{type(exc).__name__}: {exc}")

    try:
        files: set[str] = set()

        # -uall: without it, an entirely-new directory collapses to one
        # "?? dir/" entry and every file inside it is invisible to the
        # witness — found by the #85 end-to-end proof, not by unit fixtures.
        rc, out, err = _run_git(root, "status", "--porcelain", "-uall")
        if rc != 0:
            return GitDiffResult(
                is_repo=True,
                error=f"git status failed (rc={rc}): {err.strip() or out.strip()}",
            )
        for line in out.splitlines():
            path = _porcelain_path(line)
            if path:
                files.add(path)

        # Committed-on-branch half — best-effort (see module docstring).
        base: str | None = None
        for candidate in _DEFAULT_BRANCH_CANDIDATES:
            rc, _, _ = _run_git(root, "rev-parse", "--verify", "--quiet", candidate)
            if rc == 0:
                base = candidate
                break
        if base is not None:
            rc, mb_out, _ = _run_git(root, "merge-base", base, "HEAD")
            merge_base = mb_out.strip()
            if rc == 0 and merge_base:
                rc, diff_out, err = _run_git(root, "diff", "--name-only", merge_base, "HEAD")
                if rc == 0:
                    files.update(p.strip() for p in diff_out.splitlines() if p.strip())
                else:
                    return GitDiffResult(
                        is_repo=True,
                        error=f"git diff failed (rc={rc}): {err.strip()}",
                    )

        return GitDiffResult(is_repo=True, files=tuple(sorted(files)))
    except FileNotFoundError:
        return GitDiffResult(is_repo=True, error="git binary not found on PATH")
    except subprocess.TimeoutExpired:
        return GitDiffResult(is_repo=True, error=f"git timed out after {_GIT_TIMEOUT_SECONDS}s")
    except Exception as exc:  # defensive: the io layer never raises
        return GitDiffResult(is_repo=True, error=f"{type(exc).__name__}: {exc}")

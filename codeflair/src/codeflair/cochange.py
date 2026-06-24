"""Codeflair co-change probe — temporal coupling from git history (CF-D3, inferred).

The only probe that finds relations no reference-walk can reach: files that change
together. Pure parse + count (``ingest_cochange``) over already-fetched git-log text,
plus a wrapper (``index_repo_cochange``) that shells to ``git log``. Couplings are
file-level and ``inferred``; the expansion loop projects them to symbols.
"""
from __future__ import annotations

import subprocess
from itertools import combinations

from codeflair.store import Store

_COMMIT_MARK = "__CF_COMMIT__"

# A commit touching more than this many files (mass reformat, vendor bump, license
# sweep) is noise, not coupling — skip it (it would also blow up to O(n^2) pairs).
_MAX_FILES_PER_COMMIT = 40


def parse_git_log(text: str) -> list[list[str]]:
    """Parse ``git log --name-only --pretty=format:__CF_COMMIT__`` output into a list of
    commits, each a list of changed file paths."""
    commits: list[list[str]] = []
    for chunk in text.split(_COMMIT_MARK):
        files = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if files:
            commits.append(files)
    return commits


def ingest_cochange(
    store: Store,
    commits: list[list[str]],
    *,
    min_support: int = 2,
    path_suffixes: tuple[str, ...] | None = None,
) -> int:
    """Count co-changing file pairs across ``commits`` and store those with support
    >= ``min_support`` as ``co_change`` couplings. ``path_suffixes`` (e.g. ``('.go',)``)
    restricts to files of interest. Returns the number of coupling pairs stored."""
    pair_support: dict[tuple[str, str], int] = {}
    for files in commits:
        if path_suffixes is not None:
            files = [f for f in files if f.endswith(path_suffixes)]
        # drop hidden-dir + worktree-copy paths (.git/.trustless/worktrees/…)
        files = [f for f in files
                 if not any(p.startswith(".") or p == "worktrees" for p in f.split("/"))]
        files = sorted(set(files))
        if len(files) < 2 or len(files) > _MAX_FILES_PER_COMMIT:
            continue
        for a, b in combinations(files, 2):
            pair_support[(a, b)] = pair_support.get((a, b), 0) + 1

    stored = 0
    for (a, b), support in pair_support.items():
        if support >= min_support:
            store.add_coupling(a, b, "co_change", weight=support)
            stored += 1
    store.commit()
    return stored


def index_repo_cochange(
    store: Store,
    repo_path: str,
    *,
    max_commits: int = 2000,
    min_support: int = 2,
    path_suffixes: tuple[str, ...] | None = None,
) -> int:
    """Run ``git log`` in ``repo_path`` (read-only) and ingest co-change couplings."""
    out = subprocess.run(
        ["git", "-C", repo_path, "log", "--no-merges", f"-n{max_commits}",
         "--name-only", f"--pretty=format:{_COMMIT_MARK}"],
        capture_output=True, text=True, check=True,
    )
    commits = parse_git_log(out.stdout)
    return ingest_cochange(store, commits, min_support=min_support, path_suffixes=path_suffixes)

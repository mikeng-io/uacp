"""Codeflair grep probe — cross-language coupling via shared string literals (CF-D13).

SCIP yields ZERO cross-language edges (proven on the spike); the real couplings between
a Go service and a TS client are shared *strings* — HTTP routes, CLI commands, event
names, queue topics. This probe extracts quoted literals and couples files that share a
distinctive one. Language-agnostic (it is text), ``inferred``, file-level.

Pure transform (``ingest_shared_strings``) over ``{path: text}`` + a repo-walking
wrapper (``index_repo_strings``). Reads files read-only.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict

from codeflair.store import Store

# Quoted literals in any language: "double", 'single', `backtick`.
_LITERAL_RE = re.compile(r"""(?:"([^"\n\\]{2,200})"|'([^'\n\\]{2,200})'|`([^`\n\\]{2,200})`)""")

# A literal worth coupling on: long enough, and structured like a route/event/command
# (carries a separator), so we skip prose and trivial tokens.
_MIN_LEN = 6
_STRUCTURE_RE = re.compile(r"[/.:_-]")

# A literal in more files than this is ubiquitous boilerplate (e.g. "application/json"),
# not a distinctive coupling — drop it (and avoid O(n^2) pair blow-up).
_MAX_FILES_PER_TOKEN = 8

_DEFAULT_SUFFIXES = (
    ".go",
    ".ts",
    ".tsx",
    ".js",
    ".py",
    ".rs",
    ".java",
    ".rb",
    ".proto",
    ".yaml",
    ".yml",
)


# Import paths and URLs are shared by hundreds of files (``github.com/...``, ``https://``)
# — structurally noisy, never a distinctive coupling. Drop them.
_NOISE_RE = re.compile(r"(://|github\.com/|golang\.org/|gopkg\.in/|^\.+/|node_modules/)")


def _is_distinctive(tok: str) -> bool:
    return (
        len(tok) >= _MIN_LEN
        and bool(_STRUCTURE_RE.search(tok))
        and not tok.isdigit()
        and not _NOISE_RE.search(tok)
    )


def extract_string_literals(text: str) -> set[str]:
    """Distinctive quoted literals in ``text`` (routes/events/commands), de-duplicated."""
    out: set[str] = set()
    for m in _LITERAL_RE.finditer(text):
        tok = m.group(1) or m.group(2) or m.group(3) or ""
        if _is_distinctive(tok):
            out.add(tok)
    return out


def ingest_shared_strings(
    store: Store,
    files: dict[str, str],
    *,
    max_files_per_token: int = _MAX_FILES_PER_TOKEN,
) -> int:
    """Couple files that share a distinctive literal. Returns coupling pairs stored."""
    token_files: dict[str, set[str]] = defaultdict(set)
    for path, text in files.items():
        for tok in extract_string_literals(text):
            token_files[tok].add(path)

    pair_weight: dict[tuple[str, str], int] = {}
    for paths in token_files.values():
        if not (2 <= len(paths) <= max_files_per_token):
            continue
        ordered = sorted(paths)
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                key = (ordered[i], ordered[j])
                pair_weight[key] = pair_weight.get(key, 0) + 1

    for (a, b), w in pair_weight.items():
        store.add_coupling(a, b, "shared_string", weight=w)
    store.commit()
    return len(pair_weight)


def index_repo_strings(
    store: Store,
    repo_path: str,
    *,
    suffixes: tuple[str, ...] = _DEFAULT_SUFFIXES,
    max_bytes: int = 1_000_000,
) -> int:
    """Walk ``repo_path`` (skipping .git / vendor / node_modules), read source files
    read-only, and ingest shared-string couplings."""
    skip_dirs = {"node_modules", "vendor", "worktrees", "dist", "build"}
    files: dict[str, str] = {}
    for root, dirs, names in os.walk(repo_path):
        # skip hidden dirs (.git/.venv/.trustless/.worktrees/…) + known build/copy dirs
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        for name in names:
            if not name.endswith(suffixes):
                continue
            full = os.path.join(root, name)
            try:
                if os.path.getsize(full) > max_bytes:
                    continue
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    files[os.path.relpath(full, repo_path)] = fh.read()
            except OSError:
                continue
    return ingest_shared_strings(store, files)

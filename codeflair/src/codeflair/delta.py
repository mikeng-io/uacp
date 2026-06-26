"""Codeflair incremental delta re-index (01a-indexer, 10-freshness; roadmap D1 + #9).

Re-indexing a repo per commit must NOT re-do the world (the ~42s full-reindex trap):
tree-sitter is the per-commit **change-detector** deciding *which* files changed, and only
those are re-SCIP'd / re-tree-sitter'd; the watermark advances. Here the detector rides the
P1 freshness substrate — a file is *changed* iff its working-tree content hash differs from
the hash that source recorded — so detection needs no parser and is hermetically testable.

D1 (graph-source floor preserved): re-indexing is **source-scoped** via
``Store.replace_source_file``, so a SCIP delta never disturbs the tree-sitter graph-source
breadth-floor edges (and vice versa). Change-detection is an ADDED role, not a replacement.

Determinism: ``built_at`` (and ``commit_sha``) are INJECTED by the caller — this module
never reads the wall clock. The producer that turns a changed file's bytes into symbols +
edges is INJECTED too (``reindex_file``), so the orchestration is decoupled from any
particular SCIP/tree-sitter toolchain (which the unit suite cannot run).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from codeflair.freshness import content_hash
from codeflair.store import Edge, Store, Symbol


@dataclass(frozen=True)
class FileIndex:
    """One changed file's freshly-produced graph contribution for a single source:
    the symbols it defines and the edges originating from it (all carrying that source)."""

    symbols: list[Symbol]
    edges: list[Edge]


@dataclass(frozen=True)
class ChangeSet:
    """The per-source diff between the working tree and the store's recorded hashes."""

    added: frozenset[str]  # in the tree, no recorded hash for this source
    modified: frozenset[str]  # in the tree, hash differs from the recorded one
    removed: frozenset[str]  # had a recorded hash, gone from the tree
    unchanged: frozenset[str]  # hash matches — no re-index needed

    @property
    def changed(self) -> frozenset[str]:
        """Files needing a re-index = added ∪ modified (removed are dropped, not re-indexed)."""
        return self.added | self.modified


def detect_changed_files(store: Store, current: Mapping[str, bytes], *, source: str) -> ChangeSet:
    """Diff the working tree ``current`` (``{relpath: bytes}``) against what ``source``
    recorded in the freshness substrate. Pure: hash-compare only, no re-index, no write."""
    indexed = store.source_files(source)
    added: set[str] = set()
    modified: set[str] = set()
    unchanged: set[str] = set()
    for path, data in current.items():
        stored = store.source_file_hash(source, path)
        if stored is None:
            added.add(path)
        elif content_hash(data) == stored:
            unchanged.add(path)
        else:
            modified.add(path)
    removed = indexed - set(current)
    return ChangeSet(
        added=frozenset(added),
        modified=frozenset(modified),
        removed=frozenset(removed),
        unchanged=frozenset(unchanged),
    )


def delta_reindex(
    store: Store,
    current: Mapping[str, bytes],
    *,
    source: str,
    reindex_file: Callable[[str, bytes], FileIndex],
    commit_sha: str,
    built_at: str,
    tool_version: str = "",
) -> ChangeSet:
    """Re-index ONLY the files that changed since the last index for ``source``, then advance
    the watermark to ``(commit_sha, built_at)``. Returns the :class:`ChangeSet`.

    For each added/modified file: ``reindex_file`` produces its fresh symbols + edges, the
    symbols are upserted, the file's edges for ``source`` are replaced (source-scoped — the
    floor from other sources is untouched, D1), and its per-source freshness row + content
    hash are refreshed. Removed files are forgotten. Unchanged files are never touched, and
    ``reindex_file`` is never called for them — the negative-cost guarantee (#9).
    """
    changes = detect_changed_files(store, current, source=source)

    for path in sorted(changes.changed):
        produced = reindex_file(path, current[path])
        for sym in produced.symbols:
            store.add_symbol(sym)
        store.replace_source_file(source, path, produced.edges)
        h = content_hash(current[path])
        store.record_file(path, h, commit_sha=commit_sha)
        store.record_freshness(source, path, h, commit_sha=commit_sha, tool_version=tool_version)

    for path in sorted(changes.removed):
        store.forget_file(source, path)

    store.set_watermark(commit_sha, built_at)
    store.commit()
    return changes

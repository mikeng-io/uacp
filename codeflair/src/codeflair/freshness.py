"""Codeflair freshness — per-file content-hash staleness detection (10-freshness).

The store is a committed snapshot; a coding agent works a dirty tree, so the store is
stale w.r.t. the file being edited *most of the time*. The `files` table records each
indexed file's content hash, so a dirty file is just a **hash mismatch** — detectable
with zero re-indexing (the ~42s full-reindex trap is never on the query path).

This module is DETECTION ONLY (P1): it answers "is this working-tree file clean or stale
vs the index?". The 3-zone reconcile (clean/dirty/disagree) and the `live`/`unreconciled`
overlay tags are P2 — they need the LSP overlay and are NOT built here.

Hashing is deterministic (sha256) and carries no wall-clock; the watermark's `built_at`
is injected by the caller (see `Store.set_watermark`).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from codeflair.store import Store

# A file is clean (hash matches the index), stale (hash diverged → store rows are
# stale), or unknown (the index never saw this path, so there is nothing to compare).
FileStatus = Literal["clean", "stale", "unknown"]


def content_hash(data: bytes) -> str:
    """Deterministic per-file content hash (sha256 hex). The identity the `files` /
    `freshness` tables store and the query-time compare computes — same bytes, same hash,
    on every machine and run."""
    return hashlib.sha256(data).hexdigest()


def compare_file(store: Store, path: str, working_bytes: bytes) -> FileStatus:
    """Compare a working-tree file's current content to what the index recorded.

    Returns ``"clean"`` when the working bytes hash to the stored hash, ``"stale"`` when
    they diverge (the file was edited since indexing → its store rows are stale), and
    ``"unknown"`` when the index has no hash for ``path`` (nothing to reconcile against).
    Pure detection — no overlay, no reconcile, no write (those are P2).
    """
    stored = store.file_hash(path)
    if stored is None:
        return "unknown"
    return "clean" if content_hash(working_bytes) == stored else "stale"

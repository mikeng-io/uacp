"""Codeflair LSP overlay + the 3-zone reconcile (P2, 10-freshness / OD-1).

The store is a committed SCIP snapshot; a coding agent works a dirty tree, so the store
is stale w.r.t. the files being edited *most of the time*. The fix is a **live LSP
overlay** consulted at query time over the working tree — and the cardinal rule (OD-1,
mike 2026-06-26):

  **LSP is ALWAYS live, NEVER persisted.** No ``source="lsp"`` row is ever written; ``lsp``
  is a query-time tag, not a stored edge source (it is already out of ``VALID_SOURCES``).
  The overlay is attempted on EVERY reconcile-aware query and is **fail-soft**: if the
  provider (Serena) is absent or fails mid-query, the query STILL SUCCEEDS on
  SCIP/tree-sitter/grep and the result carries an explicit ``lsp_degraded`` warning the
  orchestrator can read — never a silent failure, never a crash.

The reconcile classifies the file each heatmap node lives in, using P1's per-file
content-hash compare (``freshness.compare_file``) SCOPED TO THE NODE'S OWN SOURCE (F1):

  * **trusted** — the file is clean for the node's source (working hash == that source's
    recorded hash) → the store is authoritative; the overlay is NOT consulted for it.
  * **live** — the file is dirty AND the live overlay confirms the node's symbol is PRESENT.
    The overlay supersedes the stale SCIP rows, but it is PRESENCE-ONLY: it certifies the
    symbol still exists, NOT that the edge which put this node in the blast radius is current
    (F3). ``live`` therefore emits a warning that edge-currency is unverified.
  * **unreconciled** — the file is dirty AND SCIP claims the symbol but the live overlay does
    not see it (SCIP says X, LSP says ¬X) → keep BOTH, tag it, surface the conflict. Never
    silently blend.
  * **stale** — the file is dirty but the overlay was unavailable/failed (degraded) → the
    node is flagged, not patched (the documented two-zone degrade of 10-freshness).
  * **unverified** — the file is in the working set but NO source hash exists to certify it
    (F2). "Cannot certify" is the OPPOSITE of clean — it is never collapsed into ``trusted``;
    it carries a warning.

Two more honesty guarantees the reconcile surfaces rather than hides:
  * **overlay_only** (F4) — symbols the live overlay sees in a dirty file that the store does
    NOT know (e.g. a brand-new caller of the seed added by the edit). These are never silently
    dropped: they are surfaced on the result and warned about, so a new dependency is not
    missed.

Deterministic: no LLM, no wall-clock. The overlay is INJECTED; tests drive it with a fake
(live/conflict/clean) and fault-injection (None / raises) — no live Serena required.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Protocol, runtime_checkable

from codeflair.freshness import compare_file, content_hash
from codeflair.query import FreshnessTag, HeatmapEntry
from codeflair.store import Store

# Re-exported for callers that import the tag set from the overlay module (its definition
# lives in query.py so HeatmapEntry can be typed without a circular import — F6).
__all__ = [
    "FreshnessTag",
    "LspOverlay",
    "FileConflict",
    "ReconcileResult",
    "reconcile_overlay",
]


@runtime_checkable
class LspOverlay(Protocol):
    """The injectable live-LSP seam (OD-1). Given a working-tree file and its CURRENT bytes,
    return the symbols the live LSP sees defined/referenced in it — in the store's own symbol
    identity (the SCIP descriptor) so the reconcile can compare like with like.

    PRESENCE-ONLY CONTRACT (F3): the return is a symbol SET, so it certifies which symbols are
    PRESENT in the working file — NOT whether any particular EDGE (the call/ref that put a node
    in the blast radius) is still current. A ``live`` tag therefore means "symbol present;
    edges may be stale", and the reconcile warns accordingly. An edge-aware overlay protocol
    is a later phase; until then the presence-only path is kept HONEST, not over-claimed.

    Consulted ONLY for dirty files (a clean file is store-authoritative). It MAY raise or be
    absent (``None``); the reconcile treats either as a fail-soft degrade, never a crash. The
    real Serena adapter (``serena_overlay.py``) is one thin, import-guarded implementation."""

    def refs_defs(self, file: str, working_bytes: bytes) -> Iterable[str]: ...


@dataclass(frozen=True)
class FileConflict:
    """A dirty file where the committed SCIP snapshot and the live LSP DISAGREE — surfaced,
    not blended. ``scip_symbols`` is what the (stale) store claims lives in the file;
    ``overlay_symbols`` is what the live LSP currently sees. The orchestrator gets BOTH."""

    file: str
    scip_symbols: tuple[str, ...]
    overlay_symbols: tuple[str, ...]


@dataclass(frozen=True)
class ReconcileResult:
    """The reconciled heatmap: the same nodes, each carrying a freshness tag, plus the
    surfaced conflicts, the explicit degrade signal, and the overlay-only new symbols."""

    entries: list[HeatmapEntry]  # same nodes/order, each re-tagged with its freshness zone
    conflicts: list[FileConflict]  # unreconciled (SCIP↔LSP) files, surfaced — never blended
    lsp_degraded: bool  # True iff a dirty file needed the overlay but it was absent/failed
    warnings: list[str]  # agent-readable; carries the lsp_degraded / unverified / live notices
    overlay_only: list[str] = field(default_factory=list)  # F4: live symbols the store lacks


def _file_status(store: Store, file: str, data: bytes, source: str) -> str:
    """Source-scoped staleness for one node's file (F1). With a known persisted ``source``,
    judge the working bytes against THAT source's recorded hash. Without one (a transitive /
    coupling node), be conservative: ``unknown`` if no source has a hash, ``clean`` only if the
    bytes match EVERY recorded source hash, else ``stale`` (any disagreeing source = dirty)."""
    if source:
        return compare_file(store, file, data, source=source)
    rows = store.file_source_hashes(file)
    if not rows:
        return "unknown"
    h = content_hash(data)
    return "clean" if all(v == h for v in rows.values()) else "stale"


def reconcile_overlay(
    store: Store,
    entries: list[HeatmapEntry],
    working_files: dict[str, bytes],
    overlay: LspOverlay | None,
) -> ReconcileResult:
    """Tag each node via the reconcile: ``trusted`` / ``live`` / ``unreconciled`` / ``stale`` /
    ``unverified``.

    ``working_files`` maps a file path to its CURRENT working-tree bytes (the dirty-tree
    snapshot the caller holds — injected, never read off the wall clock here). A node whose
    file is absent from ``working_files`` has no working bytes to compare and stays
    ``trusted`` (the caller asserts nothing about files it did not supply). A node whose file
    IS supplied but carries no recorded hash is ``unverified`` (F2) — never silently trusted.

    Staleness is judged per the node's OWN source (F1). Fail-soft: a dirty file whose overlay
    is ``None`` or raises is flagged ``stale`` and sets ``lsp_degraded``. The reconcile NEVER
    raises out and NEVER writes an ``lsp`` edge.
    """
    overlay_cache: dict[str, frozenset[str] | None] = {}

    def view_for(file: str, data: bytes) -> frozenset[str] | None:
        """The live overlay's symbol set for ``file`` (cached per file). ``None`` means the
        overlay was unavailable or failed — the fail-soft degrade, isolated per file."""
        if file in overlay_cache:
            return overlay_cache[file]
        view: frozenset[str] | None
        if overlay is None:
            view = None
        else:
            try:
                view = frozenset(overlay.refs_defs(file, data))
            except Exception:
                # Fail-soft (OD-1): a provider that crashes mid-query degrades this file to
                # the two-zone path; it must never error the query out.
                view = None
        overlay_cache[file] = view
        return view

    degraded_files: list[str] = []
    unverified_files: list[str] = []
    conflicts: list[FileConflict] = []
    conflict_files: set[str] = set()
    overlay_only_set: set[str] = set()
    any_live = False
    tagged: list[HeatmapEntry] = []

    for e in entries:
        row = store.symbol(e.symbol)
        file = row.file if row is not None else ""
        tag: FreshnessTag = "trusted"
        if file and file in working_files:
            status = _file_status(store, file, working_files[file], e.source)
            if status == "unknown":
                # in the working set but nothing to certify against → cannot say "clean" (F2)
                tag = "unverified"
                if file not in unverified_files:
                    unverified_files.append(file)
            elif status == "stale":
                view = view_for(file, working_files[file])
                if view is None:
                    tag = "stale"  # dirty + no live overlay → flagged, not patched
                    if file not in degraded_files:
                        degraded_files.append(file)
                else:
                    # F4: any overlay symbol the store does not know is a new dependency —
                    # surface it (never silently drop), on BOTH the live and conflict paths.
                    overlay_only_set.update(s for s in view if store.symbol(s) is None)
                    if e.symbol in view:
                        tag = "live"  # presence-confirmed; edge-currency unverified (F3)
                        any_live = True
                    else:
                        tag = "unreconciled"  # SCIP says X, live LSP says ¬X → keep both
                        if file not in conflict_files:
                            conflict_files.add(file)
                            conflicts.append(
                                FileConflict(
                                    file=file,
                                    scip_symbols=tuple(store.symbols_in_file(file)),
                                    overlay_symbols=tuple(sorted(view)),
                                )
                            )
            # status == "clean" → store authoritative for this source → stays "trusted"
        tagged.append(replace(e, freshness=tag))

    warnings: list[str] = []
    lsp_degraded = bool(degraded_files)
    if lsp_degraded:
        warnings.append(
            "lsp_degraded: live LSP overlay unavailable for "
            f"{len(degraded_files)} dirty file(s) ({', '.join(sorted(degraded_files))}); "
            "returned SCIP/tree-sitter result, dirty nodes flagged 'stale' (two-zone reconcile)"
        )
    if unverified_files:
        warnings.append(
            f"unverified: {len(unverified_files)} file(s) in the working set "
            f"({', '.join(sorted(unverified_files))}) have no recorded hash to certify "
            "freshness against — tagged 'unverified', NOT trusted"
        )
    if conflicts:
        conflicts.sort(key=lambda c: c.file)
        warnings.append(
            f"unreconciled: {len(conflicts)} file(s) where the committed SCIP snapshot and "
            "the live LSP disagree; both views surfaced, not blended"
        )
    if any_live:
        warnings.append(
            "live: node(s) confirmed PRESENT by the live overlay, but edge-currency is "
            "unverified (presence-only overlay) — their edges may be stale until the overlay "
            "seam is edge-aware"
        )
    overlay_only = sorted(overlay_only_set)
    if overlay_only:
        warnings.append(
            f"overlay_only: the live overlay sees {len(overlay_only)} symbol(s) in dirty "
            "file(s) that the store does not know (possible new dependency) — surfaced, "
            "not dropped"
        )
    return ReconcileResult(
        entries=tagged,
        conflicts=conflicts,
        lsp_degraded=lsp_degraded,
        warnings=warnings,
        overlay_only=overlay_only,
    )

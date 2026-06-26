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
content-hash compare (``freshness.compare_file``):

  * **trusted** — the file is clean (working hash == indexed hash) → the store is
    authoritative; the overlay is NOT consulted for it.
  * **live** — the file is dirty AND the live overlay confirms the node's symbol → the
    overlay's view SUPERSEDES the stale SCIP rows for that file.
  * **unreconciled** — the file is dirty AND SCIP claims the symbol but the live overlay
    does not see it (SCIP says X, LSP says ¬X) → keep BOTH, tag it, surface the conflict.
    Never silently blend.
  * **stale** — the file is dirty but the overlay was unavailable/failed (degraded) → the
    node is flagged, not patched (the documented two-zone degrade of 10-freshness).

Deterministic: no LLM, no wall-clock. The overlay is INJECTED; tests drive it with a fake
(live/conflict/clean) and fault-injection (None / raises) — no live Serena required.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Literal, Protocol, runtime_checkable

from codeflair.freshness import compare_file
from codeflair.query import HeatmapEntry
from codeflair.store import Store

# The four query-time freshness zones a reconciled node can carry.
FreshnessTag = Literal["trusted", "live", "unreconciled", "stale"]


@runtime_checkable
class LspOverlay(Protocol):
    """The injectable live-LSP seam (OD-1). Given a working-tree file and its CURRENT bytes,
    return the symbols the live LSP sees defined/referenced in it — in the store's own symbol
    identity (the SCIP descriptor) so the reconcile can compare like with like.

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
    surfaced conflicts and the explicit degrade signal."""

    entries: list[HeatmapEntry]  # same nodes/order, each re-tagged with its freshness zone
    conflicts: list[FileConflict]  # unreconciled (SCIP↔LSP) files, surfaced — never blended
    lsp_degraded: bool  # True iff a dirty file needed the overlay but it was absent/failed
    warnings: list[str]  # agent-readable; carries the lsp_degraded + unreconciled notices


def reconcile_overlay(
    store: Store,
    entries: list[HeatmapEntry],
    working_files: dict[str, bytes],
    overlay: LspOverlay | None,
) -> ReconcileResult:
    """Tag each node ``trusted``/``live``/``unreconciled``/``stale`` via the 3-zone reconcile.

    ``working_files`` maps a file path to its CURRENT working-tree bytes (the dirty-tree
    snapshot the caller holds — injected, never read off the wall clock here). A node whose
    file is absent from ``working_files`` (or unknown to the index) has no staleness evidence
    and stays ``trusted``.

    Fail-soft: a dirty file whose overlay is ``None`` or raises is flagged ``stale`` and sets
    ``lsp_degraded`` — the reconcile NEVER raises out and NEVER writes an ``lsp`` edge.
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
    conflicts: list[FileConflict] = []
    conflict_files: set[str] = set()
    tagged: list[HeatmapEntry] = []

    for e in entries:
        row = store.symbol(e.symbol)
        file = row.file if row is not None else ""
        tag: FreshnessTag = "trusted"
        if file and file in working_files:
            status = compare_file(store, file, working_files[file])
            if status == "stale":
                view = view_for(file, working_files[file])
                if view is None:
                    tag = "stale"  # dirty + no live overlay → flagged, not patched
                    if file not in degraded_files:
                        degraded_files.append(file)
                elif e.symbol in view:
                    tag = "live"  # live overlay supersedes the stale SCIP row for this file
                else:
                    tag = "unreconciled"  # SCIP says X, live LSP says ¬X → keep both, surface
                    if file not in conflict_files:
                        conflict_files.add(file)
                        conflicts.append(
                            FileConflict(
                                file=file,
                                scip_symbols=tuple(store.symbols_in_file(file)),
                                overlay_symbols=tuple(sorted(view)),
                            )
                        )
            # status in ("clean", "unknown") → no staleness evidence → stays "trusted"
        tagged.append(replace(e, freshness=tag))

    warnings: list[str] = []
    lsp_degraded = bool(degraded_files)
    if lsp_degraded:
        warnings.append(
            "lsp_degraded: live LSP overlay unavailable for "
            f"{len(degraded_files)} dirty file(s) ({', '.join(sorted(degraded_files))}); "
            "returned SCIP/tree-sitter result, dirty nodes flagged 'stale' (two-zone reconcile)"
        )
    if conflicts:
        conflicts.sort(key=lambda c: c.file)
        warnings.append(
            f"unreconciled: {len(conflicts)} file(s) where the committed SCIP snapshot and "
            "the live LSP disagree; both views surfaced, not blended"
        )
    return ReconcileResult(
        entries=tagged, conflicts=conflicts, lsp_degraded=lsp_degraded, warnings=warnings
    )

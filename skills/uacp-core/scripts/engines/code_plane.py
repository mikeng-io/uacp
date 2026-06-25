"""UACP -> Codeflair code-plane resolver (capsule #3 slice 3 / design node 32).

The thin adapter that lets a ``uacp.check.symbol_resolves`` bind to the REAL SCIP symbol index
(Codeflair) instead of a textual shadow — the #503 ``grep route_mounted`` weak-proxy fix. UACP
**consumes** the per-commit index; it does not own it (CF-D9: Codeflair has zero UACP dependency,
so this module is the *only* uacp->codeflair seam, and it imports codeflair LAZILY + fail-closed so
a deployment without codeflair degrades to ERROR rather than crashing).

Resolution happens at REPLAY (like ``artifact_integrity`` reads the watermark) — it does NOT project
``code_symbol`` nodes / ``code_anchor`` edges into the manifest graph (the prior shim-B revert seam:
code anchoring is a checkpoint->code_symbol/PARSED concern, never a work_unit/asserted graph edge).

FAIL-CLOSED (never a silent pass): NO index for the run, codeflair not importable, or a query error
is an ERROR (block); a symbol that resolves to no descriptor in a PRESENT index is a FAIL.

Index PRODUCTION (building + locating the SCIP db per run/commit) is a separate operational concern
(a documented follow-on); this resolver consumes an index present at the conventioned path.
"""

from __future__ import annotations

from pathlib import Path

from config import base_dir


def index_path(workspace: str | Path) -> Path:
    """The conventioned per-run Codeflair index location: ``<governed base>/code-index.db``.
    A rebuildable, watermark-like projection (kin to ``state/hashes/``); truth is the code."""
    return base_dir(Path(str(workspace))) / "code-index.db"


def resolve_symbol(workspace: str | Path, code_ref: str) -> tuple[str, str]:
    """Return ``(PASS|FAIL|ERROR, detail)`` for a ``symbol_resolves`` bind.

    PASS iff ``code_ref`` resolves to >=1 SCIP descriptor in the run's Codeflair index; FAIL if it
    resolves to none; ERROR (fail-closed, block) if there is no index, codeflair is unavailable, or
    the query fails. Never raises."""
    if not code_ref:
        return ("ERROR", "symbol_resolves: bind.ref.symbol missing")
    try:
        path = index_path(workspace)
    except Exception as exc:  # base_dir containment failure, etc.
        return ("ERROR", f"code index path unresolvable: {type(exc).__name__}: {exc}")
    # Check existence BEFORE opening — Store(path) would CREATE an empty db, masking "not built"
    # (an empty index would FAIL rather than ERROR). Absent index == cannot verify == ERROR.
    if not path.exists():
        return ("ERROR", f"no code index for this run ({path.name}); code plane not built")
    try:
        from codeflair.crossplane import CrossPlaneAdapter
        from codeflair.store import Store
    except ImportError as exc:
        return ("ERROR", f"codeflair (code plane) not available: {exc}")
    try:
        store = Store(str(path))
        try:
            resolved = CrossPlaneAdapter(store).resolve(str(code_ref))
        finally:
            store.con.close()
    except Exception as exc:  # any query/IO failure is fail-closed, never a pass
        return ("ERROR", f"code index query failed: {type(exc).__name__}: {exc}")
    if resolved:
        return ("PASS", "")
    return ("FAIL", f"symbol {code_ref!r} resolves to no SCIP descriptor in the index")

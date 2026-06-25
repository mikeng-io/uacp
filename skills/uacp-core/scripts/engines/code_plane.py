"""UACP -> Codeflair code-plane resolver (capsule #3 slice 3 / design node 32).

The thin adapter that lets a ``uacp.check.symbol_resolves`` bind to the REAL SCIP symbol index
(Codeflair) instead of a textual shadow — the #503 ``grep route_mounted`` weak-proxy fix. UACP
**consumes** the per-commit index; it does not own it (CF-D9). It opens the index sqlite READ-ONLY
and queries Codeflair's stable ``symbols`` schema directly — it does NOT instantiate
``CrossPlaneAdapter`` (whose ``__init__`` CREATEs a ``code_anchor`` table, mutating the index UACP
may only consume — council finding) and does NOT use that adapter's fuzzy ``resolve()``.

Resolution happens at REPLAY (like ``artifact_integrity`` reads the watermark) — it does NOT project
``code_symbol`` nodes / ``code_anchor`` edges into the manifest graph (the prior shim-B revert seam:
code anchoring is a checkpoint->code_symbol/PARSED concern, never a work_unit/asserted graph edge).

EXACT identity, never substring/LIKE: a bind matches iff ``bind.ref.symbol`` equals the SCIP
descriptor OR the exact indexed name. Fuzzy substring matching is a weak proxy (``route`` ~
``reroute``; ``%`` ~ everything) — the wrong semantics for a fail-closed gate (council finding).

FAIL-CLOSED (never a silent pass): NO index for the run, a missing/corrupt index, or a query error
is an ERROR (block); a symbol that matches nothing in a PRESENT index is a FAIL.

Index PRODUCTION (building + locating the SCIP db per run/commit) is a separate operational concern
(a documented follow-on); this resolver consumes an index present at the conventioned path.
"""

from __future__ import annotations

import sqlite3
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
    # Check existence FIRST: a connect would otherwise CREATE an empty db, masking "not built" (an
    # empty index would FAIL not ERROR). Absent index == cannot verify == ERROR (fail-closed).
    if not path.exists():
        return ("ERROR", f"no code index for this run ({path.name}); code plane not built")
    # CONSUME the index READ-ONLY (mode=ro): never mutate the index UACP does not own (CF-D9 — the
    # council caught CrossPlaneAdapter.__init__ creating its `code_anchor` table). Query Codeflair's
    # stable `symbols` schema (Symbol: symbol[=SCIP descriptor], name, file) by EXACT identity —
    # never a substring/LIKE (the council caught `route` passing against `reroute`, `%` against
    # everything — the #503 weak proxy at the SCIP layer). A bind matches a real symbol iff
    # `bind.ref.symbol` equals the SCIP descriptor OR the exact indexed name (approximate => FAIL).
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT symbol FROM symbols WHERE file != '' AND (symbol = ? OR name = ?)",
                (code_ref, code_ref),
            ).fetchall()
        finally:
            con.close()
    except Exception as exc:  # corrupt db / missing `symbols` table / IO — fail-closed, never pass
        return ("ERROR", f"code index query failed: {type(exc).__name__}: {exc}")
    if rows:
        return ("PASS", "")
    return ("FAIL", f"symbol {code_ref!r} matches no SCIP descriptor/name in the index")

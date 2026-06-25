"""UACP -> Codeflair code-INDEX builder (capsule #3 follow-on / design node 32 production).

UACP **consumes** the SCIP symbol index (CF-D9); *producing* it is Codeflair's job. This is a thin,
fail-closed convenience wrapper that runs Codeflair's tree-sitter ingest over ``repo_root`` into the
conventioned per-run index path (:func:`engines.code_plane.index_path`), so a ``symbol_resolves``
check has a real index to bind to.

The tree-sitter ingester is an OPTIONAL Codeflair dependency (``codeflair[treesitter]``); when it
(or the codeflair package) is unavailable, building is a **no-op with status** — never a crash, and
never a partial index (the ingester is imported BEFORE the store opens, so an unavailable dep leaves
no db behind). With no index the code plane then ERRORs at replay — fail-closed, never a false pass.

Real production wires this — or Codeflair's own ``bootstrap`` + ``scip_ingest.index_repo`` for
SCIP-precision symbols — as a CI / pre-verify step. This wrapper is the in-process syntactic floor.
"""

from __future__ import annotations

from pathlib import Path

from engines.code_plane import index_path


def build_code_index(workspace: str | Path, repo_root: str | Path) -> dict:
    """Build the run's Codeflair index at ``index_path(workspace)`` by tree-sitter-ingesting
    ``repo_root``. Returns ``{"ok": True, "index": <path>, "files"/"symbols"/"edges": int}`` on
    success, or ``{"ok": False, "reason": ..., "index": <path>}`` when the ingester is unavailable
    or the build fails. Never raises. The index lands where ``engines.code_plane`` reads it."""
    out = index_path(Path(str(workspace)))
    try:
        from codeflair.store import Store
        from codeflair.treesitter_ingest import index_repo_tree_sitter
    except ImportError as exc:  # optional dep / package absent -> no-op, fail-closed (no db made)
        return {"ok": False, "reason": f"codeflair tree-sitter ingester unavailable: {exc}",
                "index": str(out)}
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        store = Store(str(out))
        try:
            stats = index_repo_tree_sitter(store, str(repo_root))
            store.con.commit()
        finally:
            store.con.close()
    except Exception as exc:  # build failure is fail-closed (the resolver ERRORs on a bad index)
        return {"ok": False, "reason": f"index build failed: {type(exc).__name__}: {exc}",
                "index": str(out)}
    return {"ok": True, "index": str(out), "files": stats.files, "symbols": stats.symbols,
            "edges": stats.edges}

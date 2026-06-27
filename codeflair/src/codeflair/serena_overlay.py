"""Codeflair → Serena: the REAL live-LSP overlay adapter (P2, 12-delivery / OD-1).

This is the thin, import-guarded implementation of the :class:`~codeflair.overlay.LspOverlay`
seam. Serena (a Python LSP layer over 40+ languages, 12-delivery.md) is reached as a Python
library — but it is an OPTIONAL dependency: codeflair NEVER hard-depends on it (CF-D9), exactly
like the tree-sitter floor. The import is lazy; if Serena (or its ``uv``/``uvx`` runtime) is
absent, provisioning returns ``None`` and the query degrades fail-soft to the two-zone reconcile
with an ``lsp_degraded`` warning — never a crash, never a hard import error at module load.

OD-1: this overlay is consulted LIVE per query and its results are NEVER persisted — the
reconcile (``overlay.reconcile_overlay``) tags nodes, it does not write ``source="lsp"`` rows.
"""

from __future__ import annotations

from collections.abc import Iterable


class SerenaOverlay:
    """Live-LSP overlay backed by Serena. Holds an opaque Serena client (injected by
    :func:`load_serena_overlay`, which owns the guarded import) and answers ``refs_defs``
    by asking Serena for the symbols it currently sees in a working-tree file.

    GATED / DEFERRED — the one piece that needs a live Serena to finish: mapping Serena's
    LSP symbol identities to codeflair's SCIP descriptor identity so the reconcile compares
    like with like. Until that mapping is built+verified against a live Serena, ``refs_defs``
    raises ``NotImplementedError``; the reconcile catches it and degrades fail-soft, so the
    engine is correct (degraded) rather than silently wrong. Structure first, mapping next.
    """

    def __init__(self, client: object) -> None:
        self._client = client

    def refs_defs(self, file: str, working_bytes: bytes) -> Iterable[str]:
        # DEFERRED: query ``self._client`` for the file's live symbols, then map each
        # Serena/LSP symbol to its SCIP descriptor (the store's identity). Needs a live
        # Serena to ground the mapping — see the class docstring. Until then, fail-soft.
        raise NotImplementedError(
            "SerenaOverlay.refs_defs: Serena→SCIP-descriptor symbol mapping is the gated "
            "follow-on; reached only with a live Serena (absent in this environment)."
        )


def load_serena_overlay() -> SerenaOverlay | None:
    """Provision the live Serena overlay, or ``None`` if Serena is unavailable.

    The import is LAZY and guarded (CF-D9: no hard dependency). When ``serena`` is not
    importable — the case in the default dev venv, and whenever the user has not set up
    ``uv``/``uvx`` (their responsibility, 12-delivery.md) — this returns ``None`` so the
    orchestrator passes ``overlay=None`` and the reconcile takes the documented two-zone
    degrade with an ``lsp_degraded`` warning. It never raises ``ImportError`` at callers.
    """
    try:
        import serena  # noqa: PLC0415  (guarded optional dep — must be imported lazily here)
    except ImportError:
        return None
    # A live Serena is present: hand its client to the overlay. (Constructing the actual
    # Serena LSP client + the descriptor mapping is the gated follow-on — see SerenaOverlay.)
    return SerenaOverlay(client=serena)

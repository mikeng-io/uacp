"""Codeflair cross-plane adapter — the ``code_anchor`` join (the UACP novelty, CF-D9/D14).

Links code symbols (SCIP descriptors — the stable, location-independent identity) to
GOVERNANCE manifest entities, answering the two cross-plane questions UACP needs:
  - **governs(symbol)** — which manifest intent governs this code?
  - **realizes(manifest)** — which code realizes this proposal/plan?
and surfacing the cross-plane GAPS that are the actionable output:
  - **orphan code** — a repo symbol no manifest anchors (code nobody declared intent for);
  - **unrealized manifest** — a manifest with no code anchor (intent with no code).

This module is deliberately UACP-AGNOSTIC: per CF-D9 the core/adapter logic must NOT import
UACP. It operates on injected :class:`ManifestRef`s; the real binding (reading UACP's
manifest graph + the governed-writer/Guardian wrapper) is a thin shim ABOVE this, in UACP.
Resolution maps a manifest's *human* code reference (a name, or ``file:name``) to the
stable SCIP descriptor via the store — fuzzy reference in, stable anchor out.
"""

from __future__ import annotations

from dataclasses import dataclass

from codeflair.store import Store

_VALID_REL = frozenset({"realizes", "derives_from", "governs"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS code_anchor(
    manifest_id   TEXT NOT NULL,
    manifest_kind TEXT NOT NULL,        -- proposal | plan | execution | resolution | ...
    symbol        TEXT NOT NULL,        -- the resolved SCIP descriptor (symbols.symbol)
    rel           TEXT NOT NULL,        -- realizes | derives_from | governs
    PRIMARY KEY (manifest_id, symbol, rel)
);
CREATE INDEX IF NOT EXISTS i_anchor_sym ON code_anchor(symbol);
CREATE INDEX IF NOT EXISTS i_anchor_mid ON code_anchor(manifest_id);
"""


@dataclass(frozen=True)
class ManifestRef:
    """A governance manifest's reference TO code, before resolution. ``code_ref`` is a
    human reference: a bare symbol name (``CancelOrderUseCase``) or ``file:name``
    (``cancel_order.go:Execute``)."""

    manifest_id: str
    kind: str
    code_ref: str
    rel: str = "realizes"


@dataclass(frozen=True)
class AnchorResult:
    ref: ManifestRef
    resolved: list[str]  # SCIP descriptors the code_ref resolved to
    status: str  # "anchored" (exactly 1) | "ambiguous" (>1) | "unresolved" (0)


class CrossPlaneAdapter:
    """Owns the ``code_anchor`` table inside Codeflair's SQLite (the adapter creates it; the
    core never references it — dependency arrow adapter -> core). Resolves manifest code
    references against the store and answers the cross-plane joins and gaps."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self.store.con.executescript(_SCHEMA)
        self.store.con.commit()

    # -- resolution ----------------------------------------------------------
    def resolve(self, code_ref: str) -> list[str]:
        """Resolve a human code reference to stable SCIP descriptor(s) defined in the repo.
        Matches by symbol name (exact first, then substring), optionally scoped by file."""
        if ":" in code_ref:
            file_part, name = code_ref.rsplit(":", 1)
        else:
            file_part, name = "", code_ref
        params: list[object] = [name]
        sql = "SELECT symbol FROM symbols WHERE file != '' AND name = ?"
        if file_part:
            sql += " AND file LIKE ?"
            params.append(f"%{file_part}%")
        rows = self.store.con.execute(sql + " ORDER BY symbol", params).fetchall()
        if rows:
            return [r[0] for r in rows]
        # fall back to substring on the name (scip display names carry suffixes like "().")
        params = [f"%{name}%"]
        sql = "SELECT symbol FROM symbols WHERE file != '' AND name LIKE ?"
        if file_part:
            sql += " AND file LIKE ?"
            params.append(f"%{file_part}%")
        return [r[0] for r in self.store.con.execute(sql + " ORDER BY symbol", params).fetchall()]

    # -- writes (anchor) -----------------------------------------------------
    def anchor(self, ref: ManifestRef) -> AnchorResult:
        """Resolve ``ref`` and write a ``code_anchor`` row per resolved symbol. Ambiguous
        (>1) anchors are still recorded but flagged for governance review."""
        if ref.rel not in _VALID_REL:
            raise ValueError(f"unknown rel {ref.rel!r}; expected one of {sorted(_VALID_REL)}")
        resolved = self.resolve(ref.code_ref)
        for sym in resolved:
            self.store.con.execute(
                "INSERT OR IGNORE INTO code_anchor(manifest_id,manifest_kind,symbol,rel) "
                "VALUES (?,?,?,?)",
                (ref.manifest_id, ref.kind, sym, ref.rel),
            )
        self.store.con.commit()
        status = (
            "unresolved" if not resolved else ("anchored" if len(resolved) == 1 else "ambiguous")
        )
        return AnchorResult(ref=ref, resolved=resolved, status=status)

    def ingest(self, refs: list[ManifestRef]) -> list[AnchorResult]:
        return [self.anchor(r) for r in refs]

    # -- cross-plane joins ---------------------------------------------------
    def governs(self, symbol: str) -> list[tuple[str, str, str]]:
        """Manifest entities anchored to ``symbol`` as ``(manifest_id, kind, rel)``."""
        return [
            (r[0], r[1], r[2])
            for r in self.store.con.execute(
                "SELECT manifest_id, manifest_kind, rel FROM code_anchor WHERE symbol=? "
                "ORDER BY manifest_id",
                (symbol,),
            ).fetchall()
        ]

    def realizes(self, manifest_id: str) -> list[str]:
        """Code symbols anchored to ``manifest_id``."""
        return [
            r[0]
            for r in self.store.con.execute(
                "SELECT symbol FROM code_anchor WHERE manifest_id=? ORDER BY symbol",
                (manifest_id,),
            ).fetchall()
        ]

    # -- cross-plane gaps ----------------------------------------------------
    def orphan_code(self, *, kind: str | None = None) -> list[str]:
        """Repo symbols that NO manifest anchors — code without declared governance intent.
        ``kind`` optionally restricts to a symbol kind (e.g. a function/method)."""
        sql = (
            "SELECT s.symbol FROM symbols s "
            "WHERE s.file != '' AND s.symbol NOT IN (SELECT symbol FROM code_anchor)"
        )
        params: list[object] = []
        if kind is not None:
            sql += " AND s.kind = ?"
            params.append(kind)
        return [r[0] for r in self.store.con.execute(sql + " ORDER BY s.symbol", params).fetchall()]

    def unrealized_manifests(self, manifest_ids: list[str]) -> list[str]:
        """Of ``manifest_ids``, those with no code anchor — intent with no realizing code."""
        anchored = {
            r[0]
            for r in self.store.con.execute(
                "SELECT DISTINCT manifest_id FROM code_anchor"
            ).fetchall()
        }
        return [m for m in manifest_ids if m not in anchored]

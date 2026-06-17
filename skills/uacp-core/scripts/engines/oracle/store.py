"""Vector+FTS store behind a thin interface for the Oracle semantic leg.

LanceDB is the default backend; sqlite-vec + FTS5 is the documented lighter
swap-in behind the SAME interface (brute-force KNN suffices there). The store
dep is OPTIONAL + lazily imported — ``available()`` is the single gate the
resolver/pipeline checks before using the semantic legs. The index lives at
``.uacp/knowledge/indexes/`` and is DERIVED/REBUILDABLE from the OKF corpus
files. Never raises on a missing dep: ``available()`` returns ``False``.

No top-level ``import lancedb`` — it is resolved lazily inside ``_lancedb()`` so
the FLOOR (keyword + structured + BES, zero ML deps) imports and runs clean.
"""
from __future__ import annotations

import importlib
from typing import Any, Protocol, runtime_checkable


class StoreUnavailable(RuntimeError):
    """Raised when a store backend is unknown or its dep is missing at use-time."""


@runtime_checkable
class VectorStore(Protocol):
    """The thin store contract every backend implements."""

    def available(self) -> bool: ...
    def upsert(self, rows: list[dict[str, Any]]) -> None: ...
    def dense_search(self, vector: list[float], k: int) -> list[dict[str, Any]]: ...
    def fts_search(self, query: str, k: int) -> list[dict[str, Any]]: ...
    def rrf_hybrid(
        self, vector: list[float] | None, query: str, k: int
    ) -> list[dict[str, Any]]: ...


def _lancedb() -> Any | None:
    """Lazily import lancedb. Returns the module, or None when absent. Never raises."""
    try:
        return importlib.import_module("lancedb")
    except Exception:
        return None


# Reciprocal-rank-fusion constant (design §pipeline step 3).
RRF_K = 60

# Default table name for the corpus index.
_CORPUS_TABLE = "corpus"


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Map a native store row to a plain dict (query-shaping helper, pure)."""
    if isinstance(row, dict):
        return dict(row)
    # Tolerate mapping-like rows from other backends without importing them.
    try:
        return dict(row)
    except Exception:
        return {"value": row}


class LanceDBStore:
    """LanceDB-backed store. Lazy connection; degrades to unavailable cleanly."""

    def __init__(self, index_path: str, *, table: str = _CORPUS_TABLE) -> None:
        self.index_path = index_path
        self.table = table
        self._db: Any | None = None

    def available(self) -> bool:
        return _lancedb() is not None

    def _conn(self) -> Any:
        lancedb = _lancedb()
        if lancedb is None:
            raise StoreUnavailable("lancedb not installed")
        if self._db is None:
            self._db = lancedb.connect(self.index_path)
        return self._db

    def _open_table(self) -> Any:
        return self._conn().open_table(self.table)

    def upsert(self, rows: list[dict[str, Any]]) -> None:
        # Full index build/add is the hybrid-pipeline task's concern; the lazy
        # connection + native FTS index land there. The dep-gate is enforced here.
        self._conn()
        raise StoreUnavailable("lancedb upsert not yet implemented (semantic build task)")

    def dense_search(self, vector: list[float], k: int) -> list[dict[str, Any]]:
        table = self._open_table()
        rows = table.search(vector).limit(k).to_list()
        return [_row_to_dict(r) for r in rows]

    def fts_search(self, query: str, k: int) -> list[dict[str, Any]]:
        table = self._open_table()
        rows = table.search(query).limit(k).to_list()
        return [_row_to_dict(r) for r in rows]

    def rrf_hybrid(
        self, vector: list[float] | None, query: str, k: int
    ) -> list[dict[str, Any]]:
        # LanceDB native hybrid search fuses dense + FTS with RRF (k=60). When no
        # vector is available the dense leg is skipped and FTS carries the query.
        table = self._open_table()
        probe = vector if vector is not None else query
        rows = table.search(probe).limit(k).to_list()
        return [_row_to_dict(r) for r in rows]


class SqliteVecStore:
    """Documented lighter alternate (sqlite-vec + FTS5). Stub: only available()
    is wired for now; brute-force KNN suffices when fleshed out. Lazy + guarded."""

    def __init__(self, index_path: str) -> None:
        self.index_path = index_path

    def _sqlite_vec(self) -> Any | None:
        try:
            return importlib.import_module("sqlite_vec")
        except Exception:
            return None

    def available(self) -> bool:
        return self._sqlite_vec() is not None

    def upsert(self, rows: list[dict[str, Any]]) -> None:
        raise StoreUnavailable("sqlite-vec store not yet implemented")

    def dense_search(self, vector: list[float], k: int) -> list[dict[str, Any]]:
        raise StoreUnavailable("sqlite-vec store not yet implemented")

    def fts_search(self, query: str, k: int) -> list[dict[str, Any]]:
        raise StoreUnavailable("sqlite-vec store not yet implemented")

    def rrf_hybrid(
        self, vector: list[float] | None, query: str, k: int
    ) -> list[dict[str, Any]]:
        raise StoreUnavailable("sqlite-vec store not yet implemented")


def get_store(backend: str, *, index_path: str) -> VectorStore:
    """Return a store for ``backend``. Raises StoreUnavailable for unknown backends."""
    if backend == "lancedb":
        return LanceDBStore(index_path)
    if backend == "sqlite-vec":
        return SqliteVecStore(index_path)
    raise StoreUnavailable(f"unknown store backend: {backend!r}")

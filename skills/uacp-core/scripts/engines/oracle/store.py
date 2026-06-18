"""Vector+FTS store behind a thin interface for the Oracle semantic leg.

LanceDB is the default backend; sqlite-vec + FTS5 is the documented lighter
swap-in behind the SAME interface (brute-force KNN suffices there).
``alibaba/zvec`` (an embedded C++ vector DB, Apache-2.0, with dense + FTS +
hybrid search built in) is another candidate to evaluate behind this same
``VectorStore`` protocol once it matures. The store dep is OPTIONAL + lazily
imported — ``available()`` is the single gate the resolver/pipeline checks
before using the semantic legs. The index lives at ``.uacp/knowledge/indexes/``
and is DERIVED/REBUILDABLE from the OKF corpus files. Never raises on a missing
dep: ``available()`` returns ``False``.

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

    def _table_names(self) -> Any:
        return self._conn().table_names()

    def upsert(self, rows: list[dict[str, Any]]) -> None:
        """Populate (or refresh) the corpus table from ``rows`` and ensure FTS.

        Behaviour:
          * Empty ``rows`` is a no-op (nothing to build).
          * If the table does NOT exist, it is created from ``rows`` — LanceDB
            infers the Arrow schema (incl. the ``vector`` fixed-size-list dim)
            from the data, exactly like the e2e harness's ``create_table``.
          * If the table EXISTS, rows are upserted by ``id`` via
            ``merge_insert("id")`` (update-matched + insert-not-matched), i.e.
            true upsert-by-id semantics: re-indexing the same corpus replaces
            each item in place rather than appending duplicates.
          * After populating, the native FTS index on the ``text`` column is
            (re)built so ``fts_search`` works. Index creation is wrapped to be
            idempotent across LanceDB versions (older builds raise if an index
            already exists; we fall back to ``replace=True`` then swallow).

        Dep-gated: ``_conn()`` raises ``StoreUnavailable`` when lancedb is absent.
        """
        if not rows:
            return
        db = self._conn()

        if self.table in self._table_names():
            table = db.open_table(self.table)
            # True upsert-by-id: update rows whose id matches, insert the rest.
            (
                table.merge_insert("id")
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute(rows)
            )
        else:
            # Infer schema (incl. vector dim) from the first row's data.
            table = db.create_table(self.table, data=rows)

        self._ensure_fts_index(table)

    @staticmethod
    def _ensure_fts_index(table: Any) -> None:
        """Build the native FTS index on ``text`` idempotently across versions."""
        try:
            table.create_fts_index("text", replace=True)
            return
        except TypeError:
            # Older LanceDB: no ``replace`` kwarg.
            pass
        except Exception:
            # Some versions raise when the index already exists; that's fine.
            return
        try:
            table.create_fts_index("text")
        except Exception:
            # Index already present (or unsupported) — leave the existing one.
            pass

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
        # NOTE: this method does NOT implement real RRF fusion. It issues a single
        # table.search() call — either vector search (when vector is provided) or
        # FTS (when vector is None). True RRF fusion across both legs is performed
        # by pipeline.rrf_fuse(), which the live pipeline (pipeline.semantic_retrieve)
        # uses instead of this method. Real index build is also deferred: upsert()
        # raises StoreUnavailable. This stub exists only to satisfy the VectorStore
        # protocol while the full hybrid-index build task is pending.
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

"""Codeflair store — ONE fused SQLite graph, edges tagged by source.

Schema follows design/codeflair/01b-store.md, with one decision the C-spike earned:
the symbol primary key is the **SCIP descriptor string** (e.g.
``scip-go gomod github.com/jackc/pgx/v5 v5.10.0 `…/pgxpool`/Pool#Conn().``), which is
location-independent, version-pinned and move-stable — NOT an autoincrement row id.
A row id churns on reindex (codebase-memory's failure mode, measured 2026-06-25);
the descriptor is the stable anchor `code_anchor` binds to.

Fused for query (the recursive-CTE blast walk must cross scip+tree_sitter+co_change
edges together), partitioned for ingest/freshness: each `source` ingests on its own
clock via source-scoped delete-and-replace.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

# EDGE sources — the only provenances that emit a PERSISTED ``edges`` row. Two real
# edge producers: scip (parsed symbol edges) and tree_sitter (the syntactic breadth
# floor, CF-D14). This is the EDGE axis; it is distinct from two other axes (see
# 11-substrate.md):
#   - COUPLING axis (VALID_COUPLING): grep -> shared_string, co_change -> co_change
#     are file-level couplings, NOT edges.
#   - LSP query-time overlay (OD-1): "lsp" is an always-live, never-persisted
#     provenance/freshness tag added at query time, NOT a stored edge source.
# The store does not rank — it tags; query.py ranks by provenance trust.
VALID_SOURCES = frozenset({"scip", "tree_sitter"})
VALID_PROVENANCE = frozenset({"parsed", "syntactic", "inferred"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS symbols(
    symbol TEXT PRIMARY KEY,            -- SCIP descriptor: the stable, location-independent id
    lang   TEXT NOT NULL DEFAULT '',
    file   TEXT NOT NULL DEFAULT '',
    name   TEXT NOT NULL DEFAULT '',
    kind   TEXT NOT NULL DEFAULT '',
    line   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS edges(
    src        TEXT NOT NULL,           -- symbols.symbol (the referencer / caller)
    dst        TEXT NOT NULL,           -- symbols.symbol (the referenced / callee)
    rel        TEXT NOT NULL,           -- references | calls | defines | co_change | ...
    source     TEXT NOT NULL,           -- one of VALID_SOURCES
    provenance TEXT NOT NULL DEFAULT 'parsed',
    PRIMARY KEY (src, dst, rel, source)
);
CREATE INDEX IF NOT EXISTS i_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS i_edges_src ON edges(src);
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, lang TEXT, content_hash TEXT, commit_sha TEXT
);
CREATE TABLE IF NOT EXISTS freshness(
    source TEXT, file TEXT, content_hash TEXT, commit_sha TEXT, tool_version TEXT,
    PRIMARY KEY (source, file)
);
CREATE TABLE IF NOT EXISTS coupling(
    file_a TEXT NOT NULL,                -- file_a < file_b (canonical unordered pair)
    file_b TEXT NOT NULL,
    kind   TEXT NOT NULL,                -- co_change | shared_string
    weight INTEGER NOT NULL DEFAULT 1,   -- support (co-change commits / shared tokens)
    PRIMARY KEY (file_a, file_b, kind)
);
CREATE INDEX IF NOT EXISTS i_coupling_a ON coupling(file_a);
CREATE INDEX IF NOT EXISTS i_coupling_b ON coupling(file_b);
CREATE TABLE IF NOT EXISTS watermark(
    repo_commit TEXT, built_at TEXT       -- store-level snapshot id; single row (10-freshness)
);
"""

# File-level coupling kinds — inferred signals that reference-walking cannot reach.
VALID_COUPLING = frozenset({"co_change", "shared_string"})

# The per-worktree store cache dir (OD-4): keyed to the worktree/repo root, gitignored.
STORE_DIR = ".codeflair"
STORE_FILE = "index.db"


def default_store_path(repo_root: str | os.PathLike[str], *, create: bool = False) -> str:
    """Resolve the per-worktree store path under ``repo_root`` (OD-4).

    git worktrees are N checkouts of one repo at different commits/dirty states; a store
    built for one is wrong for another. Keying ``.codeflair/`` to the **worktree root**
    gives each its own watermarked graph — clean isolation, no special logic beyond the
    keying. The dir is gitignored (same hygiene as ``.worktrees/``). When ``create`` is
    set the ``.codeflair/`` dir is made (the store file itself is created by SQLite).
    """
    root = os.fspath(repo_root)
    cache = os.path.join(root, STORE_DIR)
    if create:
        os.makedirs(cache, exist_ok=True)
    return os.path.join(cache, STORE_FILE)


@dataclass(frozen=True)
class Symbol:
    symbol: str  # the SCIP descriptor (primary key)
    lang: str = ""
    file: str = ""
    name: str = ""
    kind: str = ""
    line: int = 0


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    rel: str
    source: str
    provenance: str = "parsed"


class Store:
    """A fused code graph backed by SQLite. Open in-memory (``":memory:"``) for tests
    or a per-worktree file path in production. Truth is the files; this is a
    rebuildable, watermarked projection."""

    def __init__(self, path: str = ":memory:", *, read_only: bool = False) -> None:
        if read_only:
            # Open an existing index as a READ-ONLY view: no schema creation, no writes —
            # so a UACP consumer can attach against an index it must not mutate (CF-D9). The
            # index must already exist and carry the schema; a ro view never creates it.
            self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        else:
            self.con = sqlite3.connect(path)
            self.con.executescript(_SCHEMA)
            self.con.commit()

    # -- writes --------------------------------------------------------------
    def add_symbol(self, sym: Symbol) -> None:
        self.con.execute(
            "INSERT OR REPLACE INTO symbols(symbol,lang,file,name,kind,line) VALUES (?,?,?,?,?,?)",
            (sym.symbol, sym.lang, sym.file, sym.name, sym.kind, sym.line),
        )

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in VALID_SOURCES:
            raise ValueError(
                f"unknown edge source {edge.source!r}; expected one of {sorted(VALID_SOURCES)}"
            )
        if edge.provenance not in VALID_PROVENANCE:
            raise ValueError(
                f"unknown provenance {edge.provenance!r}; "
                f"expected one of {sorted(VALID_PROVENANCE)}"
            )
        self.con.execute(
            "INSERT OR REPLACE INTO edges(src,dst,rel,source,provenance) VALUES (?,?,?,?,?)",
            (edge.src, edge.dst, edge.rel, edge.source, edge.provenance),
        )

    def replace_source_file(self, source: str, file: str, edges: list[Edge]) -> None:
        """Source-scoped delete-and-replace: re-ingest one file's edges for one source
        without disturbing other sources' edges on the same file (per-source freshness)."""
        if source not in VALID_SOURCES:
            raise ValueError(f"unknown source {source!r}")
        cur = self.con.execute(
            "DELETE FROM edges WHERE source=? AND src IN (SELECT symbol FROM symbols WHERE file=?)",
            (source, file),
        )
        del cur
        for e in edges:
            if e.source != source:
                raise ValueError(f"edge source {e.source!r} != replace source {source!r}")
            self.add_edge(e)

    def add_coupling(self, file_a: str, file_b: str, kind: str, weight: int = 1) -> None:
        """Record a file-level coupling (co-change / shared-string). Pair is canonicalized
        so (A,B) and (B,A) collapse; re-adding accumulates weight."""
        if kind not in VALID_COUPLING:
            raise ValueError(
                f"unknown coupling kind {kind!r}; expected one of {sorted(VALID_COUPLING)}"
            )
        if file_a == file_b:
            return
        a, b = (file_a, file_b) if file_a < file_b else (file_b, file_a)
        self.con.execute(
            "INSERT INTO coupling(file_a,file_b,kind,weight) VALUES (?,?,?,?) "
            "ON CONFLICT(file_a,file_b,kind) DO UPDATE SET weight = weight + excluded.weight",
            (a, b, kind, weight),
        )

    def coupled_files(
        self, file: str, kind: str | None = None, min_weight: int = 1
    ) -> list[tuple[str, str, int]]:
        """Files coupled to ``file``, as ``(other_file, kind, weight)`` sorted by weight desc."""
        sql = (
            "SELECT CASE WHEN file_a=? THEN file_b ELSE file_a END AS other, kind, weight "
            "FROM coupling WHERE (file_a=? OR file_b=?) AND weight>=?"
        )
        params: list[object] = [file, file, file, min_weight]
        if kind is not None:
            sql += " AND kind=?"
            params.append(kind)
        sql += " ORDER BY weight DESC, other"
        return [(r[0], r[1], r[2]) for r in self.con.execute(sql, params).fetchall()]

    # -- freshness substrate (10-freshness / 11-substrate) -------------------
    def set_watermark(self, repo_commit: str, built_at: str) -> None:
        """Set the store-level watermark (single row): the commit this snapshot indexes
        and *when* it was built. ``built_at`` is INJECTED by the caller — the store never
        reads the wall clock (determinism belongs to the gate, not buried here)."""
        self.con.execute("DELETE FROM watermark")
        self.con.execute(
            "INSERT INTO watermark(repo_commit, built_at) VALUES (?,?)", (repo_commit, built_at)
        )
        self.con.commit()

    def watermark(self) -> tuple[str, str] | None:
        """The store-level watermark as ``(repo_commit, built_at)``, or ``None`` if unset."""
        row = self.con.execute("SELECT repo_commit, built_at FROM watermark LIMIT 1").fetchone()
        return (row[0], row[1]) if row else None

    def record_file(
        self, path: str, content_hash: str, *, lang: str = "", commit_sha: str = ""
    ) -> None:
        """Record (or update) a file's content hash — the freshness anchor a dirty-tree
        compare checks against (10-freshness). Re-recording the same path updates in place."""
        self.con.execute(
            "INSERT OR REPLACE INTO files(path,lang,content_hash,commit_sha) VALUES (?,?,?,?)",
            (path, lang, content_hash, commit_sha),
        )

    def record_freshness(
        self,
        source: str,
        file: str,
        content_hash: str,
        *,
        commit_sha: str = "",
        tool_version: str = "",
    ) -> None:
        """Record a PER-SOURCE freshness row (each source stales on its own clock). The
        ``(source, file)`` pair is the key; re-ingesting one source's view of a file updates
        in place without touching another source's row."""
        if source not in VALID_SOURCES:
            raise ValueError(
                f"unknown freshness source {source!r}; expected one of {sorted(VALID_SOURCES)}"
            )
        self.con.execute(
            "INSERT OR REPLACE INTO freshness(source,file,content_hash,commit_sha,tool_version) "
            "VALUES (?,?,?,?,?)",
            (source, file, content_hash, commit_sha, tool_version),
        )

    def file_hash(self, path: str) -> str | None:
        """The content hash the global ``files`` row recorded for ``path``, or ``None``.

        NOTE: this is the LAST-writer-wins global hash; ``record_file`` overwrites it on every
        ingest, so it cannot tell WHICH source is stale (F1). The reconcile must NOT trust it
        for serving — it uses the per-source ``freshness`` rows below. Kept for the P1
        detection primitive (``compare_file`` with no source) and advisory lookups."""
        row = self.con.execute("SELECT content_hash FROM files WHERE path=?", (path,)).fetchone()
        return row[0] if row else None

    def source_file_hash(self, source: str, path: str) -> str | None:
        """The content hash recorded for ``path`` BY A SPECIFIC source (F1), or ``None`` if
        that source never indexed the file. Each source stales on its own clock — a
        tree-sitter re-ingest of a file does not refresh SCIP's view of it — so a node's
        staleness must be judged against its OWN source's hash, not the global one."""
        row = self.con.execute(
            "SELECT content_hash FROM freshness WHERE source=? AND file=?", (source, path)
        ).fetchone()
        return row[0] if row else None

    def file_source_hashes(self, path: str) -> dict[str, str]:
        """Every source's recorded hash for ``path`` as ``{source: content_hash}`` — for the
        conservative reconcile of a node with no single source (transitive/coupling)."""
        return {
            src: ch
            for src, ch in self.con.execute(
                "SELECT source, content_hash FROM freshness WHERE file=?", (path,)
            ).fetchall()
        }

    def commit(self) -> None:
        self.con.commit()

    # -- reads ---------------------------------------------------------------
    def symbol(self, symbol: str) -> Symbol | None:
        row = self.con.execute(
            "SELECT symbol,lang,file,name,kind,line FROM symbols WHERE symbol=?", (symbol,)
        ).fetchone()
        return Symbol(*row) if row else None

    def symbols_in_file(self, file: str) -> list[str]:
        return [
            r[0]
            for r in self.con.execute(
                "SELECT symbol FROM symbols WHERE file=? ORDER BY line, symbol", (file,)
            ).fetchall()
        ]

    def count_symbols(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]

    def count_edges(self, source: str | None = None) -> int:
        if source is None:
            return self.con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return self.con.execute("SELECT COUNT(*) FROM edges WHERE source=?", (source,)).fetchone()[
            0
        ]

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

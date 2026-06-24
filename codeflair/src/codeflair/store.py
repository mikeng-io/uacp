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

import sqlite3
from dataclasses import dataclass

# Probe sources, in precision order (CF-D14 ladder): scip/lsp parsed > tree_sitter
# syntactic > grep text > co_change inferred. The store does not rank — it tags;
# query.py ranks by provenance trust.
VALID_SOURCES = frozenset({"scip", "lsp", "tree_sitter", "grep", "co_change"})
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
"""

# File-level coupling kinds — inferred signals that reference-walking cannot reach.
VALID_COUPLING = frozenset({"co_change", "shared_string"})


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

    def __init__(self, path: str = ":memory:") -> None:
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

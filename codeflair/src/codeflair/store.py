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
"""


@dataclass(frozen=True)
class Symbol:
    symbol: str          # the SCIP descriptor (primary key)
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
            "INSERT OR REPLACE INTO symbols(symbol,lang,file,name,kind,line) "
            "VALUES (?,?,?,?,?,?)",
            (sym.symbol, sym.lang, sym.file, sym.name, sym.kind, sym.line),
        )

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in VALID_SOURCES:
            raise ValueError(f"unknown edge source {edge.source!r}; expected one of {sorted(VALID_SOURCES)}")
        if edge.provenance not in VALID_PROVENANCE:
            raise ValueError(f"unknown provenance {edge.provenance!r}; expected one of {sorted(VALID_PROVENANCE)}")
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

    def commit(self) -> None:
        self.con.commit()

    # -- reads ---------------------------------------------------------------
    def symbol(self, symbol: str) -> Symbol | None:
        row = self.con.execute(
            "SELECT symbol,lang,file,name,kind,line FROM symbols WHERE symbol=?", (symbol,)
        ).fetchone()
        return Symbol(*row) if row else None

    def count_symbols(self) -> int:
        return self.con.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]

    def count_edges(self, source: str | None = None) -> int:
        if source is None:
            return self.con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return self.con.execute("SELECT COUNT(*) FROM edges WHERE source=?", (source,)).fetchone()[0]

    def close(self) -> None:
        self.con.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

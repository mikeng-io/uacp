"""Incremental delta re-index (D1 + #9): tree-sitter/hash change-detection drives a
re-index of ONLY the changed files (re-SCIP / re-tree-sitter just that set, via the
per-source ``replace_source_file`` primitive) and advances the watermark — without a
full-corpus re-index, and without removing the tree-sitter graph-source breadth floor.

Change detection rides the P1 freshness substrate (per-file/per-source content hashes):
a file is changed iff its working-tree hash differs from the source's recorded hash.
The producer seam (``reindex_file``) is injected, so the orchestration is hermetically
testable without a real SCIP/tree-sitter toolchain.
"""

import pytest

from codeflair import Store, Symbol, content_hash
from codeflair.delta import ChangeSet, FileIndex, delta_reindex, detect_changed_files
from codeflair.scip_ingest import SCIP_TOOL_VERSION, ingest_scip_json

M = "scip-go gomod example.com/m v1.0.0 `example.com/m/p`"
A_FOO = f"{M}/AFoo()."
B_BAR = f"{M}/BBar()."
_DEF, _REF = 1, 0


def _occ(symbol: str, line: int, role: int) -> dict:
    return {"symbol": symbol, "range": [line, 0, 10], "symbol_roles": role}


def _seed_two_file_index(s: Store, a: bytes, b: bytes) -> None:
    """Seed a store as if a.go (defines AFoo, references BBar) and b.go (defines BBar)
    were SCIP-ingested at commit-0, populating symbols + edges + per-source freshness."""
    index = {
        "documents": [
            {"relative_path": "a.go", "occurrences": [_occ(A_FOO, 1, _DEF), _occ(B_BAR, 2, _REF)]},
            {"relative_path": "b.go", "occurrences": [_occ(B_BAR, 1, _DEF)]},
        ]
    }
    s.set_watermark("commit-0", "2026-01-01T00:00:00Z")
    ingest_scip_json(s, index, file_contents={"a.go": a, "b.go": b}, commit_sha="commit-0")


# -- pure change detection ---------------------------------------------------
def test_detect_changed_files_classifies_added_modified_removed_unchanged():
    s = Store()
    _seed_two_file_index(s, b"old-a", b"same-b")
    current = {
        "a.go": b"NEW-a",  # hash differs -> modified
        "b.go": b"same-b",  # hash matches -> unchanged
        "c.go": b"brand-new",  # no recorded hash -> added
        # b-was-removed: "b.go" still present; remove nothing here
    }
    cs = detect_changed_files(s, current, source="scip")
    assert cs.modified == frozenset({"a.go"})
    assert cs.unchanged == frozenset({"b.go"})
    assert cs.added == frozenset({"c.go"})
    assert cs.removed == frozenset()
    assert cs.changed == frozenset({"a.go", "c.go"})


def test_detect_changed_files_flags_removed():
    s = Store()
    _seed_two_file_index(s, b"a", b"b")
    cs = detect_changed_files(s, {"a.go": b"a"}, source="scip")  # b.go gone from the tree
    assert cs.removed == frozenset({"b.go"})
    assert cs.unchanged == frozenset({"a.go"})


# -- the NEGATIVE acceptance: only the changed file is re-indexed -------------
def test_delta_reindex_touches_only_the_changed_file():
    s = Store()
    _seed_two_file_index(s, b"old-a", b"keep-b")

    # snapshot b.go's symbol + edge rows BEFORE the delta — they must be byte-identical after
    def _file_symbols(file: str) -> list[tuple]:
        return s.con.execute(
            "SELECT symbol,lang,file,name,kind,line FROM symbols WHERE file=? ORDER BY symbol",
            (file,),
        ).fetchall()

    def _file_edges(file: str) -> list[tuple]:
        return sorted(
            s.con.execute(
                "SELECT src,dst,rel,source,provenance FROM edges "
                "WHERE src IN (SELECT symbol FROM symbols WHERE file=?)",
                (file,),
            ).fetchall()
        )

    b_syms_before = _file_symbols("b.go")
    b_edges_before = _file_edges("b.go")

    invoked: list[str] = []

    def producer(path: str, data: bytes) -> FileIndex:
        invoked.append(path)
        from codeflair import Edge  # noqa: PLC0415

        # a.go now CALLS a new symbol instead of referencing BBar — emit a.go's edges only
        new_dst = f"{M}/NewDep()."
        return FileIndex(
            symbols=[Symbol(symbol=A_FOO, lang="go", file="a.go", name="AFoo().", line=1)],
            edges=[Edge(src=A_FOO, dst=new_dst, rel="calls", source="scip", provenance="parsed")],
        )

    cs = delta_reindex(
        s,
        {"a.go": b"NEW-a", "b.go": b"keep-b"},
        source="scip",
        reindex_file=producer,
        commit_sha="commit-1",
        built_at="2026-02-02T00:00:00Z",
        tool_version=SCIP_TOOL_VERSION,
    )

    # the producer ran for the changed file ONLY — never the whole corpus
    assert invoked == ["a.go"]
    assert cs.changed == frozenset({"a.go"})
    # b.go's symbols + edges are byte-identical — proof of no full re-index
    assert _file_symbols("b.go") == b_syms_before
    assert _file_edges("b.go") == b_edges_before
    # a.go's edges were replaced: the old a.go->BBar reference is gone, the new call is present
    a_edges = {(src, dst, rel) for src, dst, rel, *_ in _file_edges("a.go")}
    assert (A_FOO, f"{M}/NewDep().", "calls") in a_edges
    assert (A_FOO, B_BAR, "calls") not in a_edges and (A_FOO, B_BAR, "references") not in a_edges
    # a.go's freshness hash advanced to the new content
    assert s.source_file_hash("scip", "a.go") == content_hash(b"NEW-a")
    assert s.source_file_hash("scip", "b.go") == content_hash(b"keep-b")  # untouched


def test_delta_reindex_advances_watermark():
    s = Store()
    _seed_two_file_index(s, b"a0", b"b0")
    assert s.watermark() == ("commit-0", "2026-01-01T00:00:00Z")

    def producer(path: str, data: bytes) -> FileIndex:
        return FileIndex(symbols=[], edges=[])

    delta_reindex(
        s,
        {"a.go": b"a1", "b.go": b"b0"},
        source="scip",
        reindex_file=producer,
        commit_sha="commit-9",
        built_at="2026-09-09T00:00:00Z",
    )
    assert s.watermark() == ("commit-9", "2026-09-09T00:00:00Z")


def test_delta_reindex_is_a_noop_producer_call_when_nothing_changed():
    s = Store()
    _seed_two_file_index(s, b"a", b"b")
    invoked: list[str] = []

    def producer(path: str, data: bytes) -> FileIndex:
        invoked.append(path)
        return FileIndex(symbols=[], edges=[])

    cs = delta_reindex(
        s,
        {"a.go": b"a", "b.go": b"b"},  # identical content
        source="scip",
        reindex_file=producer,
        commit_sha="commit-0b",
        built_at="2026-01-02T00:00:00Z",
    )
    assert invoked == []  # nothing re-indexed
    assert cs.changed == frozenset()
    assert s.watermark() == ("commit-0b", "2026-01-02T00:00:00Z")  # still advances the watermark


# -- D1: the tree-sitter graph-source floor is PRESERVED, not removed --------
def test_delta_reindex_preserves_tree_sitter_floor_edges():
    """A delta re-index of a changed file via the SCIP source must leave the file's
    tree-sitter (graph-source breadth-floor) edges intact — the source-scoped replace
    only touches the source being re-indexed. The floor is ADDED-to, never removed."""
    from codeflair import Edge  # noqa: PLC0415

    s = Store()
    _seed_two_file_index(s, b"old-a", b"b")
    # a tree-sitter floor edge on a.go (a syntactic guess from the breadth floor)
    ts_sym = "tree-sitter go a.go:AFoo#0"
    s.add_symbol(Symbol(symbol=ts_sym, lang="go", file="a.go", name="AFoo", line=0))
    s.add_edge(
        Edge(src=ts_sym, dst=B_BAR, rel="calls", source="tree_sitter", provenance="syntactic")
    )
    s.commit()
    assert s.count_edges(source="tree_sitter") == 1

    def producer(path: str, data: bytes) -> FileIndex:
        return FileIndex(symbols=[], edges=[])  # SCIP source emits nothing new here

    delta_reindex(
        s,
        {"a.go": b"NEW-a", "b.go": b"b"},
        source="scip",
        reindex_file=producer,
        commit_sha="commit-1",
        built_at="2026-02-02T00:00:00Z",
    )
    # the tree-sitter floor edge SURVIVES the scip-scoped delta (D1: floor preserved)
    assert s.count_edges(source="tree_sitter") == 1
    surviving = s.con.execute(
        "SELECT src,dst,source FROM edges WHERE source='tree_sitter'"
    ).fetchall()
    assert surviving == [(ts_sym, B_BAR, "tree_sitter")]


def test_delta_reindex_via_tree_sitter_producer_emits_floor_edges():
    """The change-detector can drive a tree-sitter (graph-source) re-index too: a
    tree_sitter-sourced producer persists tree_sitter edges through the delta path."""
    from codeflair import Edge  # noqa: PLC0415

    s = Store()
    _seed_two_file_index(s, b"old-a", b"b")
    ts_sym = "tree-sitter go a.go:AFoo#0"
    ts_dst = "tree-sitter go a.go:helper#5"

    def producer(path: str, data: bytes) -> FileIndex:
        return FileIndex(
            symbols=[
                Symbol(symbol=ts_sym, lang="go", file="a.go", name="AFoo", line=0),
                Symbol(symbol=ts_dst, lang="go", file="a.go", name="helper", line=5),
            ],
            edges=[
                Edge(
                    src=ts_sym,
                    dst=ts_dst,
                    rel="calls",
                    source="tree_sitter",
                    provenance="syntactic",
                )
            ],
        )

    delta_reindex(
        s,
        {"a.go": b"NEW-a", "b.go": b"b"},
        source="tree_sitter",
        reindex_file=producer,
        commit_sha="commit-1",
        built_at="2026-02-02T00:00:00Z",
    )
    assert s.count_edges(source="tree_sitter") == 1
    assert (ts_sym, ts_dst) in {
        (r[0], r[1])
        for r in s.con.execute("SELECT src,dst FROM edges WHERE source='tree_sitter'").fetchall()
    }


def test_delta_reindex_drops_removed_file_rows():
    s = Store()
    _seed_two_file_index(s, b"a", b"b")
    assert s.symbol(B_BAR) is not None  # b.go's symbol exists pre-delta

    def producer(path: str, data: bytes) -> FileIndex:
        return FileIndex(symbols=[], edges=[])

    cs = delta_reindex(
        s,
        {"a.go": b"a"},  # b.go deleted from the working tree
        source="scip",
        reindex_file=producer,
        commit_sha="commit-1",
        built_at="2026-02-02T00:00:00Z",
    )
    assert cs.removed == frozenset({"b.go"})
    # b.go's per-source freshness row is gone; its file row too
    assert s.source_file_hash("scip", "b.go") is None
    assert s.file_hash("b.go") is None


def test_change_set_changed_is_added_plus_modified():
    cs = ChangeSet(
        added=frozenset({"c"}),
        modified=frozenset({"a"}),
        removed=frozenset({"d"}),
        unchanged=frozenset({"b"}),
    )
    assert cs.changed == frozenset({"a", "c"})


# -- gated: drive the delta path with the REAL tree-sitter floor producer -----
def test_delta_reindex_with_real_tree_sitter_producer():
    pytest.importorskip("tree_sitter_languages")
    from codeflair import Edge  # noqa: PLC0415
    from codeflair.treesitter_ingest import ingest_tree_sitter  # noqa: PLC0415

    s = Store()
    _seed_two_file_index(s, b"package p\n", b"package p\n")

    def producer(path: str, data: bytes) -> FileIndex:
        # parse the single changed file with the real tree-sitter floor into a scratch
        # store, then lift its symbols + edges back out as a FileIndex.
        scratch = Store()
        ingest_tree_sitter(scratch, {path: ("go", data)})
        syms = [scratch.symbol(sym) for sym in scratch.symbols_in_file(path)]
        edges = [
            Edge(src=src, dst=dst, rel=rel, source=src_, provenance=prov)
            for src, dst, rel, src_, prov in scratch.con.execute(
                "SELECT src,dst,rel,source,provenance FROM edges WHERE source='tree_sitter'"
            ).fetchall()
        ]
        return FileIndex(symbols=[x for x in syms if x is not None], edges=edges)

    a_src = b"package p\n\nfunc AFoo() { helper() }\n\nfunc helper() {}\n"
    delta_reindex(
        s,
        {"a.go": a_src, "b.go": b"package p\n"},
        source="tree_sitter",
        reindex_file=producer,
        commit_sha="commit-1",
        built_at="2026-02-02T00:00:00Z",
    )
    assert s.count_edges(source="tree_sitter") >= 1  # the floor emitted its edges via delta

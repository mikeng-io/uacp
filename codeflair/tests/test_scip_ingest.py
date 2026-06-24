"""SCIP ingest: parse SCIP JSON -> store, then prove blast radius end-to-end."""

from codeflair import Store, blast_radius, heatmap
from codeflair.scip_ingest import ingest_scip_json

M = "scip-go gomod example.com/m v1.0.0 `example.com/m/p`"
FOO, BAR, BAZ = f"{M}/Foo().", f"{M}/Bar().", f"{M}/Baz()."
_DEF, _REF = 1, 0


def _occ(symbol: str, line: int, role: int) -> dict:
    return {"symbol": symbol, "range": [line, 0, 10], "symbol_roles": role}


def _fixture() -> dict:
    # a.go: def Foo@10, def Bar@20; ref Baz@12 (in Foo), ref Foo@22 (in Bar)
    # b.go: def Baz@5;            ref Bar@7  (in Baz)
    # => enclosing-def edges: Foo->Baz, Bar->Foo, Baz->Bar  (a 3-cycle)
    return {
        "documents": [
            {
                "relative_path": "a.go",
                "occurrences": [
                    _occ(FOO, 10, _DEF),
                    _occ(BAZ, 12, _REF),
                    _occ(BAR, 20, _DEF),
                    _occ(FOO, 22, _REF),
                ],
            },
            {
                "relative_path": "b.go",
                "occurrences": [
                    _occ(BAZ, 5, _DEF),
                    _occ(BAR, 7, _REF),
                ],
            },
        ]
    }


def test_ingest_counts_documents_symbols_edges():
    s = Store()
    stats = ingest_scip_json(s, _fixture())
    assert stats.documents == 2
    assert stats.symbols == 3  # Foo, Bar, Baz
    assert stats.edges == 3  # Foo->Baz, Bar->Foo, Baz->Bar
    assert s.count_symbols() == 3
    assert s.count_edges(source="scip") == 3


def test_ingest_records_symbol_metadata_from_definition():
    s = Store()
    ingest_scip_json(s, _fixture())
    foo = s.symbol(FOO)
    assert foo is not None
    assert foo.lang == "go"  # derived from the scip-go scheme
    assert foo.file == "a.go"  # from the Definition occurrence
    assert foo.line == 10
    assert foo.name == "Foo()."  # last descriptor


def test_ingest_attributes_reference_to_enclosing_definition():
    # The Baz reference at a.go:12 sits inside Foo (def@10) -> edge Foo->Baz, not Bar->Baz.
    s = Store()
    ingest_scip_json(s, _fixture())
    callers_of_baz = blast_radius(s, BAZ, direction="callers")
    assert callers_of_baz.get(FOO) == 1  # Foo directly references Baz
    assert BAR not in {k for k, v in callers_of_baz.items() if v == 1}


def test_blast_radius_is_transitive_over_ingested_cycle():
    # Foo->Baz->Bar->Foo. Callers of Baz: Foo(1), then Bar(2). Cycle must terminate.
    s = Store()
    ingest_scip_json(s, _fixture())
    radius = blast_radius(s, BAZ, max_hops=5, direction="callers")
    assert radius == {BAZ: 0, FOO: 1, BAR: 2}


def test_heatmap_over_ingested_graph_ranks_by_distance():
    s = Store()
    ingest_scip_json(s, _fixture())
    hm = heatmap(s, BAZ, k=10)
    syms = [e.symbol for e in hm]
    assert syms == [FOO, BAR]  # Foo (1 hop) ranks above Bar (2 hops)
    assert all("scip" in e.via for e in hm)


def test_local_symbols_and_rangeless_occurrences_are_skipped():
    s = Store()
    data = {
        "documents": [
            {
                "relative_path": "x.go",
                "occurrences": [
                    _occ(FOO, 1, _DEF),
                    {
                        "symbol": "local 0",
                        "range": [2, 0, 3],
                        "symbol_roles": _DEF,
                    },  # local -> skip
                    {"symbol": BAR, "symbol_roles": _REF},  # no range -> skip
                ],
            }
        ]
    }
    stats = ingest_scip_json(s, data)
    assert stats.symbols == 1  # only Foo; local + rangeless dropped
    assert s.symbol("local 0") is None


def test_ingest_skips_stdlib_and_build_cache_documents():
    # scip-go emits documents for the stdlib + go-build cache (paths escaping the repo).
    # Those must not enter the graph — only real repo files.
    data = {
        "documents": [
            {"relative_path": "internal/api/server.go", "occurrences": [_occ(FOO, 3, _DEF)]},
            {
                "relative_path": "../../Library/Caches/go-build/ab/cached-d",
                "occurrences": [_occ(BAR, 1, _DEF)],
            },
            {
                "relative_path": "/usr/local/go/src/testing/testing.go",
                "occurrences": [_occ(BAZ, 1, _DEF)],
            },
        ]
    }
    s = Store()
    stats = ingest_scip_json(s, data)
    assert stats.documents == 1  # only the repo doc
    assert s.symbol(FOO) is not None
    assert s.symbol(BAR) is None  # build-cache def dropped
    assert s.symbol(BAZ) is None  # stdlib def dropped


def test_ingest_empty_index_is_clean():
    s = Store()
    stats = ingest_scip_json(s, {"documents": []})
    assert stats == type(stats)(documents=0, symbols=0, edges=0)
    assert s.count_symbols() == 0

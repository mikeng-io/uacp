"""Expansion loop: fuse precise edges + inferred coupling; gaps detection."""
from codeflair import Store, Symbol, Edge, expand, find_test_gaps
from codeflair.query import heatmap


def _store_with(symbols: dict[str, str], edges: list[Edge], couplings=()) -> Store:
    s = Store()
    for sym, file in symbols.items():
        s.add_symbol(Symbol(symbol=sym, file=file, name=sym))
    for e in edges:
        s.add_edge(e)
    for a, b, kind, w in couplings:
        s.add_coupling(a, b, kind, w)
    s.commit()
    return s


def test_expand_precise_only_matches_heatmap_when_no_coupling():
    s = _store_with(
        {"A": "a.go", "B": "b.go", "C": "c.go"},
        [Edge("B", "A", "calls", "scip"), Edge("C", "B", "calls", "scip")],
    )
    res = expand(s, "A", include_coupling=False)
    assert [e.symbol for e in res.heatmap] == ["B", "C"]
    assert res.n_inferred == 0
    assert res.n_precise == 2


def test_expand_adds_inferred_symbols_from_coupled_files():
    # B calls A (precise). a.go co-changes with x.go, which defines X (no edge to A).
    s = _store_with(
        {"A": "a.go", "B": "b.go", "X": "x.go"},
        [Edge("B", "A", "calls", "scip")],
        couplings=[("a.go", "x.go", "co_change", 5)],
    )
    res = expand(s, "A")
    syms = [e.symbol for e in res.heatmap]
    assert "B" in syms and "X" in syms       # precise B + inferred X
    assert res.n_inferred == 1


def test_precise_outranks_inferred_at_face():
    s = _store_with(
        {"A": "a.go", "B": "b.go", "X": "x.go"},
        [Edge("B", "A", "calls", "scip")],
        couplings=[("a.go", "x.go", "co_change", 9)],
    )
    res = expand(s, "A")
    # B (precise parsed call, hop 1) must rank above X (inferred coupling, hop 1)
    assert res.heatmap[0].symbol == "B"
    b = next(e for e in res.heatmap if e.symbol == "B")
    x = next(e for e in res.heatmap if e.symbol == "X")
    assert b.score > x.score
    assert "coupling" in x.via


def test_precise_evidence_wins_over_coupling_for_same_symbol():
    # X is reachable BOTH precisely (edge) and via coupling — keep the precise entry.
    s = _store_with(
        {"A": "a.go", "X": "x.go"},
        [Edge("X", "A", "calls", "scip")],
        couplings=[("a.go", "x.go", "co_change", 9)],
    )
    res = expand(s, "A")
    x = next(e for e in res.heatmap if e.symbol == "X")
    assert x.via == "calls/scip"             # precise, not coupling
    assert res.n_inferred == 0               # X already precise -> not double-counted


def test_find_test_gaps_flags_untested_impacted_symbol():
    # B (prod) calls A; nothing in a test file references A -> A's impact set is unguarded.
    s = _store_with(
        {"A": "a.go", "B": "b.go"},
        [Edge("B", "A", "calls", "scip")],
    )
    res = expand(s, "A")
    assert any(g.symbol == "B" for g in res.gaps)


def test_test_caller_clears_the_gap():
    s = _store_with(
        {"A": "a.go", "B": "b.go"},
        [Edge("B", "A", "calls", "scip"),
         Edge("TB", "B", "calls", "scip")],   # a test references B
    )
    s.add_symbol(Symbol(symbol="TB", file="b_test.go", name="TB"))
    s.commit()
    gaps = find_test_gaps(s, heatmap(s, "A", k=10))
    assert all(g.symbol != "B" for g in gaps)  # B is referenced by a test -> not a gap


def test_expand_is_deterministic():
    s = _store_with(
        {"A": "a.go", "B": "b.go", "X": "x.go"},
        [Edge("B", "A", "calls", "scip")],
        couplings=[("a.go", "x.go", "co_change", 5)],
    )
    a = [(e.symbol, e.score, e.hop) for e in expand(s, "A").heatmap]
    b = [(e.symbol, e.score, e.hop) for e in expand(s, "A").heatmap]
    assert a == b

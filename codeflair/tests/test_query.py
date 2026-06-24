"""Query: blast radius (transitive closure) + deterministic heatmap ranking."""

import pytest

from codeflair import Edge, Store, Symbol, blast_radius, heatmap


def _graph(edges: list[Edge]) -> Store:
    s = Store()
    names = {e.src for e in edges} | {e.dst for e in edges}
    for n in names:
        s.add_symbol(Symbol(symbol=n, name=n))
    for e in edges:
        s.add_edge(e)
    return s


def test_blast_radius_one_hop_callers():
    # B and C both call A. Changing A affects B and C (1 hop), not D.
    s = _graph(
        [
            Edge("B", "A", "calls", "scip"),
            Edge("C", "A", "calls", "scip"),
            Edge("D", "X", "calls", "scip"),
        ]
    )
    radius = blast_radius(s, "A", max_hops=3, direction="callers")
    assert radius == {"A": 0, "B": 1, "C": 1}


def test_blast_radius_is_transitive_with_correct_min_hop():
    # C -> B -> A. Changing A reaches B at hop 1, C at hop 2.
    s = _graph([Edge("B", "A", "calls", "scip"), Edge("C", "B", "calls", "scip")])
    radius = blast_radius(s, "A", max_hops=3, direction="callers")
    assert radius == {"A": 0, "B": 1, "C": 2}


def test_blast_radius_respects_max_hops():
    s = _graph(
        [
            Edge("B", "A", "calls", "scip"),
            Edge("C", "B", "calls", "scip"),
            Edge("D", "C", "calls", "scip"),
        ]
    )
    radius = blast_radius(s, "A", max_hops=1, direction="callers")
    assert radius == {"A": 0, "B": 1}  # C (hop 2), D (hop 3) excluded


def test_blast_radius_terminates_on_cycle():
    # A <-> B cycle must not loop forever (UNION dedupes).
    s = _graph([Edge("A", "B", "calls", "scip"), Edge("B", "A", "calls", "scip")])
    radius = blast_radius(s, "A", max_hops=5, direction="callers")
    assert radius == {"A": 0, "B": 1}


def test_callees_direction_walks_outgoing():
    # A calls B calls C. A's callees are B (1) and C (2).
    s = _graph([Edge("A", "B", "calls", "scip"), Edge("B", "C", "calls", "scip")])
    assert blast_radius(s, "A", direction="callees") == {"A": 0, "B": 1, "C": 2}


def test_heatmap_excludes_seed_and_ranks_closer_higher():
    # B (1 hop) should outrank C (2 hops) under hop decay, same edge type/provenance.
    s = _graph([Edge("B", "A", "calls", "scip"), Edge("C", "B", "calls", "scip")])
    hm = heatmap(s, "A", k=10)
    syms = [e.symbol for e in hm]
    assert "A" not in syms  # seed is not its own impact
    assert syms == ["B", "C"]  # closer ranked first
    assert hm[0].score > hm[1].score


def test_heatmap_provenance_trust_outranks_at_equal_distance():
    # B reached via a parsed SCIP call; C via an inferred co_change — both 1 hop.
    # Parsed must outrank inferred (the CF-D14 precision ladder, as a score).
    s = _graph(
        [
            Edge("B", "A", "calls", "scip", provenance="parsed"),
            Edge("C", "A", "co_change", "co_change", provenance="inferred"),
        ]
    )
    hm = heatmap(s, "A", k=10)
    assert hm[0].symbol == "B"
    assert hm[1].symbol == "C"
    assert "scip" in hm[0].via


def test_heatmap_is_deterministic_and_total_ordered():
    # Two nodes with identical score must still order stably (by symbol) across runs.
    s = _graph([Edge("Zeb", "A", "calls", "scip"), Edge("Abe", "A", "calls", "scip")])
    first = [(e.symbol, e.score) for e in heatmap(s, "A", k=10)]
    second = [(e.symbol, e.score) for e in heatmap(s, "A", k=10)]
    assert first == second
    assert [sym for sym, _ in first] == ["Abe", "Zeb"]  # equal score -> lexical tiebreak


def test_heatmap_respects_k():
    s = _graph([Edge(c, "A", "calls", "scip") for c in ["B", "C", "D", "E", "F"]])
    assert len(heatmap(s, "A", k=3)) == 3


def test_empty_radius_returns_empty_heatmap():
    s = _graph([Edge("B", "A", "calls", "scip")])
    assert heatmap(s, "Nonexistent", k=5) == []


def test_blast_radius_rejects_bad_direction():
    s = _graph([Edge("B", "A", "calls", "scip")])
    with pytest.raises(ValueError, match="direction"):
        blast_radius(s, "A", direction="sideways")

"""P4 — output honesty: the byte-stable JSON contract + replayable, watermarked trace.

The council rejected "same nodes" as too weak, so these tests assert the FULL contract:
nodes AND their scores/order/hops/freshness/provenance, gaps, and the kept/pruned beam from
the trace; that re-serializing is BYTE-IDENTICAL; that replaying from the trace reconstructs
the same RANKED nodes/scores/order (not just the node set); and that a watermark/hash
mismatch flags the trace stale.
"""

from __future__ import annotations

import dataclasses
import json

from codeflair import (
    Edge,
    Store,
    Symbol,
    compute_basis_hash,
    content_hash,
    expand,
    mark_stale,
    replay,
    to_json,
)


def _store_with(symbols, edges, couplings=(), *, watermark=("c0ffee", "T0")) -> Store:
    s = Store()
    for sym, file in symbols.items():
        s.add_symbol(Symbol(symbol=sym, file=file, name=sym))
    for e in edges:
        s.add_edge(e)
    for a, b, kind, w in couplings:
        s.add_coupling(a, b, kind, w)
    # record file hashes so there is a real content-hash BASIS the trace can stale against.
    files = sorted({f for f in symbols.values()})
    for f in files:
        s.record_file(f, content_hash(f.encode()))
    s.set_watermark(*watermark)
    s.commit()
    return s


def _fixture() -> Store:
    # B calls A (precise hop1); C calls B (precise hop2); a.go co-changes x.go -> inferred X.
    return _store_with(
        {"A": "a.go", "B": "b.go", "C": "c.go", "X": "x.go"},
        [Edge("B", "A", "calls", "scip"), Edge("C", "B", "calls", "scip")],
        couplings=[("a.go", "x.go", "co_change", 5)],
    )


# --------------------------------------------------------------------------- #
# 1. The structured JSON contract {nodes[], gaps[], trace{}}
# --------------------------------------------------------------------------- #


def test_contract_shape_and_node_fields():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    doc = json.loads(to_json(res))

    assert set(doc) == {"nodes", "gaps", "trace"}

    # every node carries the full evidence trail
    assert res.heatmap, "fixture should produce a non-empty heatmap"
    for node, entry in zip(doc["nodes"], res.heatmap, strict=True):
        assert set(node) == {"symbol", "score", "hop", "via", "source", "freshness"}
        assert node["symbol"] == entry.symbol
        assert node["score"] == entry.score
        assert node["hop"] == entry.hop
        assert node["via"] == entry.via
        assert node["source"] == entry.source
        assert node["freshness"] == entry.freshness

    # nodes[] preserves the RANK order (not re-sorted by the serializer)
    assert [n["symbol"] for n in doc["nodes"]] == [e.symbol for e in res.heatmap]

    # gaps are a first-class output
    assert [g["symbol"] for g in doc["gaps"]] == [g.symbol for g in res.gaps]
    for g in doc["gaps"]:
        assert set(g) == {"symbol", "file", "reason"}


def test_trace_carries_watermark_query_and_beam():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    trace = json.loads(to_json(res))["trace"]

    assert trace["watermark"] == {"repo_commit": "c0ffee", "built_at": "T0"}
    assert trace["query"]["seed"] == "A"
    assert trace["query"]["k"] == 20
    assert trace["query"]["max_hops"] == 3
    assert trace["query"]["direction"] == "callers"

    # the hop log records which probes ran and the candidates each expanded
    probes = [h["probe"] for h in trace["hops"]]
    assert "precise" in probes and "coupling" in probes
    # at least one candidate carries a score + admitted flag
    cand = trace["hops"][0]["candidates"][0]
    assert set(cand) == {"symbol", "score", "hop", "via", "source", "admitted"}

    # the kept beam (result order) + the pruned beam are both present
    assert trace["result_order"] == [e.symbol for e in res.heatmap]
    assert "pruned" in trace


def test_p2_signals_surface_in_the_trace():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    sig = json.loads(to_json(res))["trace"]["signals"]
    assert set(sig) == {"lsp_degraded", "warnings", "conflicts", "overlay_only"}
    assert sig["lsp_degraded"] is False  # store-authoritative path


# --------------------------------------------------------------------------- #
# 2. Byte-stable replay of the FULL contract
# --------------------------------------------------------------------------- #


def test_reserialization_is_byte_identical():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    assert to_json(res) == to_json(res)


def test_mutating_a_score_breaks_byte_stability():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    baseline = to_json(res)

    # mutate ONE node's score -> the serialized contract must change
    bumped = list(res.heatmap)
    bumped[0] = dataclasses.replace(bumped[0], score=bumped[0].score + 0.001)
    mutated = dataclasses.replace(res, heatmap=bumped)
    assert to_json(mutated) != baseline


def test_reordering_nodes_breaks_byte_stability():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    baseline = to_json(res)

    reordered = dataclasses.replace(res, heatmap=list(reversed(res.heatmap)))
    assert to_json(reordered) != baseline


def test_replay_reconstructs_ranked_nodes_scores_and_order():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)

    replayed = replay(res.trace)
    # NOT just the node SET — the ranked order AND the scores must match
    assert [(n.symbol, n.score, n.hop) for n in replayed] == [
        (e.symbol, e.score, e.hop) for e in res.heatmap
    ]
    # the heatmap is genuinely multi-node and ranked (so order is load-bearing, not trivial)
    assert len(replayed) >= 2


def test_replay_diverges_when_a_logged_score_is_corrupted():
    """Replay re-derives the RANKING from the logged beam — corrupt a candidate score and
    the reconstructed order/scores must stop matching the result (non-vacuous re-derivation)."""
    s = _fixture()
    res = expand(s, "A", capture_trace=True)

    hops = list(res.trace.hops)
    cands = list(hops[0].candidates)
    cands[0] = dataclasses.replace(cands[0], score=cands[0].score + 5.0)
    hops[0] = dataclasses.replace(hops[0], candidates=tuple(cands))
    corrupted = dataclasses.replace(res.trace, hops=tuple(hops))

    replayed = replay(corrupted)
    assert [(n.symbol, n.score) for n in replayed] != [(e.symbol, e.score) for e in res.heatmap]


# --------------------------------------------------------------------------- #
# 3. Trace staleness — watermark / content-hash basis
# --------------------------------------------------------------------------- #


def test_matching_basis_is_fresh():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)
    fresh = mark_stale(res.trace, compute_basis_hash(s))
    assert fresh.stale is False
    assert json.loads(to_json(dataclasses_replace_trace(res, fresh)))["trace"]["stale"] is False


def test_working_tree_moving_on_marks_the_trace_stale():
    s = _fixture()
    res = expand(s, "A", capture_trace=True)

    # simulate the working tree moving on past the trace's watermark basis
    s.record_file("a.go", content_hash(b"a.go EDITED since the index was built"))
    s.commit()

    stale = mark_stale(res.trace, compute_basis_hash(s))
    assert stale.stale is True
    assert json.loads(to_json(dataclasses_replace_trace(res, stale)))["trace"]["stale"] is True


def test_basis_hash_is_deterministic_and_content_keyed():
    s = _fixture()
    h1 = compute_basis_hash(s)
    h2 = compute_basis_hash(s)
    assert h1 == h2  # deterministic
    s.record_file("b.go", content_hash(b"b.go changed"))
    s.commit()
    assert compute_basis_hash(s) != h1  # content-keyed


# --------------------------------------------------------------------------- #
# Determinism: no wall-clock / set-iteration nondeterminism
# --------------------------------------------------------------------------- #


def test_no_wallclock_two_independent_runs_are_byte_identical():
    # built_at is INJECTED via the watermark; the serializer must echo it, never read now().
    s1 = _fixture()
    s2 = _fixture()
    assert to_json(expand(s1, "A", capture_trace=True)) == to_json(
        expand(s2, "A", capture_trace=True)
    )


def test_to_json_top_level_keys_sorted():
    s = _fixture()
    raw = to_json(expand(s, "A", capture_trace=True))
    # sort_keys -> deterministic key order across the document
    assert raw.index('"gaps"') < raw.index('"nodes"') < raw.index('"trace"')


# small local helper: swap a (possibly re-marked) trace back onto a result for serialization
def dataclasses_replace_trace(res, trace):
    return dataclasses.replace(res, trace=trace)

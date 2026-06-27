"""P6 — the full heat formula wired end-to-end through the store / heatmap / expand, plus
the swappable score() seam (OD-3).

The per-term unit shapes live in test_policy.py; here each term is driven from REAL store
metadata so the wiring is proven, not just the arithmetic: fan-in from the edge graph,
recency from injected ``changed_at`` + ``now``, PMI from co-change couplings, and the
multi-probe agreement bonus from the expansion loop's cross-probe corroboration (including
the guard that it never boosts an ``unreconciled`` node). A trivial alternate policy proves
both ``heatmap`` and ``expand`` consult the injected policy, and a replay check proves the
trace re-derives the corroboration-boosted ranking.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import pytest

from codeflair.expand import expand
from codeflair.freshness import content_hash
from codeflair.policy import PolicyD
from codeflair.query import heatmap
from codeflair.store import Edge, Store, Symbol
from codeflair.trace import replay

P = PolicyD()


def _store(symbols: dict[str, str], edges: Iterable[tuple[str, str, str]] = ()) -> Store:
    s = Store()
    for sym, file in symbols.items():
        s.add_symbol(Symbol(symbol=sym, file=file, name=sym))
    for src, dst, rel in edges:
        s.add_edge(Edge(src=src, dst=dst, rel=rel, source="scip", provenance="parsed"))
    s.commit()
    return s


def _by_sym(entries: list) -> dict[str, object]:
    return {e.symbol: e for e in entries}


# --------------------------------------------------------------------------- #
# Term 1 — recency from injected changed_at + now (heatmap)
# --------------------------------------------------------------------------- #


def test_recency_more_recent_file_scores_higher_via_store_metadata():
    # B and C are identical hop-1 callers of A; only their files' change ordinals differ.
    s = _store({"A": "a.py", "B": "b.py", "C": "c.py"}, [("B", "A", "calls"), ("C", "A", "calls")])
    s.record_file("b.py", "h", changed_at=100)  # just changed
    s.record_file("c.py", "h", changed_at=10)  # changed long ago
    s.commit()

    by = _by_sym(heatmap(s, "A", now=100))
    assert by["B"].score > by["C"].score
    assert by["B"].score == pytest.approx(0.5)  # age 0 -> recency 1.0
    assert by["C"].score == pytest.approx(round(0.5 * 0.5 ** (90 / 30), 6))  # age 90, half-life 30

    # control: with no reference point recency is neutral -> the two tie (no effect).
    flat = _by_sym(heatmap(s, "A"))
    assert flat["B"].score == flat["C"].score == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Term 2 — fan-in penalty from the real edge graph (heatmap)
# --------------------------------------------------------------------------- #


def test_high_fan_in_node_is_down_weighted_via_real_edges():
    # B and C are identical hop-1 callers of A, but ten other symbols also call B (fan-in 10).
    edges = [("B", "A", "calls"), ("C", "A", "calls")]
    syms = {"A": "a.py", "B": "b.py", "C": "c.py"}
    for i in range(10):
        u = f"U{i}"
        syms[u] = f"u{i}.py"
        edges.append((u, "B", "calls"))
    s = _store(syms, edges)

    assert s.fan_in("B") == 10 and s.fan_in("C") == 0
    by = _by_sym(heatmap(s, "A"))
    assert by["C"].score > by["B"].score  # the ubiquitous node ranks below the focused one
    assert by["B"].score == pytest.approx(round(0.5 / (1.0 + P.w_fanin * math.log(10)), 6))
    assert by["C"].score == pytest.approx(0.5)  # fan-in 0 -> clamped 1 -> no penalty


# --------------------------------------------------------------------------- #
# Term 3 — co-change PMI from the coupling table (heatmap)
# --------------------------------------------------------------------------- #


def test_co_change_pmi_boosts_a_temporally_coupled_node():
    # B and C call A; a.py↔b.py co-change, and an unrelated x.py↔y.py pair lifts PMI above 0
    # (a pair that co-occurs MORE than the marginals predict -> positive PMI).
    s = _store({"A": "a.py", "B": "b.py", "C": "c.py"}, [("B", "A", "calls"), ("C", "A", "calls")])
    s.add_coupling("a.py", "b.py", "co_change", 5)
    s.add_coupling("x.py", "y.py", "co_change", 5)
    s.commit()

    pmi = s.cochange_pmi("a.py", "b.py")
    assert pmi == pytest.approx(math.log(2.0))  # log((5·10)/(5·5)) = log 2 > 0
    assert s.cochange_pmi("a.py", "c.py") == 0.0  # no coupling -> neutral

    by = _by_sym(heatmap(s, "A"))
    assert by["B"].score > by["C"].score
    assert by["B"].score == pytest.approx(round(0.5 + P.w_cc * math.log(2.0), 6))
    assert by["C"].score == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Term 4 — multi-probe agreement bonus from the expansion loop (expand)
# --------------------------------------------------------------------------- #


def _agreement_store() -> Store:
    # B and C are precise callers of A. a.py and b.py SHARE strings (shared_string coupling, NOT
    # co-change), so the coupling probe ALSO surfaces B -> B is corroborated by two probes while
    # C is found by one. shared_string (not co_change) keeps the PMI term out, isolating
    # agreement.
    s = _store({"A": "a.py", "B": "b.py", "C": "c.py"}, [("B", "A", "calls"), ("C", "A", "calls")])
    s.add_coupling("a.py", "b.py", "shared_string", 3)
    s.commit()
    return s


def test_two_probe_node_outranks_identical_one_probe_node():
    s = _agreement_store()
    by = _by_sym(expand(s, "A").heatmap)
    assert by["B"].score == pytest.approx(round(0.5 + P.agreement, 6))  # +0.1 corroboration
    assert by["C"].score == pytest.approx(0.5)  # single probe -> no bonus
    assert by["B"].score > by["C"].score

    # control: drop the second-probe coupling -> B and C tie (the bonus came from corroboration)
    s2 = _store(
        {"A": "a.py", "B": "b.py", "C": "c.py"}, [("B", "A", "calls"), ("C", "A", "calls")]
    )
    by2 = _by_sym(expand(s2, "A").heatmap)
    assert by2["B"].score == by2["C"].score == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# The guard — agreement NEVER boosts an unreconciled node (fabricated conflict)
# --------------------------------------------------------------------------- #


@dataclass
class _ConflictOverlay:
    """A live overlay that, for the dirty file, reports a symbol set NOT containing the node
    -> the reconcile tags it 'unreconciled' (SCIP says B, live LSP says ¬B)."""

    def refs_defs(self, file: str, working_bytes: bytes) -> Iterable[str]:
        return []  # the overlay sees nothing -> conflict with the store's claim


def test_agreement_bonus_is_stripped_from_an_unreconciled_node():
    s = _agreement_store()
    # make b.py dirty for B's source (scip): record a clean scip hash, then serve edited bytes.
    s.record_freshness("scip", "b.py", content_hash(b"clean b.py"))
    s.commit()

    res = expand(
        s,
        "A",
        working_files={"b.py": b"EDITED b.py since indexing"},
        overlay=_ConflictOverlay(),
    )
    by = _by_sym(res.heatmap)
    assert by["B"].freshness == "unreconciled"  # the fabricated SCIP↔overlay conflict
    # the corroboration bonus (B is a 2-probe node) is NOT applied — surfaced, not boosted.
    assert by["B"].score == pytest.approx(0.5)
    assert by["C"].score == pytest.approx(0.5)
    assert any("unreconciled" in w for w in res.warnings)


# --------------------------------------------------------------------------- #
# OD-3 — the score is a NAMED, swappable policy that heatmap AND expand consult
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _InvertingPolicy:
    """A trivial alternate policy that scores purely by hop (deeper = higher) — the OPPOSITE
    of Policy-D's hop decay — so a successful swap visibly flips the ranking."""

    name: str = "inverting"

    def score(self, sig) -> float:
        return float(sig.hop)

    def agreement_bonus(self, probes_found: int, conflicting: bool) -> float:
        return 0.0


def _chain() -> Store:
    # A <- B (hop1) <- C (hop2): default ranks B first (0.5 > 0.25); inverted ranks C first.
    return _store(
        {"A": "a.py", "B": "b.py", "C": "c.py"}, [("B", "A", "calls"), ("C", "B", "calls")]
    )


def test_heatmap_uses_the_injected_policy():
    s = _chain()
    assert heatmap(s, "A")[0].symbol == "B"  # default: closest hop first
    swapped = heatmap(s, "A", policy=_InvertingPolicy())
    assert swapped[0].symbol == "C"  # the alternate policy drove the ranking
    assert [e.score for e in swapped] == [2.0, 1.0]  # hop-valued scores, descending


def test_expand_uses_the_injected_policy():
    s = _chain()
    assert expand(s, "A").heatmap[0].symbol == "B"  # default
    assert expand(s, "A", policy=_InvertingPolicy()).heatmap[0].symbol == "C"  # swapped


# --------------------------------------------------------------------------- #
# Determinism — the trace replays the corroboration-boosted ranking (P4 holds)
# --------------------------------------------------------------------------- #


def test_replay_reconstructs_the_agreement_boosted_ranking():
    s = _agreement_store()
    res = expand(s, "A", capture_trace=True)
    replayed = replay(res.trace)
    # replay must re-derive the SAME scores/order, including B's +0.1 corroboration bonus —
    # if replay ignored the bonus, B would replay at 0.5 and this would fail.
    assert [(n.symbol, n.score) for n in replayed] == [
        (e.symbol, e.score) for e in res.heatmap
    ]
    assert _by_sym(replayed)["B"].score == pytest.approx(round(0.5 + P.agreement, 6))

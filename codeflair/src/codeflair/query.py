"""Codeflair query — deterministic blast radius + heatmap (CF-D11: no LLM).

Blast radius is transitive closure over the edge graph; relevance is a pure scoring
function of (edge-type, graph distance, provenance trust). Same store + same seed ->
byte-identical heatmap. The expensive model never walks; SQLite does.
"""

from __future__ import annotations

from dataclasses import dataclass

from codeflair.store import Store

# Relevance weights — deterministic, tunable, no model. "Impact" = who is affected
# when the seed changes = walk *incoming* edges (callers/referencers), transitively.

# Trust by provenance (CF-D14 precision ladder): a parsed SCIP/LSP edge outranks a
# syntactic tree-sitter guess, which outranks an inferred co-change link.
_PROVENANCE_TRUST = {"parsed": 1.0, "syntactic": 0.6, "inferred": 0.3}

# Edge-relation weight: a direct call/reference is stronger evidence of impact than a
# mere temporal co-change.
_REL_WEIGHT = {
    "calls": 1.0,
    "references": 0.9,
    "defines": 0.8,
    "co_change": 0.4,
}

_DEFAULT_REL_WEIGHT = 0.5
_HOP_DECAY = 0.5  # each hop away from the seed halves contribution


@dataclass(frozen=True)
class HeatmapEntry:
    symbol: str
    hop: int  # shortest distance from the seed (0 = the seed itself)
    score: float  # deterministic relevance, descending
    via: str  # the strongest (rel, source) that reached it, for explainability


def blast_radius(
    store: Store,
    seed: str,
    max_hops: int = 3,
    direction: str = "callers",
) -> dict[str, int]:
    """Transitive closure from ``seed`` over the edge graph, returning ``{symbol: min_hop}``.

    ``direction='callers'`` walks *incoming* edges (who depends on the seed — the impact
    set); ``'callees'`` walks *outgoing* edges (what the seed depends on).
    """
    if direction not in ("callers", "callees"):
        raise ValueError(f"direction must be 'callers' or 'callees', got {direction!r}")
    if max_hops < 0:
        raise ValueError("max_hops must be >= 0")
    # callers: step from a discovered node N along edges where dst=N, taking src (the
    # caller). callees: step where src=N, taking dst (the callee).
    sql = f"""
        WITH RECURSIVE blast(sym, hop) AS (
            SELECT ?, 0
            UNION
            SELECT {"e.src" if direction == "callers" else "e.dst"}, b.hop + 1
            FROM edges e
            JOIN blast b ON {"e.dst" if direction == "callers" else "e.src"} = b.sym
            WHERE b.hop < ?
        )
        SELECT sym, MIN(hop) AS hop FROM blast GROUP BY sym
    """
    rows = store.con.execute(sql, (seed, max_hops)).fetchall()
    return {sym: hop for sym, hop in rows}


def heatmap(
    store: Store,
    seed: str,
    k: int = 20,
    max_hops: int = 3,
    direction: str = "callers",
) -> list[HeatmapEntry]:
    """Rank the blast radius into a top-``k`` heatmap by deterministic relevance.

    Score of a node = best over the edges that reach it of
    ``rel_weight * provenance_trust * hop_decay**hop``. The seed is excluded (it is
    not its own impact). Ties break by symbol string so the order is total + stable.
    """
    radius = blast_radius(store, seed, max_hops=max_hops, direction=direction)
    radius.pop(seed, None)
    if not radius:
        return []

    # For each reached node, find the strongest single edge that lands on it (from a
    # node also in the radius), and combine with hop decay.
    entries: list[HeatmapEntry] = []
    # A reached node sits on the FAR side of its edge from the seed: walking callers we
    # arrived at a node via an edge it emits (src=sym -> something closer); walking
    # callees, via an edge that lands on it (dst=sym).
    join_col = "src" if direction == "callers" else "dst"
    for sym, hop in radius.items():
        best_score = -1.0
        best_via = ""
        cur = store.con.execute(
            f"SELECT rel, source, provenance FROM edges WHERE {join_col}=?", (sym,)
        )
        for rel, source, provenance in cur.fetchall():
            rel_w = _REL_WEIGHT.get(rel, _DEFAULT_REL_WEIGHT)
            trust = _PROVENANCE_TRUST.get(provenance, 0.3)
            s = rel_w * trust * (_HOP_DECAY**hop)
            if s > best_score:
                best_score = s
                best_via = f"{rel}/{source}"
        if best_score < 0:
            # reached only as a seed-side endpoint with no inbound edge of its own
            best_score = _DEFAULT_REL_WEIGHT * (_HOP_DECAY**hop)
            best_via = "transitive"
        entries.append(HeatmapEntry(symbol=sym, hop=hop, score=round(best_score, 6), via=best_via))

    entries.sort(key=lambda e: (-e.score, e.symbol))
    return entries[:k]

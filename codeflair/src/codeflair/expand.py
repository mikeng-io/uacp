"""Codeflair expansion loop + gaps (CF-D3 / CF-D6) — the relation-finder.

Fuses the two signal classes into one ranked heatmap:
- **precise** edge-walk (SCIP/LSP/tree-sitter) via the recursive-CTE blast radius, and
- **inferred** file-level couplings (co-change / shared-string) projected to symbols,
  expanded only from the top-``beam`` precise nodes so cost stays bounded on huge graphs.

Precise always outranks inferred at equal distance (the CF-D14 ladder). Deterministic:
no LLM, stable ordering. Gaps (untested impacted symbols) are a first-class, best-effort
output scored separately from the heatmap (CF-D6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from codeflair.query import HeatmapEntry, heatmap
from codeflair.store import Store

# Inferred couplings are weak by construction — floor them well below any parsed edge.
_INFERRED_TRUST = 0.3
_COUPLING_KIND_WEIGHT = {"co_change": 0.4, "shared_string": 0.5}
_HOP_DECAY = 0.5

_TEST_FILE_RE = re.compile(
    r"(_test\.go$|_test\.py$|test_.*\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|(^|/)tests?/)"
)


@dataclass(frozen=True)
class Gap:
    symbol: str
    file: str
    reason: str  # e.g. "no test references this impacted symbol"


@dataclass(frozen=True)
class ExpandResult:
    heatmap: list[HeatmapEntry]
    gaps: list[Gap]
    n_precise: int  # symbols reached by precise edge-walk
    n_inferred: int  # symbols added only by coupling projection


def is_test_file(path: str) -> bool:
    return bool(_TEST_FILE_RE.search(path))


def expand(
    store: Store,
    seed: str,
    *,
    k: int = 20,
    max_hops: int = 3,
    beam: int = 50,
    direction: str = "callers",
    include_coupling: bool = True,
) -> ExpandResult:
    """Grow the relation subgraph from ``seed`` and rank it into a top-``k`` heatmap + gaps."""
    # 1. precise closure, fully scored (heatmap with no top-k cut)
    precise = heatmap(store, seed, k=2_000_000_000, max_hops=max_hops, direction=direction)
    entries: dict[str, HeatmapEntry] = {e.symbol: e for e in precise}
    n_precise = len(entries)

    # 2. inferred coupling projection from the seed + top-beam precise nodes
    n_inferred = 0
    if include_coupling:
        bases: list[tuple[str, int]] = [(seed, 0)]
        bases += [(e.symbol, e.hop) for e in precise[:beam]]
        for base_sym, base_hop in bases:
            sym_row = store.symbol(base_sym)
            if sym_row is None or not sym_row.file:
                continue
            for other_file, kind, _weight in store.coupled_files(sym_row.file):
                hop = base_hop + 1
                score = round(
                    _INFERRED_TRUST * _COUPLING_KIND_WEIGHT.get(kind, 0.3) * (_HOP_DECAY**hop), 6
                )
                for csym in store.symbols_in_file(other_file):
                    if csym == seed or csym in entries:
                        continue  # precise evidence always wins
                    entries[csym] = HeatmapEntry(
                        symbol=csym, hop=hop, score=score, via=f"{kind}/coupling"
                    )
                    n_inferred += 1

    ranked = sorted(entries.values(), key=lambda e: (-e.score, e.symbol))[:k]
    gaps = find_test_gaps(store, ranked)
    return ExpandResult(heatmap=ranked, gaps=gaps, n_precise=n_precise, n_inferred=n_inferred)


def find_test_gaps(store: Store, entries: list[HeatmapEntry]) -> list[Gap]:
    """Impacted symbols (in non-test files) that NO test file references — the actionable
    'changing this is unguarded' signal. Best-effort, deterministic, ordered by entry rank."""
    gaps: list[Gap] = []
    for e in entries:
        row = store.symbol(e.symbol)
        if row is None or not row.file or is_test_file(row.file):
            continue
        # any caller (edge dst=sym) whose source symbol lives in a test file?
        callers = store.con.execute("SELECT src FROM edges WHERE dst=?", (e.symbol,)).fetchall()
        tested = False
        for (src,) in callers:
            src_row = store.symbol(src)
            if src_row is not None and is_test_file(src_row.file):
                tested = True
                break
        if not tested:
            gaps.append(
                Gap(
                    symbol=e.symbol, file=row.file, reason="no test references this impacted symbol"
                )
            )
    return gaps

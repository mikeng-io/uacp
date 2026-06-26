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

from codeflair.probes import ProbeContext, ProbeParams, ProbeRegistry, default_registry
from codeflair.query import HeatmapEntry
from codeflair.store import Store

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
    registry: ProbeRegistry | None = None,
) -> ExpandResult:
    """Grow the relation subgraph from ``seed`` and rank it into a top-``k`` heatmap + gaps.

    The probe sequence is NOT hardcoded: the loop consults ``registry`` (defaulting to the
    core probe set — precise edge-walk then coupling projection). Probes run in registration
    order; the FIRST probe to claim a symbol wins, so precise evidence outranks inferred
    couplings (and any later-registered probe). New sources (LSP, contracts, the UACP
    cross-plane join) plug in by registering a probe — no change to this function.
    """
    if registry is None:
        registry = default_registry(include_coupling=include_coupling)
    params = ProbeParams(k=k, max_hops=max_hops, beam=beam, direction=direction)
    ctx = ProbeContext(store=store, seed=seed, params=params)

    counts = {"precise": 0, "inferred": 0}
    for probe in registry.probes:
        for entry in probe.expand(ctx):
            if entry.symbol == seed or entry.symbol in ctx.entries:
                continue  # first claim wins — precise evidence (earlier probe) is never displaced
            ctx.entries[entry.symbol] = entry
            counts[probe.kind] = counts.get(probe.kind, 0) + 1

    ranked = sorted(ctx.entries.values(), key=lambda e: (-e.score, e.symbol))[:k]
    gaps = find_test_gaps(store, ranked)
    return ExpandResult(
        heatmap=ranked,
        gaps=gaps,
        n_precise=counts.get("precise", 0),
        n_inferred=counts.get("inferred", 0),
    )


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

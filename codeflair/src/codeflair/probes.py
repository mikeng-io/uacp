"""Codeflair probe registry — the pluggable expansion seam (CF-D9, 02-probes / 09-abstraction).

The expansion loop (``expand.py``) does NOT hardcode its probe sequence; it consults a
:class:`ProbeRegistry`. A **probe** takes the accumulated frontier and yields candidate
:class:`HeatmapEntry` nodes; the loop merges them under one precedence rule (first claim on a
symbol wins, so probes registered earlier — precise edges — outrank later ones — inferred
couplings). This is the seam the UACP adapter and future probes (LSP, contract-parser)
register into WITHOUT editing the loop: ``registry.register(MyProbe())``.

Deterministic, no LLM. The two built-in probes reproduce the prior hardcoded behaviour
exactly: the precise edge-walk (SCIP/tree-sitter blast radius) then the inferred coupling
projection (co-change / shared-string) from the top-``beam`` precise nodes.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from codeflair.policy import ScorePolicy
from codeflair.query import HeatmapEntry, heatmap
from codeflair.store import Store


@dataclass(frozen=True)
class ProbeParams:
    """The query knobs every probe sees (the loop's call parameters)."""

    k: int = 20
    max_hops: int = 3
    beam: int = 50
    direction: str = "callers"


@dataclass
class ProbeContext:
    """What a probe is handed each run: the store, the seed, the params, and the
    insertion-ordered ``entries`` accumulated by probes that already ran (so a later probe
    can build on earlier results — e.g. coupling springboards off the precise frontier)."""

    store: Store
    seed: str
    params: ProbeParams
    entries: dict[str, HeatmapEntry] = field(default_factory=dict)
    # P6: the swappable score policy + the injected recency reference (OD-3). ``None`` ->
    # the scoring helpers fall back to the package default policy / neutral recency.
    policy: ScorePolicy | None = None
    now: int | None = None

    def bases(self) -> list[tuple[str, int]]:
        """Springboard nodes for projection probes: the seed plus the top-``beam`` already
        found nodes (in accumulation order = heatmap rank for the precise probe)."""
        springboards = list(self.entries.values())[: self.params.beam]
        return [(self.seed, 0)] + [(e.symbol, e.hop) for e in springboards]


@runtime_checkable
class Probe(Protocol):
    """A deterministic read against one source. ``kind`` buckets its contribution for the
    precise/inferred counts (``"precise"`` | ``"inferred"``)."""

    name: str
    kind: str

    def expand(self, ctx: ProbeContext) -> Iterable[HeatmapEntry]: ...


class PreciseEdgeWalkProbe:
    """The recursive-CTE blast radius over parsed/syntactic edges (SCIP + tree-sitter)."""

    name = "precise"
    kind = "precise"

    def expand(self, ctx: ProbeContext) -> Iterable[HeatmapEntry]:
        # No top-k cut here — the loop ranks + truncates the fused result once.
        return heatmap(
            ctx.store,
            ctx.seed,
            k=2_000_000_000,
            max_hops=ctx.params.max_hops,
            direction=ctx.params.direction,
            policy=ctx.policy,
            now=ctx.now,
        )


class CouplingProjectionProbe:
    """Inferred file-level couplings (co-change / shared-string) projected to symbols from
    the seed + top-``beam`` frontier nodes. Weak by construction — floored below any parsed
    edge — and bounded by the beam so cost stays sane on huge graphs."""

    name = "coupling"
    kind = "inferred"

    # Inferred couplings are weak by construction — floor them well below any parsed edge.
    _INFERRED_TRUST = 0.3
    _KIND_WEIGHT = {"co_change": 0.4, "shared_string": 0.5}
    _HOP_DECAY = 0.5

    def expand(self, ctx: ProbeContext) -> Iterator[HeatmapEntry]:
        for base_sym, base_hop in ctx.bases():
            sym_row = ctx.store.symbol(base_sym)
            if sym_row is None or not sym_row.file:
                continue
            for other_file, kind, _weight in ctx.store.coupled_files(sym_row.file):
                hop = base_hop + 1
                kind_weight = self._KIND_WEIGHT.get(kind, 0.3)
                score = round(self._INFERRED_TRUST * kind_weight * (self._HOP_DECAY**hop), 6)
                for csym in ctx.store.symbols_in_file(other_file):
                    yield HeatmapEntry(symbol=csym, hop=hop, score=score, via=f"{kind}/coupling")


@dataclass
class ProbeRegistry:
    """An ordered set of probes the expansion loop consults. Registration order IS
    precedence (earlier probes claim a symbol first)."""

    probes: list[Probe] = field(default_factory=list)

    def register(self, probe: Probe) -> None:
        self.probes.append(probe)


def default_registry(*, include_coupling: bool = True) -> ProbeRegistry:
    """The core probe set: precise edge-walk, then (optionally) the coupling projection."""
    reg = ProbeRegistry()
    reg.register(PreciseEdgeWalkProbe())
    if include_coupling:
        reg.register(CouplingProjectionProbe())
    return reg

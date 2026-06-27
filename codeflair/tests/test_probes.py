"""Probe registry: the pluggable expansion seam (P0, gap #4 / CF-D9)."""

from codeflair import Edge, Store, Symbol, expand
from codeflair.probes import (
    CouplingProjectionProbe,
    PreciseEdgeWalkProbe,
    ProbeContext,
    ProbeParams,
    ProbeRegistry,
    default_registry,
)
from codeflair.query import HeatmapEntry


def _store() -> Store:
    s = Store()
    s.add_symbol(Symbol(symbol="A", file="a.go", name="A"))
    s.add_symbol(Symbol(symbol="B", file="b.go", name="B"))
    s.add_edge(Edge("B", "A", "calls", "scip"))
    s.commit()
    return s


def test_default_registry_is_precise_then_coupling():
    """The loop's probe sequence lives in the registry, not hardcoded in expand.py."""
    assert [p.name for p in default_registry().probes] == ["precise", "coupling"]
    assert [p.name for p in default_registry(include_coupling=False).probes] == ["precise"]
    # built-in probes are bucketed for the precise/inferred counts
    assert PreciseEdgeWalkProbe().kind == "precise"
    assert CouplingProjectionProbe().kind == "inferred"


def test_registry_is_consulted_only_what_is_registered_runs():
    """An EMPTY registry yields an empty heatmap — proving the loop walks the registry and
    nothing else (the precise edge-walk only runs because a probe is registered)."""
    s = _store()
    res = expand(s, "A", registry=ProbeRegistry())
    assert res.heatmap == []
    assert res.n_precise == 0 and res.n_inferred == 0


def test_custom_probe_adds_to_heatmap_without_editing_expand():
    """P0 ACCEPTANCE (gap #4): a NEW probe registers into the loop and its candidate appears
    in the fused heatmap — with NO change to expand.py. The probe also sees what earlier
    probes found, proving the loop threads the accumulating frontier through the registry."""
    s = _store()
    sentinel = HeatmapEntry(symbol="GHOST", hop=2, score=0.123456, via="dummy/test")
    seen: dict[str, bool] = {}

    class DummyProbe:
        name = "dummy"
        kind = "inferred"

        def expand(self, ctx: ProbeContext):
            seen["precise_ran_first"] = "B" in ctx.entries  # precise probe ran before us
            return [sentinel]

    reg = default_registry()
    reg.register(DummyProbe())
    res = expand(s, "A", registry=reg)

    syms = [e.symbol for e in res.heatmap]
    assert "B" in syms  # the built-in precise probe still works through the registry
    assert "GHOST" in syms  # the NEW probe's candidate landed in the heatmap
    ghost = next(e for e in res.heatmap if e.symbol == "GHOST")
    assert ghost.score == 0.123456 and ghost.via == "dummy/test"
    assert seen["precise_ran_first"] is True


def test_custom_probe_does_not_override_precise_evidence():
    """First claim wins: a later probe cannot displace a symbol an earlier (precise) probe
    already found — the precise entry for B is kept, the dummy's B candidate is dropped."""
    s = _store()

    class ShadowProbe:
        name = "shadow"
        kind = "inferred"

        def expand(self, ctx: ProbeContext):
            # try to overwrite B (precise) with a bogus high score — must be ignored
            return [HeatmapEntry(symbol="B", hop=9, score=99.0, via="shadow/bogus")]

    reg = default_registry()
    reg.register(ShadowProbe())
    res = expand(s, "A", registry=reg)
    b = next(e for e in res.heatmap if e.symbol == "B")
    assert b.via == "calls/scip" and b.hop == 1  # precise evidence preserved


def test_probe_context_bases_seed_plus_frontier():
    """The coupling springboards = seed + accumulated frontier (bounded by beam)."""
    s = _store()
    ctx = ProbeContext(store=s, seed="A", params=ProbeParams(beam=1))
    ctx.entries["B"] = HeatmapEntry(symbol="B", hop=1, score=0.5, via="calls/scip")
    assert ctx.bases() == [("A", 0), ("B", 1)]

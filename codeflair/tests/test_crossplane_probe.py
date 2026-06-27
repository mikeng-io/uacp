"""P7 #11 — the cross-plane READ-ONLY spanning join probe.

The heatmap spans both planes when (and only when) the cross-plane adapter probe is
registered: relation-plane manifest nodes the blast radius touches appear ALONGSIDE the
code-plane symbols (04-outputs / CF-D9). The join is read-only — it performs no governed
write into UACP state (OD-2: the write-back is deferred).
"""

from codeflair import Edge, Store, Symbol, expand
from codeflair.crossplane import CrossPlaneAdapter, CrossPlaneProbe, ManifestRef
from codeflair.probes import default_registry


def _build_index(path: str) -> None:
    """Build a tiny code graph + ``code_anchor`` anchors and persist to ``path``. This is the
    index BUILD (writable); the cross-plane QUERY later runs read-only against it. The anchors
    stand in for the deferred governed write-back (OD-2) — here just seeded for the test."""
    with Store(path) as s:
        s.add_symbol(Symbol(symbol="A", file="a.py", name="A", kind="func"))
        s.add_symbol(Symbol(symbol="B", file="b.py", name="B", kind="func"))
        s.add_edge(Edge("B", "A", "calls", "scip"))  # B calls A => A's caller is B (hop 1)
        s.commit()
        adapter = CrossPlaneAdapter(s)
        adapter.anchor(ManifestRef("PROP-1", "proposal", "A", rel="governs"))  # governs the seed
        adapter.anchor(ManifestRef("PLAN-9", "plan", "B", rel="realizes"))  # anchored to a caller
        s.set_watermark("c0ffee", "c0ffee")


def test_heatmap_spans_planes_when_crossplane_probe_registered(tmp_path):
    """ACCEPTANCE: with the cross-plane probe registered the heatmap CONTAINS relation-plane
    nodes (manifest ids the code touches) alongside code-plane nodes."""
    db = str(tmp_path / "index.db")
    _build_index(db)
    ro = Store(db, read_only=True)
    try:
        adapter = CrossPlaneAdapter(ro)
        reg = default_registry()
        reg.register(CrossPlaneProbe(adapter))  # span both planes
        res = expand(ro, "A", registry=reg)
    finally:
        ro.close()

    syms = [e.symbol for e in res.heatmap]
    assert "B" in syms  # code-plane node: A's caller
    assert "PROP-1" in syms  # relation-plane: the manifest governing the seed A
    assert "PLAN-9" in syms  # relation-plane: the manifest anchored to B (in the blast radius)
    prop = next(e for e in res.heatmap if e.symbol == "PROP-1")
    assert prop.via == "governs/manifest"  # carries the relation-plane marker
    plan = next(e for e in res.heatmap if e.symbol == "PLAN-9")
    assert plan.via == "realizes/manifest"
    # the manifest nodes do not inflate the precise/inferred CODE counts (distinct bucket)
    assert res.n_precise == 1 and res.n_inferred == 0


def test_standalone_heatmap_is_code_plane_only(tmp_path):
    """CF-D9 non-vacuity: WITHOUT the cross-plane probe the heatmap is code-plane only — so
    the spanning above is caused by the probe, not present regardless."""
    db = str(tmp_path / "index.db")
    _build_index(db)
    ro = Store(db, read_only=True)
    try:
        res = expand(ro, "A", registry=default_registry())  # no cross-plane probe
    finally:
        ro.close()
    syms = [e.symbol for e in res.heatmap]
    assert "B" in syms
    assert "PROP-1" not in syms and "PLAN-9" not in syms


def test_crossplane_join_performs_no_write(tmp_path):
    """ACCEPTANCE: the read-only join mutates nothing. It opens the adapter against a READ-ONLY
    index (a write would raise ``OperationalError`` on that connection) and the ``code_anchor``
    row count is identical before and after."""
    db = str(tmp_path / "index.db")
    _build_index(db)
    with Store(db) as s:
        before = s.con.execute("SELECT COUNT(*) FROM code_anchor").fetchone()[0]

    ro = Store(db, read_only=True)
    try:
        adapter = CrossPlaneAdapter(ro)
        reg = default_registry()
        reg.register(CrossPlaneProbe(adapter))
        res = expand(ro, "A", registry=reg)  # MUST NOT raise — no write is attempted
    finally:
        ro.close()
    assert any(e.symbol == "PROP-1" for e in res.heatmap)  # the join actually ran

    with Store(db) as s:
        after = s.con.execute("SELECT COUNT(*) FROM code_anchor").fetchone()[0]
    assert after == before  # zero mutation


def test_crossplane_probe_tolerates_never_anchored_index(tmp_path):
    """A read-only index with NO ``code_anchor`` table (never anchored) yields just the
    code plane — the probe's ``governs`` reads tolerate the absent table, no error, no write."""
    db = str(tmp_path / "bare.db")
    with Store(db) as s:
        s.add_symbol(Symbol(symbol="A", file="a.py", name="A", kind="func"))
        s.add_symbol(Symbol(symbol="B", file="b.py", name="B", kind="func"))
        s.add_edge(Edge("B", "A", "calls", "scip"))
        s.set_watermark("c0ffee", "c0ffee")
        s.commit()
    ro = Store(db, read_only=True)
    try:
        reg = default_registry()
        reg.register(CrossPlaneProbe(CrossPlaneAdapter(ro)))
        res = expand(ro, "A", registry=reg)
    finally:
        ro.close()
    assert [e.symbol for e in res.heatmap] == ["B"]  # code plane only; no manifest nodes

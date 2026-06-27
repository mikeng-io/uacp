"""Cross-plane adapter: code_anchor resolution, joins, and gaps (UACP-agnostic)."""

import pytest

from codeflair import Store, Symbol
from codeflair.crossplane import CrossPlaneAdapter, ManifestRef


def _store() -> Store:
    s = Store()
    # two repo symbols + one external (no file) that must never be anchored/orphaned
    s.add_symbol(
        Symbol(
            symbol="scip go `m`/CancelOrderUseCase#Execute().",
            file="usecases/cancel.go",
            name="Execute",
            kind="method",
        )
    )
    s.add_symbol(
        Symbol(
            symbol="scip go `m`/PlaceOrderUseCase#Execute().",
            file="usecases/place.go",
            name="Execute",
            kind="method",
        )
    )
    s.add_symbol(
        Symbol(
            symbol="scip go `m`/NewCancelOrderUseCase().",
            file="usecases/cancel.go",
            name="NewCancelOrderUseCase",
            kind="func",
        )
    )
    s.add_symbol(Symbol(symbol="scip go `ext`/Println().", file="", name="Println", kind="func"))
    s.commit()
    return s


def test_resolve_exact_name():
    a = CrossPlaneAdapter(_store())
    got = a.resolve("NewCancelOrderUseCase")
    assert got == ["scip go `m`/NewCancelOrderUseCase()."]


def test_resolve_ambiguous_name_returns_all():
    a = CrossPlaneAdapter(_store())
    got = a.resolve("Execute")  # two methods named Execute
    assert len(got) == 2


def test_resolve_file_scoped_disambiguates():
    a = CrossPlaneAdapter(_store())
    got = a.resolve("cancel.go:Execute")
    assert got == ["scip go `m`/CancelOrderUseCase#Execute()."]


def test_resolve_never_matches_external_symbol_without_file():
    a = CrossPlaneAdapter(_store())
    assert a.resolve("Println") == []  # external (file == '') is not anchorable


def test_anchor_status_anchored_ambiguous_unresolved():
    a = CrossPlaneAdapter(_store())
    assert a.anchor(ManifestRef("P-1", "proposal", "NewCancelOrderUseCase")).status == "anchored"
    assert a.anchor(ManifestRef("P-2", "proposal", "Execute")).status == "ambiguous"
    assert a.anchor(ManifestRef("P-3", "proposal", "Nonexistent")).status == "unresolved"


def test_anchor_rejects_unknown_rel():
    a = CrossPlaneAdapter(_store())
    with pytest.raises(ValueError, match="unknown rel"):
        a.anchor(ManifestRef("P-1", "proposal", "Execute", rel="vibes"))


def test_governs_and_realizes_roundtrip():
    a = CrossPlaneAdapter(_store())
    a.anchor(ManifestRef("PROP-7", "proposal", "cancel.go:Execute", rel="realizes"))
    sym = "scip go `m`/CancelOrderUseCase#Execute()."
    assert a.governs(sym) == [("PROP-7", "proposal", "realizes")]
    assert a.realizes("PROP-7") == [sym]


def test_orphan_code_lists_unanchored_repo_symbols_only():
    s = _store()
    a = CrossPlaneAdapter(s)
    a.anchor(ManifestRef("PROP-7", "proposal", "cancel.go:Execute"))
    orphans = a.orphan_code()
    # the anchored Cancel Execute is governed; the other two repo symbols are orphans;
    # the external Println (no file) is never an orphan.
    assert "scip go `m`/CancelOrderUseCase#Execute()." not in orphans
    assert "scip go `m`/PlaceOrderUseCase#Execute()." in orphans
    assert "scip go `m`/NewCancelOrderUseCase()." in orphans
    assert "scip go `ext`/Println()." not in orphans


def test_orphan_code_kind_filter():
    s = _store()
    a = CrossPlaneAdapter(s)
    methods = a.orphan_code(kind="method")
    assert all(s.symbol(sym).kind == "method" for sym in methods)
    assert "scip go `m`/NewCancelOrderUseCase()." not in methods  # it's a func, filtered out


def test_unrealized_manifests():
    a = CrossPlaneAdapter(_store())
    a.anchor(ManifestRef("PROP-7", "proposal", "NewCancelOrderUseCase"))
    unrealized = a.unrealized_manifests(["PROP-7", "PROP-8", "PLAN-3"])
    assert unrealized == ["PROP-8", "PLAN-3"]  # PROP-7 has an anchor; the rest don't


def _anchor_table_present(store) -> bool:
    return (
        store.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='code_anchor'"
        ).fetchone()
        is not None
    )


def test_construct_does_not_create_table_until_write():
    """D4: constructing the adapter must NOT mutate the store — the code_anchor table is
    created lazily by the write path, not by __init__."""
    s = _store()
    a = CrossPlaneAdapter(s)
    assert not _anchor_table_present(s)  # construction created nothing
    a.anchor(ManifestRef("P-1", "proposal", "NewCancelOrderUseCase"))  # the write path creates it
    assert _anchor_table_present(s)


def test_construct_on_readonly_index_performs_no_mutation(tmp_path):
    """D4: a UACP consumer must be able to open the adapter against a READ-ONLY index.
    Construction must perform no write (a CREATE TABLE would fail on a ro db), and the
    read queries must answer against a never-anchored index without erroring."""
    db = tmp_path / "index.db"
    with Store(str(db)) as s:  # writable: build the core code graph only (NO anchors)
        s.add_symbol(Symbol(symbol="scip `m`/Foo#", file="foo.go", name="Foo", kind="func"))
        s.commit()

    ro = Store(str(db), read_only=True)
    try:
        a = CrossPlaneAdapter(ro)  # MUST NOT mutate / raise on the ro db
        # reads against the never-anchored index: Foo is an orphan; no governance anchors
        assert a.orphan_code() == ["scip `m`/Foo#"]
        assert a.governs("scip `m`/Foo#") == []
        assert a.realizes("P-1") == []
        assert a.unrealized_manifests(["P-1", "P-2"]) == ["P-1", "P-2"]
    finally:
        ro.close()


def test_anchor_table_does_not_touch_core_store():
    # the adapter owns code_anchor; the core symbol/edge counts are untouched by anchoring
    s = _store()
    a = CrossPlaneAdapter(s)
    before = s.count_symbols()
    a.anchor(ManifestRef("PROP-7", "proposal", "Execute"))
    assert s.count_symbols() == before  # anchoring adds no symbols/edges to the core graph
    assert s.count_edges() == 0

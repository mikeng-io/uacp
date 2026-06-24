"""Inferred manifest->code anchoring: token extraction + end-to-end through the adapter."""

from codeflair import Store, Symbol
from codeflair.crossplane import CrossPlaneAdapter
from codeflair.manifest_anchor import candidate_tokens, refs_from_manifest_nodes


def test_candidate_tokens_keeps_codeish_drops_prose():
    toks = candidate_tokens("Refactor the CancelOrderUseCase.Execute and cancel_order flow now")
    assert "CancelOrderUseCase.Execute" in toks  # dotted member
    assert "cancel_order" in toks  # snake_case
    assert "Refactor" in toks  # leading capital (real word but code-shaped; resolver filters)
    assert "the" not in toks  # prose, too short + lowercase
    assert "flow" not in toks  # lowercase prose
    assert "now" not in toks


def test_candidate_tokens_dedupes_case_insensitively():
    assert candidate_tokens("Execute Execute EXECUTE") == ["Execute"]


def test_refs_one_per_node_per_token():
    nodes = [
        {"id": "WU-1", "kind": "work_unit", "intent": "update CancelOrderUseCase"},
        {"id": "SI-1", "kind": "scope_item", "statement": "the PlaceOrder path"},
    ]
    refs = refs_from_manifest_nodes(nodes)
    by_id = {r.manifest_id for r in refs}
    assert by_id == {"WU-1", "SI-1"}
    assert any(r.code_ref == "CancelOrderUseCase" for r in refs)
    assert any(r.code_ref == "PlaceOrder" for r in refs)


def test_refs_skip_nodes_without_id():
    assert refs_from_manifest_nodes([{"kind": "work_unit", "intent": "Execute"}]) == []


def test_end_to_end_inferred_anchor_resolves_against_code_graph():
    # the code graph has CancelOrderUseCase#Execute; a work_unit mentioning it should anchor,
    # while a mention of a non-existent symbol resolves to nothing (dropped).
    s = Store()
    s.add_symbol(
        Symbol(
            symbol="scip go `m`/CancelOrderUseCase#Execute().",
            file="cancel.go",
            name="Execute",
            kind="method",
        )
    )
    s.commit()
    adapter = CrossPlaneAdapter(s)
    nodes = [
        {"id": "WU-1", "kind": "work_unit", "intent": "harden cancel.go Execute path"},
        {"id": "WU-2", "kind": "work_unit", "intent": "touch NonexistentThing"},
    ]
    results = adapter.ingest(refs_from_manifest_nodes(nodes))
    anchored = [r for r in results if r.status == "anchored"]
    assert any(r.ref.manifest_id == "WU-1" for r in anchored)  # WU-1 anchored to Execute
    assert adapter.realizes("WU-1") == ["scip go `m`/CancelOrderUseCase#Execute()."]
    assert adapter.realizes("WU-2") == []  # nothing real to anchor -> no edge
    # and the cross-plane gap is reported: WU-2 is unrealized
    assert "WU-2" in adapter.unrealized_manifests(["WU-1", "WU-2"])

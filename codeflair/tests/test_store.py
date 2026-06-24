"""Store: schema, source-tagging, stable identity, source-scoped re-ingest."""
import pytest

from codeflair import Store, Symbol, Edge


def test_symbol_identity_is_the_scip_descriptor_not_a_row_id():
    """The C-spike lesson made executable: identity is the SCIP descriptor string, so
    it is stable across reindex. There is no autoincrement row id to churn."""
    s = Store()
    desc = "scip-go gomod github.com/jackc/pgx/v5 v5.10.0 `.../pgxpool`/Pool#Conn()."
    s.add_symbol(Symbol(symbol=desc, lang="go", file="pgxpool/pool.go", name="Conn", kind="method"))
    got = s.symbol(desc)
    assert got is not None
    assert got.symbol == desc          # the descriptor IS the key
    assert got.name == "Conn"


def test_reinsert_same_descriptor_is_idempotent_keeps_one_row():
    """Re-ingesting the same symbol (e.g. a rebuild) updates in place — the identity is
    stable, the count does not grow. Contrast: an autoincrement id would mint a new row."""
    s = Store()
    desc = "scip-go gomod m v1 `p`/Foo#"
    s.add_symbol(Symbol(symbol=desc, file="a.go", line=1))
    s.add_symbol(Symbol(symbol=desc, file="a.go", line=2))  # moved a line on rebuild
    assert s.count_symbols() == 1
    assert s.symbol(desc).line == 2     # updated in place under the SAME identity


def test_add_edge_rejects_unknown_source():
    s = Store()
    with pytest.raises(ValueError, match="unknown edge source"):
        s.add_edge(Edge(src="a", dst="b", rel="calls", source="vibes"))


def test_add_edge_rejects_unknown_provenance():
    s = Store()
    with pytest.raises(ValueError, match="unknown provenance"):
        s.add_edge(Edge(src="a", dst="b", rel="calls", source="scip", provenance="guessed"))


def test_edges_are_tagged_and_counted_by_source():
    """Fused store, edges partitioned by source for independent freshness/counting."""
    s = Store()
    s.add_edge(Edge("a", "b", "calls", "scip"))
    s.add_edge(Edge("a", "b", "co_change", "co_change", provenance="inferred"))
    s.add_edge(Edge("c", "b", "references", "tree_sitter", provenance="syntactic"))
    assert s.count_edges() == 3
    assert s.count_edges(source="scip") == 1
    assert s.count_edges(source="co_change") == 1
    assert s.count_edges(source="tree_sitter") == 1


def test_replace_source_file_is_source_scoped():
    """Re-ingesting one file's SCIP edges must not delete another source's edges on the
    same file (per-source freshness clocks)."""
    s = Store()
    s.add_symbol(Symbol(symbol="A", file="a.go"))
    s.add_symbol(Symbol(symbol="B", file="a.go"))
    s.add_edge(Edge("A", "B", "calls", "scip"))
    s.add_edge(Edge("A", "B", "co_change", "co_change", provenance="inferred"))
    # re-ingest a.go's SCIP edges (now A no longer calls B)
    s.replace_source_file("scip", "a.go", edges=[])
    assert s.count_edges(source="scip") == 0          # scip edge replaced away
    assert s.count_edges(source="co_change") == 1     # co_change edge untouched


def test_replace_source_file_rejects_mismatched_edge_source():
    s = Store()
    s.add_symbol(Symbol(symbol="A", file="a.go"))
    with pytest.raises(ValueError, match="!= replace source"):
        s.replace_source_file("scip", "a.go", edges=[Edge("A", "B", "calls", "lsp")])

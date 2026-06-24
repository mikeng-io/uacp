"""Tree-sitter floor: syntactic symbols + enclosing-def call edges, multi-language.

Gated on the optional tree-sitter dep (install: pip install 'codeflair[treesitter]').
Run with the dev venv: .venv/bin/python -m pytest."""

import pytest

from codeflair import Store, blast_radius, heatmap

pytest.importorskip("tree_sitter_languages")
from codeflair.treesitter_ingest import ingest_tree_sitter, synth_symbol  # noqa: E402

PY = b"""
def helper():
    return 1

def answer():
    return helper() + 1

def caller():
    return answer()
"""


def test_python_defs_become_symbols():
    s = Store()
    stats = ingest_tree_sitter(s, {"m.py": ("python", PY)})
    names = {s.symbol(sym).name for sym in s.symbols_in_file("m.py")}
    assert {"helper", "answer", "caller"} <= names
    assert stats.symbols >= 3


def test_python_call_edges_resolve_to_enclosing_def():
    # answer() calls helper(); caller() calls answer(). Blast radius of helper = answer, caller.
    s = Store()
    ingest_tree_sitter(s, {"m.py": ("python", PY)})
    helper = next(sym for sym in s.symbols_in_file("m.py") if s.symbol(sym).name == "helper")
    radius = blast_radius(s, helper, direction="callers")
    reached = {s.symbol(sym).name for sym in radius}
    assert "answer" in reached  # answer -> helper (direct)
    assert "caller" in reached  # caller -> answer -> helper (transitive)


def test_edges_are_tagged_syntactic_tree_sitter():
    s = Store()
    ingest_tree_sitter(s, {"m.py": ("python", PY)})
    assert s.count_edges(source="tree_sitter") >= 2
    row = s.con.execute(
        "SELECT provenance FROM edges WHERE source='tree_sitter' LIMIT 1"
    ).fetchone()
    assert row[0] == "syntactic"


def test_identity_is_synthesized_path_based_not_scip():
    s = Store()
    ingest_tree_sitter(s, {"pkg/m.py": ("python", PY)})
    syms = s.symbols_in_file("pkg/m.py")
    assert any(sym.startswith("tree-sitter python pkg/m.py:") for sym in syms)


def test_go_and_typescript_parse_into_one_store():
    go = b"package m\nfunc Helper() int { return 1 }\nfunc Answer() int { return Helper() }\n"
    ts = b"function helper() { return 1; }\nfunction answer() { return helper(); }\n"
    s = Store()
    ingest_tree_sitter(s, {"a.go": ("go", go), "b.ts": ("typescript", ts)})
    langs = {s.symbol(sym).lang for sym in s.symbols_in_file("a.go") + s.symbols_in_file("b.ts")}
    assert langs == {"go", "typescript"}
    # within-language edge present in each, no cross-language symbol edge
    go_helper = next(sym for sym in s.symbols_in_file("a.go") if s.symbol(sym).name == "Helper")
    assert any(
        s.symbol(c).name == "Answer" for c in blast_radius(s, go_helper, direction="callers")
    )


def test_heatmap_over_treesitter_floor():
    s = Store()
    ingest_tree_sitter(s, {"m.py": ("python", PY)})
    helper = next(sym for sym in s.symbols_in_file("m.py") if s.symbol(sym).name == "helper")
    hm = heatmap(s, helper, k=10)
    assert hm and all("tree_sitter" in e.via for e in hm)


def test_unsupported_language_skipped():
    s = Store()
    stats = ingest_tree_sitter(s, {"x.rb": ("ruby", b"def foo; end")})
    assert stats.symbols == 0


def test_synth_symbol_shape():
    assert synth_symbol("python", "a/b.py", "foo", 4) == "tree-sitter python a/b.py:foo#4"

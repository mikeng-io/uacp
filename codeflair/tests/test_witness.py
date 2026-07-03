"""Witness subcommand — the scope-conformance FACTS face (UACP issue #85).

Two test layers:

- **hermetic unit tests** (no external indexer): they exercise the fact-derivation logic by
  INJECTING a fake reindex that seeds a controlled SCIP-shaped store, plus the git observation
  (changed-set, tree_token) against a real tiny fixture repo. This is the right unit boundary —
  the witness's contract is "reindex, then derive"; injection tests the derivation against a
  known graph, and the CLI/integration test below proves the real reindex wiring.
- **one integration test** (tree-sitter-gated) drives ``codeflair witness`` through the REAL
  ``build_index`` reindex on a fixture repo, so the end-to-end path is faithfully exercised.
"""

import json
import os
import subprocess

import pytest

from codeflair import cli
from codeflair.store import Edge, Store, Symbol, default_store_path
from codeflair.witness import (
    build_baseline_witness,
    build_witness,
    changed_files,
    committed_paths,
    default_branch,
    human_name,
    parse_code_ref,
    tree_token,
)

# -- fixtures -----------------------------------------------------------------------------


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo, *, default_branch="main"):
    """A git repo with .codeflair/ gitignored (the store cache must never pollute changed_files)."""
    _git(repo, "init", "-q", "-b", default_branch)
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / ".gitignore").write_text(".codeflair/\n")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "init")


def _seeder(symbols, edges):
    """A fake ``reindex`` that ignores the tree and seeds a controlled store at the repo's
    store path — standing in for ``build_index`` so derivation is tested against a known graph.
    ``symbols``: list of (symbol_id, file, name). ``edges``: list of (src, dst, rel)."""

    def reindex(repo, *, lang="python"):
        db = default_store_path(repo, create=True)
        with Store(db) as s:
            for sid, file, name in symbols:
                s.add_symbol(Symbol(symbol=sid, file=file, name=name, kind="", line=1))
                s.record_symbol_source("scip", sid)
            for src, dst, rel in edges:
                s.add_edge(Edge(src=src, dst=dst, rel=rel, source="scip"))
            s.set_watermark("deadbeef", "deadbeef")
            s.commit()
        return {"indexed": True}

    return reindex


# -- (1) changed file's symbols, hop-1 neighborhood, reasons ------------------------------


def test_witness_reports_changed_file_symbols_and_neighborhood(tmp_path):
    """A changed file -> its symbols in ``symbols_touched``; hop-1 edges (both directions) in
    ``neighborhood`` with reasons mapped onto {calls, references, defines}."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    (repo / "helper.py").write_text("# helper\n")
    (repo / "model.py").write_text("# model\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "files")
    # change ONE file after the initial commit (uncommitted edit)
    (repo / "svc.py").write_text("# svc changed\n")

    # svc.Service (in svc.py) calls helper.helper() and references model.Model; and it is
    # a container defining Service.run().
    symbols = [
        ("scip py `svc`/Service#", "svc.py", "Service#"),
        ("scip py `svc`/Service#run().", "svc.py", "run#"),
        ("scip py `helper`/helper().", "helper.py", "helper#"),
        ("scip py `model`/Model#", "model.py", "Model#"),
    ]
    edges = [
        ("scip py `svc`/Service#", "scip py `helper`/helper().", "calls"),
        ("scip py `svc`/Service#", "scip py `model`/Model#", "references"),
        ("scip py `svc`/Service#", "scip py `svc`/Service#run().", "defines"),
    ]
    doc = build_witness(repo, _seeder(symbols, edges), lang="python")

    # only svc.py changed -> its two symbols are touched (file-level), model/helper are not
    touched = {(e["file"], e["name"]) for e in doc["symbols_touched"]}
    assert touched == {("svc.py", "Service"), ("svc.py", "Service.run")}

    # hop-1 neighborhood: every edge incident to a touched symbol, both directions
    triples = {(e["src"]["name"], e["dst"]["name"], e["reason"]) for e in doc["neighborhood"]}
    assert ("Service", "helper", "calls") in triples
    assert ("Service", "Model", "references") in triples
    assert ("Service", "Service.run", "defines") in triples
    assert {e["reason"] for e in doc["neighborhood"]} <= {"calls", "references", "defines"}

    assert doc["graph_stamp"]["commit"] == cli._git_head(str(repo))
    assert doc["ingestion"] == "scip"


# -- (2) declared resolution (resolves / not / dotted parse) ------------------------------


def test_witness_declared_resolution_and_dotted_name(tmp_path):
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    symbols = [
        ("scip py `svc`/Heartgate#validate_closure().", "svc.py", "validate_closure#"),
        ("scip py `svc`/Violation#", "svc.py", "Violation#"),
    ]
    reindex = _seeder(symbols, [])
    refs = [
        parse_code_ref("svc.py:Heartgate.validate_closure"),  # qualified, resolves
        parse_code_ref("svc.py:Violation"),  # bare, resolves
        parse_code_ref("svc.py:DoesNotExist"),  # resolves: false
    ]
    doc = build_witness(repo, reindex, code_refs=refs, lang="python")

    by_name = {(d["file"], d["name"]): d["resolved"] for d in doc["declared"]}
    assert by_name[("svc.py", "Heartgate.validate_closure")] is True
    assert by_name[("svc.py", "Violation")] is True
    assert by_name[("svc.py", "DoesNotExist")] is False


def test_parse_code_ref_splits_on_first_colon_only():
    assert parse_code_ref("a/b.py:Foo.Bar.baz") == ("a/b.py", "Foo.Bar.baz")
    assert parse_code_ref("weird:path:Name") == ("weird", "path:Name")
    assert parse_code_ref("no_colon") == ("no_colon", "")  # echoed, never dropped


def test_human_name_normalization():
    def hn(sid, name=""):
        return human_name(Symbol(symbol=sid, name=name))

    assert hn("scip py `m`/Violation#") == "Violation"
    assert hn("scip py `m`/Heartgate#validate_closure().") == "Heartgate.validate_closure"
    assert hn("scip py `m`/CancelOrder#") == "CancelOrder"
    assert hn("scip-python python . . `pkg`/mod/X.X.") == "X"  # doubled module-const collapses
    # tree-sitter synth id: the bare identifier comes from the store's name column
    assert hn("tree-sitter python svc.py:helper#3", name="helper") == "helper"


# -- (3) tree_token: moves on content change, stable otherwise ----------------------------


def test_tree_token_changes_on_content_and_is_stable(tmp_path):
    repo = tmp_path
    _init_repo(repo)
    (repo / "a.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a")

    t0 = tree_token(repo, changed_files(repo))
    t0_again = tree_token(repo, changed_files(repo))
    assert t0 == t0_again  # stable when nothing changes

    (repo / "a.py").write_text("x = 2\n")  # content edit (still tracked-modified)
    t1 = tree_token(repo, changed_files(repo))
    assert t1 != t0

    (repo / "new.py").write_text("y = 1\n")  # untracked add
    t2 = tree_token(repo, changed_files(repo))
    assert t2 != t1

    (repo / "new.py").write_text("y = 2\n")  # untracked content edit -> still moves
    t3 = tree_token(repo, changed_files(repo))
    assert t3 != t2


# -- (4) neither main nor master -> committed half skipped, still works --------------------


def test_witness_without_main_or_master_branch(tmp_path):
    """On a branch where neither main nor master exists, the committed-on-branch half is
    skipped gracefully; the uncommitted half still drives the witness."""
    repo = tmp_path
    _init_repo(repo, default_branch="feature")  # no main, no master
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    assert default_branch(str(repo)) is None
    assert committed_paths(str(repo)) == set()  # skipped, not an error

    symbols = [("scip py `svc`/Service#", "svc.py", "Service#")]
    doc = build_witness(repo, _seeder(symbols, []), lang="python")
    assert {e["name"] for e in doc["symbols_touched"]} == {"Service"}
    assert "error" not in doc


# -- (5) determinism: two runs byte-identical ---------------------------------------------


def test_witness_is_byte_deterministic(tmp_path):
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    symbols = [
        ("scip py `svc`/Service#", "svc.py", "Service#"),
        ("scip py `helper`/helper().", "helper.py", "helper#"),
    ]
    edges = [("scip py `svc`/Service#", "scip py `helper`/helper().", "calls")]
    refs = [parse_code_ref("svc.py:Service")]
    reindex = _seeder(symbols, edges)

    a = json.dumps(build_witness(repo, reindex, code_refs=refs), sort_keys=True)
    b = json.dumps(build_witness(repo, reindex, code_refs=refs), sort_keys=True)
    assert a == b


# -- failure modes + unresolved_touched ---------------------------------------------------


def test_witness_not_a_git_repo_errors_nonzero(tmp_path, capsys):
    rc = cli.main(["witness", "--repo", str(tmp_path)])  # tmp_path is not a git repo
    assert rc == 1
    doc = json.loads(capsys.readouterr().out)
    assert doc["error"] == "not a git repository"


def test_witness_index_produced_nothing_errors_nonzero(tmp_path):
    repo = tmp_path
    _init_repo(repo)

    def empty_reindex(repo, *, lang="python"):
        return {"indexed": False}

    doc = build_witness(repo, empty_reindex)
    assert doc["error"] == "index produced nothing"


def test_witness_unresolved_touched_for_skipped_file(tmp_path):
    """A changed indexed-language file the ingester produced NO symbols for lands in
    ``unresolved_touched`` (honest: the file is known, the symbols are not)."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "seen.py").write_text("# seen\n")
    (repo / "skipped.py").write_text("# skipped\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "seen.py").write_text("# c1\n")
    (repo / "skipped.py").write_text("# c2\n")

    # only seen.py yields a symbol; skipped.py is a changed .py with none
    symbols = [("scip py `seen`/Seen#", "seen.py", "Seen#")]
    doc = build_witness(repo, _seeder(symbols, []), lang="python")
    assert doc["unresolved_touched"] == [{"file": "skipped.py", "name": None}]  # NULLABLE name
    assert {e["name"] for e in doc["symbols_touched"]} == {"Seen"}


def test_witness_empty_changed_py_file_is_unresolved_touched(tmp_path):
    """CONTRACT (Codex P2): a changed .py file that yields ZERO symbols after a REAL reindex
    (here an empty new file) is serialized file-level in ``unresolved_touched`` with
    ``name: null`` — known from the diff, never silently dropped (fail-open forbidden)."""
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path
    _init_repo(repo)
    (repo / "real.py").write_text("def a():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "code")
    (repo / "real.py").write_text("def a():\n    return 2\n")  # keep the index non-empty
    (repo / "empty.py").write_text("")  # changed .py with no parseable symbol

    doc = build_witness(repo, cli.build_index, lang="python")
    assert "error" not in doc
    assert {"file": "empty.py", "name": None} in doc["unresolved_touched"]


def test_witness_cli_smoke_json_shape(tmp_path, capsys):
    """The CLI wiring: ``codeflair witness`` prints a well-formed facts document with all
    contract keys. Uses a real reindex (no external indexer -> shared-string couplings only,
    so no symbols, but the document shape and success exit are what this asserts)."""
    repo = tmp_path
    _init_repo(repo)
    # the two files share a distinctive route string so the dep-free shared-string ingest
    # persists a coupling (the index is non-empty even with no external symbol indexer); the
    # edit KEEPS the shared string so the coupling survives the reindex.
    (repo / "handler.py").write_text('ROUTE = "/api/v1/cancel-order"\n')
    (repo / "client.py").write_text('url = "/api/v1/cancel-order"\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "handler.py").write_text(
        'ROUTE = "/api/v1/cancel-order"\nEXTRA = "/api/v1/cancel-order"\n'
    )

    rc = cli.main(["witness", "--repo", str(repo), "--code-ref", "handler.py:ROUTE"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) >= {
        "graph_stamp",
        "ingestion",
        "symbols_touched",
        "neighborhood",
        "declared",
        "unresolved_touched",
    }
    assert doc["graph_stamp"]["commit"] == cli._git_head(str(repo))
    assert [d["name"] for d in doc["declared"]] == ["ROUTE"]


# -- integration: the REAL reindex path (tree-sitter floor) -------------------------------


def test_witness_real_reindex_end_to_end(tmp_path):
    """Faithful end-to-end: drive ``codeflair witness`` through the REAL ``build_index``
    reindex. With the tree-sitter floor present, a changed Python file's real definitions
    show up in ``symbols_touched`` and its call edge in ``neighborhood`` (reason=calls)."""
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text(
        "def helper():\n    return 1\n\n\ndef service():\n    return helper()\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "code")
    # edit the file so it is in the uncommitted changed-set
    (repo / "svc.py").write_text(
        "def helper():\n    return 2\n\n\ndef service():\n    return helper()\n"
    )

    result = build_witness(repo, cli.build_index, lang="python")
    assert "error" not in result
    assert result["ingestion"] == "treesitter"
    names = {e["name"] for e in result["symbols_touched"]}
    assert {"helper", "service"} <= names
    triples = {(e["src"]["name"], e["dst"]["name"], e["reason"]) for e in result["neighborhood"]}
    assert ("service", "helper", "calls") in triples


# -- C1/C2: declared echo — canonical name + ambiguity ------------------------------------


def test_witness_declared_echoes_canonical_qualified_name(tmp_path):
    """C1: an UNQUALIFIED authored declared name resolves to (and echoes) the class-qualified
    CANONICAL derived name, resolved true — so kernel-side coverage compares
    canonical-to-canonical (an unqualified declared method no longer false-positives as an
    undeclared cascade AND over-declared)."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    symbols = [("scip py `svc`/Heartgate#validate_closure().", "svc.py", "validate_closure#")]
    refs = [parse_code_ref("svc.py:validate_closure")]  # UNQUALIFIED authored name
    doc = build_witness(repo, _seeder(symbols, []), code_refs=refs, lang="python")

    expected = {"file": "svc.py", "name": "Heartgate.validate_closure", "resolved": True}
    assert doc["declared"] == [expected], doc["declared"]


def test_witness_ambiguous_unqualified_declared_is_unresolved(tmp_path):
    """C2: a bare declared name matching MORE THAN ONE canonical symbol in the file is
    AMBIGUOUS -> resolved:false (an ambiguous claim must never count as coverage). The
    authored name is echoed back (never dropped)."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    symbols = [
        ("scip py `svc`/A#foo().", "svc.py", "foo#"),  # A.foo
        ("scip py `svc`/B#foo().", "svc.py", "foo#"),  # B.foo
    ]
    refs = [parse_code_ref("svc.py:foo")]  # bare, matches BOTH A.foo and B.foo
    doc = build_witness(repo, _seeder(symbols, []), code_refs=refs, lang="python")

    decl = doc["declared"]
    assert decl == [{"file": "svc.py", "name": "foo", "resolved": False}], decl


# -- C3: fresh store per witness -----------------------------------------------------------


def test_witness_fresh_store_drops_stale_symbols(tmp_path):
    """C3: build_witness deletes the store before reindex, so a symbol/edge seeded into a
    PRIOR store does not survive to manufacture false hop-1 coverage — the ingest ladder
    appends without clearing."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")

    # Pre-seed a STALE symbol + edge in the changed file.
    db = default_store_path(repo, create=True)
    with Store(db) as s:
        s.add_symbol(Symbol(symbol="scip py `svc`/Stale#", file="svc.py", name="Stale#", line=1))
        s.record_symbol_source("scip", "scip py `svc`/Stale#")
        s.add_symbol(Symbol(symbol="scip py `svc`/StaleDep#", file="svc.py", name="StaleDep#"))
        s.record_symbol_source("scip", "scip py `svc`/StaleDep#")
        s.add_edge(
            Edge(
                src="scip py `svc`/Stale#",
                dst="scip py `svc`/StaleDep#",
                rel="calls",
                source="scip",
            )
        )
        s.set_watermark("stale", "stale")
        s.commit()

    # A fresh reindex seeds DIFFERENT content (Fresh, no Stale).
    fresh = _seeder([("scip py `svc`/Fresh#", "svc.py", "Fresh#")], [])
    doc = build_witness(repo, fresh, lang="python")

    names = {(e["file"], e["name"]) for e in doc["symbols_touched"]}
    assert ("svc.py", "Fresh") in names, names
    assert ("svc.py", "Stale") not in names, "stale symbol must not survive a fresh witness store"
    edges = {(e["src"]["name"], e["dst"]["name"]) for e in doc["neighborhood"]}
    assert ("Stale", "StaleDep") not in edges, "stale edge must not survive to fake coverage"


# -- C4: non-indexed-language changed files stay visible -----------------------------------


def test_witness_non_indexed_language_file_is_unresolved_touched(tmp_path):
    """C4: a changed file OUTSIDE the indexed language (a .rs when lang=python) surfaces
    file-level in unresolved_touched ({file, name: null}), never silently dropped."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    (repo / "lib.rs").write_text("fn main() {}\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")
    (repo / "lib.rs").write_text("fn main() { let x = 1; }\n")  # changed .rs (non-python)

    symbols = [("scip py `svc`/Service#", "svc.py", "Service#")]
    doc = build_witness(repo, _seeder(symbols, []), lang="python")

    assert {"file": "lib.rs", "name": None} in doc["unresolved_touched"], doc["unresolved_touched"]
    assert {e["name"] for e in doc["symbols_touched"]} == {"Service"}


# -- C5: touched-scoped ingestion floor ----------------------------------------------------


def test_witness_touched_ingestion_floor_ignores_scip_elsewhere(tmp_path):
    """C5: the floor reflects the TOUCHED symbols' OWN sources — a tree-sitter-owned touched
    symbol yields 'treesitter' even when SCIP symbols exist ELSEWHERE (unchanged files). A
    store-global floor would launder the tree-sitter touched symbol up to 'scip'."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    (repo / "other.py").write_text("# other\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")  # ONLY svc.py changed

    def reindex(repo, *, lang="python"):
        db = default_store_path(repo, create=True)
        with Store(db) as s:
            # touched symbol (in the changed file) owned by TREE-SITTER
            ts_id = "tree-sitter python svc.py:S#1"
            s.add_symbol(Symbol(symbol=ts_id, file="svc.py", name="S", line=1))
            s.record_symbol_source("tree_sitter", ts_id)
            # a SCIP symbol ELSEWHERE (unchanged file) — the would-be laundering vector
            s.add_symbol(Symbol(symbol="scip py `other`/O#", file="other.py", name="O#", line=1))
            s.record_symbol_source("scip", "scip py `other`/O#")
            s.set_watermark("x", "x")
            s.commit()
        return {"indexed": True}

    doc = build_witness(repo, reindex, lang="python")
    assert {e["name"] for e in doc["symbols_touched"]} == {"S"}, doc["symbols_touched"]
    assert doc["ingestion"] == "treesitter", doc["ingestion"]


def test_changed_paths_sees_files_inside_new_untracked_directory(tmp_path):
    """-uall regression (#85 e2e proof): a brand-new directory must yield its
    individual files, not one collapsed '?? dir/' entry the suffix filter drops."""
    _init_repo(tmp_path)
    pkg = tmp_path / "newpkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("def f():\n    return 1\n")

    paths = changed_files(str(tmp_path))
    assert "newpkg/mod.py" in paths, paths
    assert "newpkg/" not in paths, paths


# -- inbound_counts: per-symbol inbound fan-in for touched symbols (issue #87) ------------


def _inbound_repo(tmp_path):
    """A repo where svc.py (the changed file) holds two symbols: Target (two inbound
    callers) and Lonely (no inbound). Callers live in unchanged files."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    (repo / "a.py").write_text("# a\n")
    (repo / "b.py").write_text("# b\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    (repo / "svc.py").write_text("# changed\n")  # only svc.py is touched
    return repo


def test_inbound_counts_two_distinct_callers(tmp_path):
    """(1) A touched symbol with two DISTINCT inbound callers -> count 2, keyed
    '<file>:<name>' exactly as symbols_touched serializes it."""
    repo = _inbound_repo(tmp_path)
    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `svc`/Lonely#", "svc.py", "Lonely#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
        ("scip py `b`/callerB().", "b.py", "callerB#"),
    ]
    edges = [
        ("scip py `a`/callerA().", "scip py `svc`/Target#", "calls"),
        ("scip py `b`/callerB().", "scip py `svc`/Target#", "references"),
    ]
    doc = build_witness(repo, _seeder(symbols, edges), lang="python")
    assert doc["inbound_counts"]["svc.py:Target"] == 2


def test_inbound_counts_zero_is_present_not_omitted(tmp_path):
    """(2) A touched symbol with NO inbound edges is present with count 0 (never omitted)."""
    repo = _inbound_repo(tmp_path)
    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `svc`/Lonely#", "svc.py", "Lonely#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
    ]
    edges = [("scip py `a`/callerA().", "scip py `svc`/Target#", "calls")]
    doc = build_witness(repo, _seeder(symbols, edges), lang="python")
    assert "svc.py:Lonely" in doc["inbound_counts"]
    assert doc["inbound_counts"]["svc.py:Lonely"] == 0
    # every touched symbol has an entry (no omissions)
    keys = {f"{e['file']}:{e['name']}" for e in doc["symbols_touched"]}
    assert set(doc["inbound_counts"]) == keys


def test_inbound_counts_counts_from_edges_not_capped_neighborhood(tmp_path):
    """The count derives from the store's edges table directly, independent of the
    (possibly capped) neighborhood list — a self-loop / defines edge is NOT an inbound
    reference/call, and outbound edges never count."""
    repo = _inbound_repo(tmp_path)
    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `svc`/Target#run().", "svc.py", "run#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
    ]
    edges = [
        ("scip py `a`/callerA().", "scip py `svc`/Target#", "calls"),  # inbound (counts)
        ("scip py `svc`/Target#", "scip py `svc`/Target#run().", "defines"),  # outbound+defines
        ("scip py `svc`/Target#", "scip py `a`/callerA().", "references"),  # outbound
    ]
    doc = build_witness(repo, _seeder(symbols, edges), lang="python")
    assert doc["inbound_counts"]["svc.py:Target"] == 1  # only the inbound calls edge


def test_inbound_counts_is_byte_deterministic(tmp_path):
    """(3) Two runs are byte-identical (sorted keys via sort_keys)."""
    repo = _inbound_repo(tmp_path)
    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `svc`/Lonely#", "svc.py", "Lonely#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
        ("scip py `b`/callerB().", "b.py", "callerB#"),
    ]
    edges = [
        ("scip py `a`/callerA().", "scip py `svc`/Target#", "calls"),
        ("scip py `b`/callerB().", "scip py `svc`/Target#", "references"),
    ]
    reindex = _seeder(symbols, edges)
    a = json.dumps(build_witness(repo, reindex), sort_keys=True)
    b = json.dumps(build_witness(repo, reindex), sort_keys=True)
    assert a == b


def test_inbound_counts_key_matches_symbols_touched_serialization(tmp_path):
    """(4) The inbound_counts key format is EXACTLY symbols_touched's file/name joined by a
    single colon — constructed both ways and compared, so the two never drift."""
    repo = _inbound_repo(tmp_path)
    symbols = [
        ("scip py `svc`/Heartgate#validate_closure().", "svc.py", "validate_closure#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
    ]
    edges = [("scip py `a`/callerA().", "scip py `svc`/Heartgate#validate_closure().", "calls")]
    doc = build_witness(repo, _seeder(symbols, edges), lang="python")

    # the derived-human-name key: class-qualified, colon-joined with file
    keys_from_touched = {f"{e['file']}:{e['name']}" for e in doc["symbols_touched"]}
    assert set(doc["inbound_counts"]) == keys_from_touched
    assert "svc.py:Heartgate.validate_closure" in doc["inbound_counts"]
    assert doc["inbound_counts"]["svc.py:Heartgate.validate_closure"] == 1


# == baseline_refs forecast mode (issue #86) =============================================


def test_baseline_refs_ignores_dirty_workspace(tmp_path):
    """(1) Baseline isolation via the REAL reindex: a dirty edit (and a brand-new untracked
    file) in the workspace does NOT change the graph-derived facts — they derive on HEAD only.
    Byte-compared modulo ``workspace_dirty`` (the one key that is intentionally ABOUT dirtiness,
    so it flips false->true; everything else is byte-identical)."""
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text(
        "def helper():\n    return 1\n\n\ndef service():\n    return helper()\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "code")

    refs = [parse_code_ref("svc.py:service")]
    clean = build_baseline_witness(repo, cli.build_index, code_refs=refs, lang="python")
    assert "error" not in clean, clean
    assert clean["workspace_dirty"] is False

    # A dirty edit that WOULD change a diff-grounded (mode-1) witness: svc.py body edited, a new
    # symbol added, plus a brand-new untracked file. None of it is committed.
    (repo / "svc.py").write_text(
        "def helper():\n    return 99\n\n\ndef service():\n"
        "    return helper()\n\n\ndef sneaky():\n    return 0\n"
    )
    (repo / "extra.py").write_text("def brand_new():\n    return 1\n")

    dirty = build_baseline_witness(repo, cli.build_index, code_refs=refs, lang="python")
    assert dirty["workspace_dirty"] is True

    def graph(d):
        return json.dumps({k: v for k, v in d.items() if k != "workspace_dirty"}, sort_keys=True)

    assert graph(clean) == graph(dirty), "baseline facts must not depend on the dirty tree"


def test_baseline_refs_declared_resolution_and_ambiguity(tmp_path):
    """(2) Declared resolution on the BASELINE tree: an unqualified shorthand resolves to the
    class-qualified canonical name; a bare name matching two symbols is AMBIGUOUS -> resolved
    false; a missing name -> resolved false. Same semantics as mode-1 (shared _match_ref)."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")

    symbols = [
        ("scip py `svc`/Heartgate#validate_closure().", "svc.py", "validate_closure#"),
        ("scip py `svc`/A#foo().", "svc.py", "foo#"),  # A.foo
        ("scip py `svc`/B#foo().", "svc.py", "foo#"),  # B.foo -> foo is ambiguous
    ]
    refs = [
        parse_code_ref("svc.py:validate_closure"),  # shorthand -> canonical, resolves
        parse_code_ref("svc.py:foo"),  # ambiguous -> false
        parse_code_ref("svc.py:Nope"),  # missing -> false
    ]
    doc = build_baseline_witness(repo, _seeder(symbols, []), code_refs=refs, lang="python")

    assert doc["mode"] == "baseline_refs"
    by = {(d["file"], d["name"]): d["resolved"] for d in doc["declared"]}
    assert by[("svc.py", "Heartgate.validate_closure")] is True
    assert by[("svc.py", "foo")] is False  # authored name echoed, never dropped
    assert by[("svc.py", "Nope")] is False
    head = cli._git_head(str(repo))
    assert doc["graph_stamp"]["commit"] == head
    assert doc["graph_stamp"]["tree_token"] == head  # the baseline IS the commit


def test_baseline_refs_neighborhood_and_inbound_counts(tmp_path):
    """(3) Hop-1 neighborhood + inbound_counts for a RESOLVED ref with two distinct callers."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")

    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
        ("scip py `b`/callerB().", "b.py", "callerB#"),
    ]
    edges = [
        ("scip py `a`/callerA().", "scip py `svc`/Target#", "calls"),
        ("scip py `b`/callerB().", "scip py `svc`/Target#", "references"),
    ]
    refs = [parse_code_ref("svc.py:Target")]
    doc = build_baseline_witness(repo, _seeder(symbols, edges), code_refs=refs, lang="python")

    assert doc["inbound_counts"] == {"svc.py:Target": 2}
    triples = {(e["src"]["name"], e["dst"]["name"], e["reason"]) for e in doc["neighborhood"]}
    assert ("callerA", "Target", "calls") in triples
    assert ("callerB", "Target", "references") in triples
    assert {e["reason"] for e in doc["neighborhood"]} <= {"calls", "references", "defines"}


def test_baseline_refs_workspace_dirty_flag(tmp_path):
    """(4) ``workspace_dirty`` is False on a clean checkout, True once the workspace is edited —
    independent of the (HEAD-derived) graph facts."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")
    symbols = [("scip py `svc`/Service#", "svc.py", "Service#")]

    clean = build_baseline_witness(repo, _seeder(symbols, []), lang="python")
    assert clean["workspace_dirty"] is False

    (repo / "svc.py").write_text("# dirty edit\n")  # uncommitted change on the real workspace
    dirty = build_baseline_witness(repo, _seeder(symbols, []), lang="python")
    assert dirty["workspace_dirty"] is True


def test_baseline_refs_is_byte_deterministic(tmp_path):
    """(5) Two runs are byte-identical (sort_keys, no wall clock, temp-dir path never leaks)."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")

    symbols = [
        ("scip py `svc`/Target#", "svc.py", "Target#"),
        ("scip py `a`/callerA().", "a.py", "callerA#"),
    ]
    edges = [("scip py `a`/callerA().", "scip py `svc`/Target#", "calls")]
    reindex = _seeder(symbols, edges)
    refs = [parse_code_ref("svc.py:Target")]
    a = json.dumps(build_baseline_witness(repo, reindex, code_refs=refs), sort_keys=True)
    b = json.dumps(build_baseline_witness(repo, reindex, code_refs=refs), sort_keys=True)
    assert a == b


def test_baseline_refs_omits_diff_only_keys(tmp_path):
    """(6) No ``symbols_touched`` / ``unresolved_touched`` in this mode (there is no diff) —
    ABSENT, not empty. The full key set is exactly the baseline_refs contract."""
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text("# svc\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "f")

    symbols = [("scip py `svc`/Service#", "svc.py", "Service#")]
    refs = [parse_code_ref("svc.py:Service")]
    doc = build_baseline_witness(repo, _seeder(symbols, []), code_refs=refs, lang="python")

    assert "symbols_touched" not in doc
    assert "unresolved_touched" not in doc
    assert set(doc) == {
        "mode",
        "graph_stamp",
        "ingestion",
        "declared",
        "inbound_counts",
        "neighborhood",
        "workspace_dirty",
    }


def test_baseline_refs_not_a_git_repo_errors(tmp_path):
    """not a git repo -> {"error": ...} (mode-1 parity)."""
    doc = build_baseline_witness(tmp_path, _seeder([], []), lang="python")
    assert doc["error"] == "not a git repository"


def test_baseline_refs_no_head_errors(tmp_path):
    """A repo with no commits -> no HEAD -> {"error": ...}."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    doc = build_baseline_witness(tmp_path, _seeder([], []), lang="python")
    assert doc["error"] == "no HEAD commit"


def test_baseline_refs_cli_flag_end_to_end(tmp_path, capsys):
    """The CLI wiring: ``codeflair witness --baseline-refs`` through the REAL build_index reindex
    on the committed baseline. Resolves the ref, emits the forecast neighborhood, exits 0."""
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path
    _init_repo(repo)
    (repo / "svc.py").write_text(
        "def helper():\n    return 1\n\n\ndef service():\n    return helper()\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "code")

    rc = cli.main(
        ["witness", "--repo", str(repo), "--baseline-refs", "--code-ref", "svc.py:service"]
    )
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["mode"] == "baseline_refs"
    head = cli._git_head(str(repo))
    assert doc["graph_stamp"]["commit"] == doc["graph_stamp"]["tree_token"] == head
    assert doc["workspace_dirty"] is False
    assert [d["name"] for d in doc["declared"]] == ["service"]
    triples = {(e["src"]["name"], e["dst"]["name"], e["reason"]) for e in doc["neighborhood"]}
    assert ("service", "helper", "calls") in triples


def test_baseline_refs_strips_committed_symlinks(tmp_path):
    """(C1) A COMMITTED symlink pointing at a LIVE workspace file is stripped from the
    materialized baseline before indexing, so the facts are provably independent of that live
    target (exists / changes / deleted) — byte-identical modulo ``workspace_dirty``. Without
    stripping, the indexer would follow the symlink into live/dirty workspace state, breaking
    the baseline's dirt-independence and re-derivability."""
    pytest.importorskip("tree_sitter_languages")
    repo = tmp_path
    _init_repo(repo)
    # A real committed source file so the baseline index is never empty after the strip.
    (repo / "keep.py").write_text("def keep():\n    return 0\n")
    live = repo / "real_svc.py"
    live.write_text("def service():\n    return 1\n")
    os.symlink(str(live), str(repo / "svc.py"))  # absolute symlink -> a LIVE workspace file
    _git(repo, "add", "keep.py", "svc.py")  # commit the SYMLINK; real_svc.py stays untracked/live
    _git(repo, "commit", "-q", "-m", "symlink")

    refs = [parse_code_ref("svc.py:service")]

    def graph(d):
        return json.dumps({k: v for k, v in d.items() if k != "workspace_dirty"}, sort_keys=True)

    exists = build_baseline_witness(repo, cli.build_index, code_refs=refs, lang="python")
    assert "error" not in exists, exists
    live.write_text("def service():\n    return 999\n")  # change the live target
    changed = build_baseline_witness(repo, cli.build_index, code_refs=refs, lang="python")
    live.unlink()  # delete the live target -> the committed symlink now dangles
    deleted = build_baseline_witness(repo, cli.build_index, code_refs=refs, lang="python")

    assert graph(exists) == graph(changed) == graph(deleted), (
        "baseline must not follow a committed symlink into live workspace state"
    )
    # The symlinked file is not indexable source -> its symbol never resolves.
    assert all(d["resolved"] is False for d in exists["declared"])


def test_baseline_refs_rejects_submodules(tmp_path):
    """(C2) A committed ``.gitmodules`` -> ``git archive`` cannot materialize submodule
    contents, so the baseline would silently UNDER-report the neighborhood. Detect the
    submodule config in the HEAD tree and error VISIBLY (nonzero, kernel-visible) instead of
    a silent partial account."""
    repo = tmp_path
    _init_repo(repo)
    (repo / ".gitmodules").write_text(
        '[submodule "vendor/x"]\n\tpath = vendor/x\n\turl = https://example.com/x.git\n'
    )
    _git(repo, "add", ".gitmodules")
    _git(repo, "commit", "-q", "-m", "add submodule config")

    doc = build_baseline_witness(repo, _seeder([], []), lang="python")
    assert doc["error"] == "submodules are not supported in baseline_refs mode"


def test_witness_never_observes_its_own_cache(tmp_path):
    """Post-merge P2: on a repo that does NOT gitignore .codeflair/, the witness's
    own index cache must not appear in the facts or move the tree_token."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("def f():\n    return 1\n")
    _git(tmp_path, "add", "a.py")
    _git(tmp_path, "commit", "-q", "-m", "init")
    # NO .gitignore — the cache dir is visible to porcelain on purpose.
    cache = tmp_path / ".codeflair"
    cache.mkdir()
    (cache / "index.db").write_text("stand-in")

    assert not any(p.startswith(".codeflair/") for p in changed_files(str(tmp_path)))
    tok_a = tree_token(str(tmp_path), changed_files(str(tmp_path)))
    (cache / "index.db").write_text("stand-in CHANGED")
    tok_b = tree_token(str(tmp_path), changed_files(str(tmp_path)))
    assert tok_a == tok_b, "gate-owned cache content must never move the tree token"

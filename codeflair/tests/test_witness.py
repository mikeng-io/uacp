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
import subprocess

import pytest

from codeflair import cli
from codeflair.store import Edge, Store, Symbol, default_store_path
from codeflair.witness import (
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

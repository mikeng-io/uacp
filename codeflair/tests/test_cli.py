"""P7 — the CLI delivery face (``codeflair query`` / ``codeflair index``)."""

import json
import os
import subprocess
import sys

from codeflair import Edge, Store, Symbol, cli
from codeflair.store import default_store_path

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")


def _seed_index(repo: str) -> str:
    """Persist a tiny code graph at the repo's per-worktree store path (the index BUILD)."""
    db = default_store_path(repo, create=True)
    with Store(db) as s:
        s.add_symbol(Symbol(symbol="A", file="a.py", name="A", kind="func"))
        s.add_symbol(Symbol(symbol="B", file="b.py", name="B", kind="func"))
        s.add_edge(Edge("B", "A", "calls", "scip"))  # B calls A => A's caller is B
        s.set_watermark("deadbeef", "deadbeef")
        s.commit()
    return db


def test_cli_query_emits_json_contract(tmp_path, capsys):
    """ACCEPTANCE: ``codeflair query`` runs from the CLI and emits the canonical
    ``{nodes, gaps, trace}`` JSON contract containing the seed's blast radius."""
    repo = str(tmp_path)
    _seed_index(repo)
    rc = cli.main(["query", "A", "--repo", repo])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert set(doc) == {"nodes", "gaps", "trace"}
    assert "B" in [n["symbol"] for n in doc["nodes"]]  # A's caller B is in the heatmap
    assert doc["trace"]["watermark"]["repo_commit"] == "deadbeef"


def test_cli_query_seed_not_found_is_clean(tmp_path, capsys):
    repo = str(tmp_path)
    _seed_index(repo)
    rc = cli.main(["query", "Nonexistent", "--repo", repo])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["error"] == "seed not found"


def test_cli_query_is_deterministic(tmp_path):
    """The JSON contract is byte-stable for a fixed store + seed (CF-D11)."""
    repo = str(tmp_path)
    _seed_index(repo)
    assert cli.query_to_json(repo, "A") == cli.query_to_json(repo, "A")


def test_cli_query_resolves_human_substring(tmp_path, capsys):
    """A human substring seed resolves to the stored symbol id."""
    repo = str(tmp_path)
    db = default_store_path(repo, create=True)
    with Store(db) as s:
        s.add_symbol(Symbol(symbol="scip py `m`/CancelOrder#", file="c.py", name="CancelOrder"))
        s.add_symbol(Symbol(symbol="scip py `m`/Caller#", file="d.py", name="Caller"))
        s.add_edge(Edge("scip py `m`/Caller#", "scip py `m`/CancelOrder#", "calls", "scip"))
        s.set_watermark("w", "w")
        s.commit()
    rc = cli.main(["query", "CancelOrder", "--repo", repo])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["trace"]["query"]["seed"] == "scip py `m`/CancelOrder#"


def test_cli_index_builds_store(tmp_path, capsys):
    """ACCEPTANCE: ``codeflair index`` builds the per-worktree index. Dep-free: two files share
    a distinctive route string, so the pure-text shared-string ingest persists a coupling and
    the watermark is set — proving the index path actually ran (non-vacuous)."""
    repo = tmp_path
    (repo / "handler.py").write_text('ROUTE = "/api/v1/cancel-order"\n')
    (repo / "client.py").write_text('url = "/api/v1/cancel-order"\n')
    rc = cli.main(["index", str(repo), "--lang", "python"])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["indexed"] is True

    db = default_store_path(str(repo))
    assert os.path.exists(db)
    with Store(db, read_only=True) as s:
        assert s.watermark() is not None
        coup = s.con.execute(
            "SELECT COUNT(*) FROM coupling WHERE kind='shared_string'"
        ).fetchone()[0]
    assert coup >= 1  # the shared-string ingest actually ran and persisted


def test_python_dash_m_entrypoint(tmp_path):
    """ACCEPTANCE: the CLI also runs via ``python -m codeflair`` and emits the JSON contract."""
    repo = str(tmp_path)
    _seed_index(repo)
    env = {**os.environ, "PYTHONPATH": _SRC}
    proc = subprocess.run(
        [sys.executable, "-m", "codeflair", "query", "A", "--repo", repo],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert "B" in [n["symbol"] for n in doc["nodes"]]

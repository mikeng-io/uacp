"""Integration: a REAL scip-go index -> codeflair, proving the parser handles actual
scip-go JSON (not just the synthetic fixture). Skipped when the tools are absent, so the
hermetic suite stays green without a Go toolchain."""

import json
import shutil
import subprocess

import pytest

from codeflair import Store, blast_radius, heatmap
from codeflair.scip_ingest import ingest_scip_json

pytestmark = pytest.mark.skipif(
    not (shutil.which("scip-go") and shutil.which("scip")),
    reason="requires scip-go + scip on PATH",
)

_LIB = """package m

func Helper() int { return 41 }

func Answer() int { return Helper() + 1 }

func Caller() int { return Answer() }
"""


def _index_real_module(tmp_path) -> dict:
    (tmp_path / "go.mod").write_text("module example.com/m\n\ngo 1.21\n")
    (tmp_path / "lib.go").write_text(_LIB)
    subprocess.run(
        ["scip-go", "--output", "index.scip"], cwd=tmp_path, check=True, capture_output=True
    )
    printed = subprocess.run(
        ["scip", "print", "--json", str(tmp_path / "index.scip")], check=True, capture_output=True
    )
    return json.loads(printed.stdout)


def test_real_scip_go_index_ingests_and_blast_radius_is_correct(tmp_path):
    data = _index_real_module(tmp_path)
    s = Store()
    stats = ingest_scip_json(s, data)
    assert stats.edges >= 2  # Answer->Helper, Caller->Answer

    helper = s.con.execute("SELECT symbol FROM symbols WHERE name LIKE 'Helper%'").fetchone()
    assert helper is not None
    helper_sym = helper[0]
    # the C-spike's stable identity: the SCIP descriptor, not a row id or a path
    assert helper_sym.startswith("scip-go gomod example.com/m")

    callers = blast_radius(s, helper_sym, direction="callers")
    names = {k.rsplit("/", 1)[-1]: v for k, v in callers.items()}
    assert names.get("Answer().") == 1  # Answer calls Helper directly
    assert names.get("Caller().") == 2  # Caller -> Answer -> Helper

    hm = heatmap(s, helper_sym, k=5)
    ranked = [e.symbol.rsplit("/", 1)[-1] for e in hm]
    assert ranked[0] == "Answer()."  # closer caller ranks first

"""E2E scope-conformance tests: prove ``scope_conformance.validate`` returns ZERO
violations on a genuinely complete, in-scope run, and that each computable
out-of-scope condition is CAUGHT (teeth).

The positive test reuses ``seed_coherent_run`` from test_coherence (a real
INIT -> ... -> FINALIZE run with a registered scope artifact + run-registry
entry whose write_paths agree). Each teeth test starts from that good run,
corrupts EXACTLY one thing, and asserts the specific SC_ code fires while
confirming the good run did NOT fire it.

The engine is honest about the kernel's missing per-write audit log: it does NOT
attempt "every actual file write was in-scope" (uncomputable from state). These
tests therefore exercise only the computable rules — declared-boundary validity,
scope/registry agreement, manifest-referenced-artifact containment, and
write_path workspace-escape.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from engines.base import Violation
from engines.scope_conformance import validate

from tests.e2e.test_coherence import seed_coherent_run


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


def _scope_path(root: Path, run_id: str) -> Path:
    return root / ".uacp" / "plans" / f"{run_id}-scope.yaml"


def _load_scope(root: Path, run_id: str) -> dict:
    return yaml.safe_load(_scope_path(root, run_id).read_text())


def _write_scope(root: Path, run_id: str, data: dict) -> None:
    _scope_path(root, run_id).write_text(yaml.safe_dump(data, sort_keys=False))


def _registry_path(root: Path) -> Path:
    return root / ".uacp" / "state" / "run-registry.yaml"


def _load_registry(root: Path) -> dict:
    return yaml.safe_load(_registry_path(root).read_text())


def _write_registry(root: Path, data: dict) -> None:
    _registry_path(root).write_text(yaml.safe_dump(data, sort_keys=False))


# ---------------------------------------------------------------- positive test
def test_conformant_run_has_zero_violations(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    violations = validate(temp_uacp_root, valid_run_id)
    assert violations == [], (
        f"expected zero violations, got: {[(v.code, v.message) for v in violations]}"
    )
    assert all(isinstance(v, Violation) for v in violations)


# -------------------------------------------------- SC_SCOPE_REGISTRY_DISAGREE
def test_sc_scope_registry_write_paths_disagree(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "SC_SCOPE_REGISTRY_DISAGREE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Mutate the scope's write_paths so it no longer matches the registry ([]).
    body = _load_scope(temp_uacp_root, valid_run_id)
    body["write_paths"] = ["docs/elsewhere/"]
    _write_scope(temp_uacp_root, valid_run_id, body)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_SCOPE_REGISTRY_DISAGREE" in codes, codes


def test_sc_scope_registry_scope_artifact_path_disagree(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "SC_SCOPE_REGISTRY_DISAGREE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Point the registry's scope_artifact_path at a different artifact than the
    # manifest references, leaving write_paths in agreement.
    reg = _load_registry(temp_uacp_root)
    reg["active_runs"][0]["scope_artifact_path"] = f"plans/{valid_run_id}-OTHER-scope.yaml"
    _write_registry(temp_uacp_root, reg)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_SCOPE_REGISTRY_DISAGREE" in codes, codes


# ------------------------------------------------------- SC_ARTIFACT_OUT_OF_SCOPE
def test_sc_artifact_out_of_scope(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "SC_ARTIFACT_OUT_OF_SCOPE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Write an artifact OUTSIDE every declared write_path and every permitted
    # output surface (docs/ is neither in write_paths==[] nor an output surface),
    # then make the manifest reference it.
    out_rel = "docs/out-of-scope-product.yaml"
    (temp_uacp_root / "docs").mkdir(parents=True, exist_ok=True)
    (temp_uacp_root / out_rel).write_text("kind: stray\n")

    manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml"
    data = yaml.safe_load(manifest_path.read_text())
    data.setdefault("artifacts", {})["stray"] = out_rel
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False))

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_ARTIFACT_OUT_OF_SCOPE" in codes, codes


def test_sc_artifact_in_declared_write_path_is_ok(temp_uacp_root: Path, valid_run_id: str):
    """A referenced artifact UNDER a declared write_path must NOT fire."""
    seed_coherent_run(temp_uacp_root, valid_run_id)

    # Declare docs/ writable (and mirror it in the registry so the scope/registry
    # check stays clean), then reference an artifact under docs/.
    body = _load_scope(temp_uacp_root, valid_run_id)
    body["write_paths"] = ["docs/"]
    _write_scope(temp_uacp_root, valid_run_id, body)
    reg = _load_registry(temp_uacp_root)
    reg["active_runs"][0]["write_paths"] = ["docs/"]
    _write_registry(temp_uacp_root, reg)

    in_rel = "docs/in-scope-product.yaml"
    (temp_uacp_root / "docs").mkdir(parents=True, exist_ok=True)
    (temp_uacp_root / in_rel).write_text("kind: in-scope\n")
    manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml"
    data = yaml.safe_load(manifest_path.read_text())
    data.setdefault("artifacts", {})["product"] = in_rel
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False))

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_ARTIFACT_OUT_OF_SCOPE" not in codes, codes


def test_sc_arbitrary_file_under_governance_home_is_still_flagged(
    temp_uacp_root: Path, valid_run_id: str
):
    """Containment is preserved by KIND, not by a dir-prefix whitelist (D43 Option B).

    ``uacp_artifact_write`` permits ARBITRARY non-manifest files under the governance
    homes (plans/proposals/executions) — it only refuses RELATION-plane *manifest*
    kinds. So a real EXECUTE product dumped under ``executions/`` and registered must
    STILL be flagged out-of-scope. Whitelisting ``executions/`` by prefix would let it
    pass — a containment bypass. The RELATION-plane governance chain that
    ``seed_coherent_run`` registers (keyed scope module, PIV, checkpoint, assessment)
    is exempt by KIND, so the good run stays clean."""
    seed_coherent_run(temp_uacp_root, valid_run_id)  # write_paths == []
    assert "SC_ARTIFACT_OUT_OF_SCOPE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # An arbitrary, NON-manifest file under executions/ (a governance HOME), registered.
    # It has no RELATION manifest kind, so it is NOT governance and is out-of-scope.
    evil_rel = f"executions/{valid_run_id}-exfil.py"
    (temp_uacp_root / ".uacp" / "executions").mkdir(parents=True, exist_ok=True)
    (temp_uacp_root / ".uacp" / evil_rel).write_text("print('arbitrary execute product')\n")
    manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{valid_run_id}.yaml"
    data = yaml.safe_load(manifest_path.read_text())
    data.setdefault("artifacts", {})["exfil"] = evil_rel
    manifest_path.write_text(yaml.safe_dump(data, sort_keys=False))

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_ARTIFACT_OUT_OF_SCOPE" in codes, codes


# -------------------------------------------------------- SC_BLAST_RADIUS_INVALID
def test_sc_blast_radius_invalid(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "SC_BLAST_RADIUS_INVALID" not in _codes(validate(temp_uacp_root, valid_run_id))

    body = _load_scope(temp_uacp_root, valid_run_id)
    body["blast_radius"] = "apocalyptic"  # not in [low, medium, high, critical]
    _write_scope(temp_uacp_root, valid_run_id, body)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_BLAST_RADIUS_INVALID" in codes, codes


def test_sc_blast_radius_valid_value_is_ok(temp_uacp_root: Path, valid_run_id: str):
    """A declared blast_radius inside the schema enum must NOT fire."""
    seed_coherent_run(temp_uacp_root, valid_run_id)

    body = _load_scope(temp_uacp_root, valid_run_id)
    body["blast_radius"] = "low"
    _write_scope(temp_uacp_root, valid_run_id, body)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_BLAST_RADIUS_INVALID" not in codes, codes


# --------------------------------------------------- SC_WRITE_PATH_ESCAPES_WORKSPACE
def test_sc_write_path_escapes_workspace(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "SC_WRITE_PATH_ESCAPES_WORKSPACE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Declare a write_path that traverses out of the workspace. Mirror it in the
    # registry so the divergence under test is the escape, not a scope/registry
    # disagreement.
    escape = "../../etc/passwd"
    body = _load_scope(temp_uacp_root, valid_run_id)
    body["write_paths"] = [escape]
    _write_scope(temp_uacp_root, valid_run_id, body)
    reg = _load_registry(temp_uacp_root)
    reg["active_runs"][0]["write_paths"] = [escape]
    _write_registry(temp_uacp_root, reg)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "SC_WRITE_PATH_ESCAPES_WORKSPACE" in codes, codes


# --------------------------------------------------------- defensive: never raises
def test_never_raises_on_missing_run(temp_uacp_root: Path):
    out = validate(temp_uacp_root, "no-such-run")
    assert isinstance(out, list) and out == []  # no manifest -> nothing to conform to


def test_never_raises_on_missing_scope(temp_uacp_root: Path, another_run_id: str):
    # A run that has not declared a scope: write a bare manifest with no scope
    # artifact reference -> no-op, no exception.
    manifest_path = temp_uacp_root / ".uacp" / "state" / "runs" / f"{another_run_id}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump({"run_id": another_run_id, "artifacts": {}}))
    out = validate(temp_uacp_root, another_run_id)
    assert isinstance(out, list) and out == []


def test_never_raises_on_missing_registry(temp_uacp_root: Path, valid_run_id: str):
    # Scope declared but registry absent -> scope/registry check is a no-op; the
    # other (registry-independent) checks still run without raising.
    seed_coherent_run(temp_uacp_root, valid_run_id)
    (temp_uacp_root / ".uacp" / "state" / "run-registry.yaml").unlink()
    out = validate(temp_uacp_root, valid_run_id)
    assert isinstance(out, list)
    assert "SC_SCOPE_REGISTRY_DISAGREE" not in _codes(out)


def test_never_raises_on_garbled_scope(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _scope_path(temp_uacp_root, valid_run_id).write_text("this: : : not valid yaml: [")
    out = validate(temp_uacp_root, valid_run_id)
    assert isinstance(out, list)  # garbled scope -> no-op, not an exception


# ------------------------------------------------------------- SC diff containment
# C1 (issue #85): the module docstring's documented "future mode", now implemented —
# compare the ACTUAL git-observed change set against the DECLARED write_paths.
# Advisory-first: every SC_DIFF_* violation is severity "warn" (correct-but-out-of-
# scope is a governance flag, remedy = re-declare — never a silent allow, never yet
# a block). Absent git repo at the workspace root is a documented no-op (mirrors
# the absent-scope precedent) so the synthetic temp-root fixtures above stay quiet.

import subprocess  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@test",
            "-c",
            "user.name=t",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(root: Path) -> None:
    """Turn the seeded temp workspace into a git repo whose baseline commit is the
    post-seed state — so anything written AFTER this call is 'the run's changes'."""
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed", "--no-verify")


def _declare_write_paths(root: Path, run_id: str, wps: list[str]) -> None:
    """Set write_paths identically on scope + registry so the ONLY divergence a
    diff test exercises is the diff itself, never scope/registry disagreement."""
    body = _load_scope(root, run_id)
    body["write_paths"] = wps
    _write_scope(root, run_id, body)
    reg = _load_registry(root)
    reg["active_runs"][0]["write_paths"] = wps
    _write_registry(root, reg)


def _diff_codes(violations: list[Violation]) -> set[str]:
    return {v.code for v in violations if v.code.startswith("SC_DIFF_")}


def test_diff_out_of_scope_uncommitted_fires(temp_uacp_root: Path, valid_run_id: str):
    """An uncommitted write OUTSIDE every declared write_path fires
    SC_DIFF_OUT_OF_SCOPE (advisory), naming the offending file."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue.py").write_text("# out-of-scope write\n")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE, got {_codes(violations)}"
    assert any("rogue.py" in v.message for v in hits), [v.message for v in hits]
    assert all(v.severity == "warn" for v in hits), "advisory-first: must be warn"


def test_diff_in_scope_changes_quiet(temp_uacp_root: Path, valid_run_id: str):
    """Writes under a declared write_path produce NO SC_DIFF_* violations."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "src").mkdir()
    (temp_uacp_root / "src" / "ok.py").write_text("# in-scope write\n")

    assert _diff_codes(validate(temp_uacp_root, valid_run_id)) == set()


def test_diff_committed_on_branch_fires(temp_uacp_root: Path, valid_run_id: str):
    """An out-of-scope change COMMITTED on the run's branch (not just uncommitted)
    is still caught — the changed set is uncommitted ∪ committed-since-merge-base."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    _git(temp_uacp_root, "checkout", "-q", "-b", "run-branch")
    (temp_uacp_root / "rogue.py").write_text("# committed out-of-scope\n")
    _git(temp_uacp_root, "add", "rogue.py")
    _git(temp_uacp_root, "commit", "-q", "-m", "rogue", "--no-verify")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE, got {_codes(violations)}"
    assert any("rogue.py" in v.message for v in hits), [v.message for v in hits]


def test_diff_no_git_repo_is_noop(temp_uacp_root: Path, valid_run_id: str):
    """No .git at the workspace root -> the diff check self-disables (documented
    no-op, same doctrine as absent scope). This is what keeps every synthetic
    fixture in this file quiet."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert _diff_codes(validate(temp_uacp_root, valid_run_id)) == set()


def test_diff_broken_git_repo_fires_unavailable(temp_uacp_root: Path, valid_run_id: str):
    """A .git entry EXISTS but git cannot read it -> the witness is expected but
    unavailable. Fail-closed distinction: that is SC_DIFF_UNAVAILABLE (advisory),
    never a silent pass."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    (temp_uacp_root / ".git").mkdir()  # empty dir = present but not a valid repo

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_UNAVAILABLE"]
    assert hits, f"expected SC_DIFF_UNAVAILABLE, got {_codes(violations)}"
    assert all(v.severity == "warn" for v in hits)


def test_diff_governed_namespace_changes_quiet(temp_uacp_root: Path, valid_run_id: str):
    """Writes under the governed namespace (.uacp/) are governed-writer territory
    (Guardian-protected), not free-form EXECUTE writes -> never SC_DIFF-flagged."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _init_git_repo(temp_uacp_root)
    note = temp_uacp_root / ".uacp" / "state" / "post-seed-note.yaml"
    note.write_text("note: governed-namespace write\n")

    assert _diff_codes(validate(temp_uacp_root, valid_run_id)) == set()


# ---------------------------------------------------------- SC cascade witness (#85)
# The scope-witness half of #85: the agent AUTHORS code_refs (the falsifiable claim);
# the GATE derives an INDEPENDENT account by exec'ing the codeflair CLI (design node 02).
# These teeth tests drive the engine through a STUB CLI resolved from operator config
# (config/uacp.toml [witness].codeflair_cli via a per-root .uacp/config.toml override —
# the FAITHFUL resolution path, no monkeypatch: it also proves the trust root reads from
# operator config, never the workspace). The stub prints a fixture JSON (parameterized by
# writing it to a file the stub cats) and appends to an invocations log, so tests both
# assert verdicts and count CLI invocations for the memo test. All witness codes are
# advisory severity "warn".

import json  # noqa: E402
import sys  # noqa: E402

from engines.io import clear_witness_memo, derive_witness  # noqa: E402

from config import clear_config_cache  # noqa: E402

_WITNESS_CODES = {
    "SC_UNDECLARED_CASCADE",
    "SC_SCOPE_OVERDECLARED",
    "SC_WITNESS_UNRESOLVED_CLAIM",
    "SC_WITNESS_UNAVAILABLE",
}

# The stub CLI: append one byte to calls.log, print fixture.json to stdout, exit 0.
_STUB_SRC = (
    "import pathlib, sys\n"
    "here = pathlib.Path(__file__).resolve().parent\n"
    "with (here / 'calls.log').open('a') as _f:\n"
    "    _f.write('x')\n"
    "sys.stdout.write((here / 'fixture.json').read_text())\n"
)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_witness_memo():
    """The witness derivation memo is process-global — reset it around each test."""
    clear_witness_memo()
    yield
    clear_witness_memo()


def _install_stub(stub_dir: Path, fixture: object) -> tuple[Path, Path]:
    """Write the stub CLI + its fixture under ``stub_dir``. ``fixture`` is dumped as
    JSON when a dict/list, else written verbatim (for the garbled-stdout case).
    Returns (stub_py, calls_log)."""
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_py = stub_dir / "stub.py"
    stub_py.write_text(_STUB_SRC)
    fixture_path = stub_dir / "fixture.json"
    if isinstance(fixture, (dict, list)):
        fixture_path.write_text(json.dumps(fixture))
    else:
        fixture_path.write_text(str(fixture))
    calls_log = stub_dir / "calls.log"
    return stub_py, calls_log


def _configure_witness_cli(root: Path, cli: str) -> None:
    """Point [witness].codeflair_cli (operator config) at ``cli`` via a per-root
    .uacp/config.toml override — the real resolution path the kernel uses."""
    cfg = root / ".uacp" / "config.toml"
    cfg.write_text(f"[witness]\ncodeflair_cli = {json.dumps(cli)}\n")
    clear_config_cache()


def _stub_cli(stub_py: Path) -> str:
    return f"{json.dumps(sys.executable)[1:-1]} {stub_py}"


def _set_code_refs(root: Path, run_id: str, refs: list[dict[str, str]]) -> None:
    body = _load_scope(root, run_id)
    body["code_refs"] = refs
    _write_scope(root, run_id, body)


def _sym_json(file: str, name: str) -> dict:
    return {"file": file, "name": name}


def _decl(file: str, name: str, resolved: bool) -> dict:
    return {"file": file, "name": name, "resolved": resolved}


def _edge(src: tuple[str, str], dst: tuple[str, str], reason: str = "calls") -> dict:
    return {"src": _sym_json(*src), "dst": _sym_json(*dst), "reason": reason}


def _witness_fixture(
    *,
    ingestion: str = "scip",
    declared: list[dict] | None = None,
    symbols_touched: list[tuple[str, str]] | None = None,
    neighborhood: list[dict] | None = None,
    unresolved_touched: list[tuple[str, str]] | None = None,
) -> dict:
    return {
        "graph_stamp": {"commit": "deadbeef", "tree_token": "t1"},
        "ingestion": ingestion,
        "symbols_touched": [_sym_json(f, n) for f, n in (symbols_touched or [])],
        "neighborhood": neighborhood or [],
        "declared": declared or [],
        "unresolved_touched": [_sym_json(f, n) for f, n in (unresolved_touched or [])],
    }


def _witness_codes(violations: list[Violation]) -> set[str]:
    return {v.code for v in violations if v.code in _WITNESS_CODES}


# (a) undeclared cascade fires, naming the symbol, severity warn.
def test_witness_undeclared_cascade_fires(temp_uacp_root: Path, valid_run_id: str, tmp_path: Path):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/b.py", "Beta")],  # Beta not adjacent
        neighborhood=[],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert hits, f"expected SC_UNDECLARED_CASCADE, got {_codes(violations)}"
    assert any("Beta" in v.message for v in hits), [v.message for v in hits]
    assert all(v.severity == "warn" for v in hits)
    assert "SC_SCOPE_OVERDECLARED" not in _codes(violations)


# (b) touched symbol hop-1-connected to a declared ref -> quiet.
def test_witness_hop1_connected_is_quiet(temp_uacp_root: Path, valid_run_id: str, tmp_path: Path):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/b.py", "Beta")],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("src/b.py", "Beta"))],  # Beta hop-1 of Alpha
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    assert _witness_codes(validate(temp_uacp_root, valid_run_id)) == set()


# (c) over-declaration fires.
def test_witness_over_declaration_fires(temp_uacp_root: Path, valid_run_id: str, tmp_path: Path):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(
        temp_uacp_root,
        valid_run_id,
        [{"file": "src/a.py", "name": "Alpha"}, {"file": "src/z.py", "name": "Zeta"}],
    )
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True), _decl("src/z.py", "Zeta", True)],
        symbols_touched=[("src/a.py", "Alpha")],  # Zeta neither touched nor adjacent
        neighborhood=[],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_SCOPE_OVERDECLARED"]
    assert hits, f"expected SC_SCOPE_OVERDECLARED, got {_codes(violations)}"
    assert any("Zeta" in v.message for v in hits), [v.message for v in hits]
    assert all(v.severity == "warn" for v in hits)
    assert "SC_UNDECLARED_CASCADE" not in _codes(violations)


# (d) unresolved declared ref fires SC_WITNESS_UNRESOLVED_CLAIM and does NOT count as coverage.
def test_witness_unresolved_declared_does_not_cover(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(
        temp_uacp_root,
        valid_run_id,
        [{"file": "src/a.py", "name": "Alpha"}, {"file": "src/ghost.py", "name": "Ghost"}],
    )
    # Alpha resolves; Ghost does NOT. G2 is touched and hop-1-adjacent ONLY to the
    # UNRESOLVED Ghost -> Ghost must not cover it, so G2 is an undeclared cascade.
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True), _decl("src/ghost.py", "Ghost", False)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/g2.py", "G2")],
        neighborhood=[_edge(("src/ghost.py", "Ghost"), ("src/g2.py", "G2"))],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    codes = _codes(violations)
    assert "SC_WITNESS_UNRESOLVED_CLAIM" in codes, codes
    assert any("Ghost" in v.message for v in violations if v.code == "SC_WITNESS_UNRESOLVED_CLAIM")
    # Proof the unresolved ref did not count as coverage: G2 shows up as a cascade.
    cascade = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert cascade and any("G2" in v.message for v in cascade), (
        "unresolved declared ref must not cover its neighbor"
    )


# (e) no code_refs -> no witness codes and the CLI is never invoked.
def test_witness_no_code_refs_is_noop_and_never_invokes_cli(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)  # no code_refs on the scope
    fixture = _witness_fixture(declared=[], symbols_touched=[])
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    assert _witness_codes(violations) == set()
    assert not calls_log.exists(), "CLI must not be invoked when no code_refs are declared"


# (f) unconfigured / absent CLI -> SC_WITNESS_UNAVAILABLE.
def test_witness_unconfigured_cli_is_unavailable(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    # No [witness] config written -> codeflair_cli is None -> unconfigured.

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert all(v.severity == "warn" for v in hits)
    assert any("not configured" in (v.detail.get("error") or "") for v in hits)


# (g) garbled stdout -> SC_WITNESS_UNAVAILABLE.
def test_witness_garbled_stdout_is_unavailable(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    stub_py, calls_log = _install_stub(tmp_path / "cf", "this is not json {[")
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert all(v.severity == "warn" for v in hits)
    # Garbled output is retried ONCE before reporting unavailable (2 invocations).
    assert calls_log.read_text() == "xx", "garbled derivation must retry exactly once"


# (h) ingestion "treesitter" -> SC_WITNESS_UNAVAILABLE (weaker provenance floor rejected).
def test_witness_weaker_provenance_floor_is_unavailable(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        ingestion="treesitter",
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("scip" in v.message or "provenance" in v.message for v in hits), [
        v.message for v in hits
    ]


# (i) memo reuse: two validate() calls with an unchanged tree invoke the CLI exactly once.
def test_witness_memo_reuse_invokes_cli_once(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))
    # A git repo is required for the tree-token approximation the memo keys on.
    _init_git_repo(temp_uacp_root)

    first = validate(temp_uacp_root, valid_run_id)
    second = validate(temp_uacp_root, valid_run_id)
    assert _witness_codes(first) == set()
    assert _witness_codes(second) == set()
    assert calls_log.read_text() == "x", "unchanged tree must reuse the memoized derivation"


# (i-bis) memo key includes the claim: same tree, CHANGED code_refs -> CLI re-invoked.
# Driven at the io seam directly so the tree token is held CONSTANT while only the
# claim changes (changing code_refs via the scope file would also change the tree).
def test_witness_memo_rederives_on_changed_code_refs(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))
    _init_git_repo(temp_uacp_root)  # tree token stays constant across the calls below

    refs_a = [{"file": "src/a.py", "name": "Alpha"}]
    refs_b = [{"file": "src/b.py", "name": "Beta"}]
    derive_witness(temp_uacp_root, refs_a)  # exec (1)
    derive_witness(temp_uacp_root, refs_a)  # memo hit (unchanged tree + claim)
    derive_witness(temp_uacp_root, refs_b)  # changed claim -> re-derive (2)
    assert calls_log.read_text() == "xx", (
        "same tree but changed code_refs must re-derive (stdout depends on the claim)"
    )


# (j) unresolved_touched tolerates a NULL name (file-level entry for an unparseable file):
# it must parse cleanly and surface the bare file path in the cascade advisory detail.
def test_witness_unresolved_touched_null_name_tolerated(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/b.py", "Beta")],  # Beta -> cascade
        neighborhood=[],
    )
    # A file-level unresolved entry with a NULL name (unparseable new file).
    fixture["unresolved_touched"] = [{"file": "src/new.py", "name": None}]
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(temp_uacp_root, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    cascade = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert cascade, f"expected SC_UNDECLARED_CASCADE, got {_codes(violations)}"
    # The null-name file surfaces as the bare path in the advisory detail, not dropped.
    assert any("src/new.py" in v.detail.get("unresolved_touched", []) for v in cascade), [
        v.detail for v in cascade
    ]

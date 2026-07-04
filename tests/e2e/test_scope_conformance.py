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
import stat  # noqa: E402
import sys  # noqa: E402

import engines.io.witnessio as witnessio  # noqa: E402
from engines.io import clear_witness_memo, derive_witness  # noqa: E402

_WITNESS_CODES = {
    "SC_UNDECLARED_CASCADE",
    "SC_SCOPE_OVERDECLARED",
    "SC_WITNESS_UNRESOLVED_CLAIM",
    "SC_WITNESS_UNRESOLVED_TOUCHED",
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

# A stub that records its invocation then SLEEPS past a (monkeypatched) short timeout —
# used to prove a transient timeout is retried exactly once (K6).
_SLEEP_STUB_SRC = (
    "import pathlib, time\n"
    "here = pathlib.Path(__file__).resolve().parent\n"
    "with (here / 'calls.log').open('a') as _f:\n"
    "    _f.write('x')\n"
    "time.sleep(5)\n"
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


def _configure_witness_cli(monkeypatch, op_dir: Path, cli: str) -> None:
    """Point the KERNEL-DEFAULT [witness].codeflair_cli at ``cli`` by monkeypatching the
    operator-config seam (``witnessio._operator_config_path``) at a temp toml (K1).

    This is the FAITHFUL resolution path: the workspace ``.uacp/config.toml`` is
    explicitly IGNORED for the ``[witness]`` table (an override-wins merge would hand the
    witnessed agent the pointer), so tests must configure the kernel-default seam — not a
    workspace override. Real ``tomllib`` parsing is still exercised (the seam only swaps
    which file is read)."""
    op = op_dir / "operator-uacp.toml"
    op.write_text(f"[witness]\ncodeflair_cli = {json.dumps(cli)}\n")
    monkeypatch.setattr(witnessio, "_operator_config_path", lambda: op)


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
def test_witness_undeclared_cascade_fires(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/b.py", "Beta")],  # Beta not adjacent
        neighborhood=[],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert hits, f"expected SC_UNDECLARED_CASCADE, got {_codes(violations)}"
    assert any("Beta" in v.message for v in hits), [v.message for v in hits]
    assert all(v.severity == "warn" for v in hits)
    assert "SC_SCOPE_OVERDECLARED" not in _codes(violations)


# (b) touched symbol hop-1-connected to a declared ref -> quiet.
def test_witness_hop1_connected_is_quiet(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha"), ("src/b.py", "Beta")],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("src/b.py", "Beta"))],  # Beta hop-1 of Alpha
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    assert _witness_codes(validate(temp_uacp_root, valid_run_id)) == set()


# (c) over-declaration fires.
def test_witness_over_declaration_fires(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
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
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_SCOPE_OVERDECLARED"]
    assert hits, f"expected SC_SCOPE_OVERDECLARED, got {_codes(violations)}"
    assert any("Zeta" in v.message for v in hits), [v.message for v in hits]
    assert all(v.severity == "warn" for v in hits)
    assert "SC_UNDECLARED_CASCADE" not in _codes(violations)


# (d) unresolved declared ref fires SC_WITNESS_UNRESOLVED_CLAIM and does NOT count as coverage.
def test_witness_unresolved_declared_does_not_cover(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
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
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

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
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)  # no code_refs on the scope
    fixture = _witness_fixture(declared=[], symbols_touched=[])
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

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
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    stub_py, calls_log = _install_stub(tmp_path / "cf", "this is not json {[")
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert all(v.severity == "warn" for v in hits)
    # Garbled output is DETERMINISTIC (K6): it must fail immediately, NOT retry — retrying
    # buys latency, not signal. Only a transient timeout retries. Exactly one invocation.
    assert calls_log.read_text() == "x", "garbled derivation must NOT retry (deterministic)"


# (h) ingestion "treesitter" -> SC_WITNESS_UNAVAILABLE (weaker provenance floor rejected).
def test_witness_weaker_provenance_floor_is_unavailable(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        ingestion="treesitter",
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("scip" in v.message or "provenance" in v.message for v in hits), [
        v.message for v in hits
    ]


# (i) memo reuse: two validate() calls with an unchanged tree invoke the CLI exactly once.
def test_witness_memo_reuse_invokes_cli_once(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
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
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
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
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
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
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    cascade = [v for v in violations if v.code == "SC_UNDECLARED_CASCADE"]
    assert cascade, f"expected SC_UNDECLARED_CASCADE, got {_codes(violations)}"
    # The null-name file surfaces as the bare path in the advisory detail, not dropped.
    assert any("src/new.py" in v.detail.get("unresolved_touched", []) for v in cascade), [
        v.detail for v in cascade
    ]


def test_diff_out_of_scope_inside_new_directory_fires(temp_uacp_root: Path, valid_run_id: str):
    """Files inside an entirely-NEW untracked directory must be observed
    individually (-uall): without it, porcelain collapses the dir to one
    '?? dir/' entry and every file inside is invisible — found by the #85
    end-to-end proof, invisible to the root-level-file fixtures above."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "newpkg").mkdir()
    (temp_uacp_root / "newpkg" / "rogue.py").write_text("# nested out-of-scope\n")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE, got {_codes(violations)}"
    assert any("newpkg/rogue.py" in v.message for v in hits), [v.message for v in hits]


# ---------------------------------------------------------- K1: executable trust root
# The witness command is resolved from the KERNEL-DEFAULT config ONLY — the workspace
# .uacp/config.toml [witness] table is IGNORED (an override-wins merge would hand the
# witnessed agent the pointer), argv[0] is resolved to an absolute path and REJECTED if
# it lands under the run workspace, and the resolved argv is recorded for audit.


def test_witness_workspace_config_is_ignored(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    """A workspace .uacp/config.toml [witness].codeflair_cli MUST be ignored: with no
    [witness] in the kernel default (and NO operator seam monkeypatch), the witness is
    UNCONFIGURED — the workspace-named stub is never invoked (K1 adversarial blocker)."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)], symbols_touched=[("src/a.py", "Alpha")]
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    # A friendly witness the agent points its OWN workspace config at — must NOT win.
    cfg = temp_uacp_root / ".uacp" / "config.toml"
    cfg.write_text(f"[witness]\ncodeflair_cli = {json.dumps(_stub_cli(stub_py))}\n")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("not configured" in (v.detail.get("error") or "") for v in hits), [
        v.detail for v in hits
    ]
    assert not calls_log.exists(), "the workspace-configured witness must never be invoked"


def test_witness_cli_under_workspace_is_rejected(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """A configured CLI that resolves UNDER the run workspace is a tampered work-product
    prober (ADR-0019 does not raw-block work-product writes) → UNAVAILABLE naming the
    reason, never exec'd."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    evil = temp_uacp_root / "evil-witness"
    evil.write_text("#!/bin/sh\necho '{}'\n")  # would print junk if ever run
    evil.chmod(evil.stat().st_mode | stat.S_IEXEC)
    _configure_witness_cli(monkeypatch, tmp_path, str(evil))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("under the run workspace" in (v.detail.get("error") or "") for v in hits), [
        v.detail for v in hits
    ]


def test_witness_records_resolved_absolute_argv(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """The RESOLVED (absolute) argv is recorded in WitnessResult.command — the trust root
    is auditable."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)], symbols_touched=[("src/a.py", "Alpha")]
    )
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    res = derive_witness(temp_uacp_root, [{"file": "src/a.py", "name": "Alpha"}])
    assert res.available, res.error
    assert res.command, "the resolved argv must be recorded"
    assert Path(res.command[0]).is_absolute()
    assert res.command[0] == str(Path(sys.executable).resolve())


# --------------------------------------------------------- K2: content-sensitive memo
def test_witness_content_only_edit_rederives(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """Editing an ALREADY-DIRTY tracked file's CONTENT (status letter unchanged) moves the
    memo token, so the witness is re-derived — a HEAD+status-only token would wrongly reuse
    a stale account (K2)."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)], symbols_touched=[("src/a.py", "Alpha")]
    )
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    _init_git_repo(temp_uacp_root)

    tracked = temp_uacp_root / "dirty.py"
    tracked.write_text("x = 1\n")
    _git(temp_uacp_root, "add", "dirty.py")
    _git(temp_uacp_root, "commit", "-q", "-m", "add dirty", "--no-verify")
    tracked.write_text("x = 2\n")  # now tracked-modified (status ' M')

    refs = [{"file": "src/a.py", "name": "Alpha"}]
    derive_witness(temp_uacp_root, refs)  # exec (1)
    derive_witness(temp_uacp_root, refs)  # memo hit (unchanged tree + claim)
    tracked.write_text("x = 3\n")  # content-only edit, STILL status ' M'
    derive_witness(temp_uacp_root, refs)  # token moved -> re-derive (2)
    assert calls_log.read_text() == "xx", (
        "a content-only edit to an already-dirty file must move the memo token"
    )


# ----------------------------------------------------- K3: unconditional unresolved-touched
def test_witness_unresolved_touched_fires_unconditionally(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """unresolved_touched fires SC_WITNESS_UNRESOLVED_TOUCHED whenever non-empty, even with
    NO cascade — a diff whose only unresolved artifact is a file (nullable name) must not
    vanish (K3)."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],  # Alpha declared+touched -> no cascade
        neighborhood=[],
    )
    fixture["unresolved_touched"] = [{"file": "src/weird.rs", "name": None}]  # nullable name
    stub_py, _ = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    codes = _codes(violations)
    assert "SC_WITNESS_UNRESOLVED_TOUCHED" in codes, codes
    assert "SC_UNDECLARED_CASCADE" not in codes, codes
    hits = [v for v in violations if v.code == "SC_WITNESS_UNRESOLVED_TOUCHED"]
    assert all(v.severity == "warn" for v in hits)
    assert any("src/weird.rs" in v.detail.get("unresolved_touched", []) for v in hits), [
        v.detail for v in hits
    ]


# ----------------------------------------------------------- K5: strict wire validation
def test_witness_malformed_neighborhood_is_unavailable(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """A single malformed neighborhood entry (bad ``reason``) fails the whole account →
    SC_WITNESS_UNAVAILABLE (fail-closed), NOT a quiet drop; and being deterministic it is
    NOT retried (K5 + K6)."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    fixture = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)], symbols_touched=[("src/a.py", "Alpha")]
    )
    fixture["neighborhood"] = [
        {
            "src": {"file": "src/a.py", "name": "Alpha"},
            "dst": {"file": "src/b.py", "name": "Beta"},
            "reason": "bogus",  # not in {calls, references, defines}
        }
    ]
    stub_py, calls_log = _install_stub(tmp_path / "cf", fixture)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert calls_log.read_text() == "x", "malformed (deterministic) output must NOT retry"


# ------------------------------------------------------------- K6: transient-only retry
def test_witness_timeout_retries_once(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """A subprocess TIMEOUT is transient and retried EXACTLY once (2 invocations) before
    reporting unavailable (K6). Contrast the garbled/malformed cases, which do not retry."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    stub_dir = tmp_path / "cf"
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_py = stub_dir / "stub.py"
    stub_py.write_text(_SLEEP_STUB_SRC)
    calls_log = stub_dir / "calls.log"
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    monkeypatch.setattr(witnessio, "_WITNESS_TIMEOUT_SECONDS", 0.4)

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("timed out" in (v.detail.get("error") or "") for v in hits)
    assert calls_log.read_text() == "xx", "a transient timeout must retry exactly once"


# --------------------------------------------------------------- K7: env scrub filter
def test_scrubbed_env_filters_git_and_python_keeps_path(monkeypatch):
    """The subprocess env scrub removes GIT_* / PYTHON* (steering vectors) but keeps PATH."""
    from engines.io.gitio import _scrubbed_env

    monkeypatch.setenv("GIT_DIR", "/tmp/evil")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/evil.cfg")
    monkeypatch.setenv("PYTHONPATH", "/tmp/inject")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    env = _scrubbed_env()
    assert "GIT_DIR" not in env
    assert "GIT_CONFIG_GLOBAL" not in env
    assert "PYTHONPATH" not in env
    assert env.get("PATH") == "/usr/bin:/bin"


# ----------------------------------------------------------- K4: origin default-branch
def test_diff_committed_via_origin_default_branch(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path
):
    """A worktree carrying only ``origin/main`` (no LOCAL main/master) still resolves a
    committed-diff baseline, so an out-of-scope COMMITTED change is caught (K4). With the
    old (main, master)-only candidate list the committed half would silently self-disable."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)  # commits the seed on local main

    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", str(bare)], check=True, capture_output=True, text=True
    )
    _git(temp_uacp_root, "remote", "add", "origin", str(bare))
    _git(temp_uacp_root, "push", "-q", "origin", "main")
    _git(temp_uacp_root, "checkout", "-q", "-b", "run-branch")
    _git(temp_uacp_root, "branch", "-D", "main")  # only origin/main resolves now

    (temp_uacp_root / "rogue.py").write_text("# committed out-of-scope\n")
    _git(temp_uacp_root, "add", "rogue.py")
    _git(temp_uacp_root, "commit", "-q", "-m", "rogue", "--no-verify")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE via origin/main baseline, got {_codes(violations)}"
    assert any("rogue.py" in v.message for v in hits), [v.message for v in hits]


def test_diff_glob_write_path_constrains_suffix(temp_uacp_root: Path, valid_run_id: str):
    """P2 review: 'docs/*.md' must NOT become 'everything under docs/'. A .py
    written under a *.md glob is out of scope; the matching .md is not."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["docs/*.md"])
    _init_git_repo(temp_uacp_root)
    # temp root already has a docs/ dir from the fixture; write into it
    (temp_uacp_root / "docs" / "ok.md").write_text("# in-scope\n")
    (temp_uacp_root / "docs" / "rogue.py").write_text("# glob-dodging write\n")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE for docs/rogue.py, got {_codes(violations)}"
    assert any("docs/rogue.py" in v.message for v in hits), [v.message for v in hits]
    assert not any("ok.md" in v.message for v in hits), [v.message for v in hits]


def test_witness_cli_workspace_resident_argument_rejected(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """P1 review: a launcher-style config (safe interpreter + workspace-resident
    script argument) must be rejected — screening argv[0] alone lets
    'python <workspace>/evil.py' smuggle a run-mutable witness through the tail."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    evil = temp_uacp_root / "evil.py"
    evil.write_text("print('{}')\n")
    _configure_witness_cli(monkeypatch, tmp_path, f"{_stub_cli(evil).split(' ', 1)[0]} {evil}")
    clear_witness_memo()

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_WITNESS_UNAVAILABLE, got {_codes(violations)}"
    assert any("run workspace" in v.message for v in hits), [v.message for v in hits]


def test_diff_gate_owned_cache_dir_exempt(temp_uacp_root: Path, valid_run_id: str):
    """Post-merge P2: on a repo that does NOT gitignore .codeflair/, the gate must
    not flag its own witness index cache as an out-of-scope write."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    cache = temp_uacp_root / ".codeflair"
    cache.mkdir()
    (cache / "index.db").write_text("sqlite-bytes-stand-in")

    assert _diff_codes(validate(temp_uacp_root, valid_run_id)) == set()


def test_diff_symlink_escaping_workspace_is_flagged(temp_uacp_root: Path, valid_run_id: str):
    """Post-merge P2: a git-reported change that resolves OUTSIDE the workspace
    (symlink out) is an escape and must be flagged, never silently skipped."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue-link").symlink_to("/tmp")

    violations = validate(temp_uacp_root, valid_run_id)
    hits = [v for v in violations if v.code == "SC_DIFF_OUT_OF_SCOPE"]
    assert hits, f"expected SC_DIFF_OUT_OF_SCOPE for the escaping symlink, got {_codes(violations)}"
    assert any("rogue-link" in v.message for v in hits), [v.message for v in hits]


def test_witness_subprocess_cwd_is_not_the_workspace(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """Post-merge P1: launcher witnesses resolve modules/projects from cwd; the
    exec must pin a neutral cwd, never inherit one inside the run workspace."""
    import os as _os

    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    _init_git_repo(temp_uacp_root)
    cwd_probe = tmp_path / "cwd.txt"
    probe = tmp_path / "cwd_probe.py"
    probe.write_text(
        "import os, sys, pathlib\n"
        f"pathlib.Path({str(cwd_probe)!r}).write_text(os.getcwd())\n"
        "print('not json')\n"
    )
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(probe))
    clear_witness_memo()

    monkeypatch.chdir(temp_uacp_root)  # simulate a validator running inside the workspace
    validate(temp_uacp_root, valid_run_id)
    recorded = cwd_probe.read_text().strip()
    assert _os.path.realpath(recorded) != _os.path.realpath(str(temp_uacp_root)), recorded


# ============================================================================
# PREVENTION-at-PLAN forecast (design node 04) — the plan_exit hop-1 forecast vs the
# declared boundary, its gate-owned record, and the closure join. Driven through the SAME
# stub-CLI harness (a stub selecting a baseline vs diff account by the --baseline-refs flag)
# so the FAITHFUL trust-root / envelope path is exercised end to end.
# ============================================================================

from engines.graph_projection import validate_graph_invariants  # noqa: E402
from engines.io import load_forecast_record  # noqa: E402
from engines.scope_conformance import validate_cascade_forecast  # noqa: E402

# A stub that returns baseline.json when invoked with --baseline-refs, else witness.json —
# so ONE configured CLI answers both the forecast (plan_exit) and the diff-mode witness.
_DUAL_STUB_SRC = (
    "import pathlib, sys\n"
    "here = pathlib.Path(__file__).resolve().parent\n"
    "with (here / 'calls.log').open('a') as _f:\n"
    "    _f.write('x')\n"
    "name = 'baseline.json' if '--baseline-refs' in sys.argv else 'witness.json'\n"
    "sys.stdout.write((here / name).read_text())\n"
)


def _baseline_fixture(
    *,
    ingestion: str = "scip",
    declared: list[dict] | None = None,
    neighborhood: list[dict] | None = None,
    workspace_dirty: bool = False,
) -> dict:
    return {
        "mode": "baseline_refs",
        "graph_stamp": {"commit": "deadbeef", "tree_token": "deadbeef"},
        "ingestion": ingestion,
        "declared": declared or [],
        "neighborhood": neighborhood or [],
        "inbound_counts": {},
        "workspace_dirty": workspace_dirty,
    }


def _install_baseline_stub(stub_dir: Path, baseline: dict) -> tuple[Path, Path]:
    """A stub whose single fixture.json is the BASELINE account (the --baseline-refs flag is
    ignored — the forecast is the only caller). Returns (stub_py, calls_log)."""
    return _install_stub(stub_dir, baseline)


def _install_dual_stub(stub_dir: Path, baseline: dict, witness: dict) -> tuple[Path, Path]:
    """A stub that answers baseline vs diff-mode by argv. Returns (stub_py, calls_log)."""
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_py = stub_dir / "stub.py"
    stub_py.write_text(_DUAL_STUB_SRC)
    (stub_dir / "baseline.json").write_text(json.dumps(baseline))
    (stub_dir / "witness.json").write_text(json.dumps(witness))
    return stub_py, stub_dir / "calls.log"


def _forecast_record(root: Path, run_id: str) -> dict | None:
    rec, err = load_forecast_record(root, run_id)
    assert err is None, err
    return rec


# (a) forecast fires listing the out-of-boundary neighbor file; the declared refs' OWN
#     files are carved out (even when that file is itself outside the boundary).
def test_forecast_fires_on_out_of_boundary_neighbor(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "pkg/core.py", "name": "Core"}])
    baseline = _baseline_fixture(
        declared=[_decl("pkg/core.py", "Core", True)],
        neighborhood=[
            # Beta lives in rogue.py -> OUTSIDE src/** -> predicted.
            _edge(("pkg/core.py", "Core"), ("rogue.py", "Beta")),
            # Self2 lives in the DECLARED ref's own file -> carved out (even though pkg/ is
            # itself outside the src/** boundary).
            _edge(("pkg/core.py", "Core"), ("pkg/core.py", "Self2")),
        ],
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    hits = [
        v
        for v in validate_cascade_forecast(temp_uacp_root, valid_run_id)
        if v.code == "SC_PLAN_CASCADE_FORECAST"
    ]
    assert hits, "expected SC_PLAN_CASCADE_FORECAST"
    assert all(v.severity == "warn" for v in hits)
    files = hits[0].detail["files"]
    assert "rogue.py" in files, files
    assert "pkg/core.py" not in files, ("declared ref's own file must be carved out", files)

    # The forecast of record is written with predicted == the fired set.
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec["forecast_of_record"] is True
    assert rec["predicted"] == ["rogue.py"]
    assert rec["boundary"] == ["src/**"]


# (a2) the plan_exit forced-gate branch actually invokes the forecast (wiring proof).
def test_forecast_wired_into_plan_exit_forced_gate(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    codes = {v.code for v in validate_graph_invariants(temp_uacp_root, valid_run_id, "plan_exit")}
    assert "SC_PLAN_CASCADE_FORECAST" in codes, codes


# (b) missing EITHER declaration -> no-op, and the CLI is NEVER invoked.
def test_forecast_noop_without_write_paths_never_invokes_cli(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    # UNDECLARED write_paths (key absent) -> no boundary declared -> no-op. Distinct from
    # declared-EMPTY ([], the strictest valid boundary) — see the test below (codex P2).
    seed_coherent_run(temp_uacp_root, valid_run_id)
    body = _load_scope(temp_uacp_root, valid_run_id)
    body.pop("write_paths", None)
    _write_scope(temp_uacp_root, valid_run_id, body)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(declared=[_decl("src/a.py", "Alpha", True)])
    stub_py, calls_log = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert out == [], out
    assert not calls_log.exists(), "undeclared write_paths -> witness must not be invoked"
    assert _forecast_record(temp_uacp_root, valid_run_id) is None


def test_forecast_runs_against_declared_empty_boundary(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    # codex P2: write_paths: [] is a VALID declaration (the strictest boundary — the run
    # writes nothing outside the permitted surfaces), exactly as diff-containment treats
    # it. The forecast must RUN against it: every out-of-carve-out hop-1 neighbor file is
    # out-of-boundary.
    seed_coherent_run(temp_uacp_root, valid_run_id)  # write_paths == [] (declared empty)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("elsewhere.py", "Beta"))],
    )
    stub_py, calls_log = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert calls_log.exists(), "declared-empty boundary must still derive the forecast"
    hits = [v for v in out if v.code == "SC_PLAN_CASCADE_FORECAST"]
    assert hits, f"expected SC_PLAN_CASCADE_FORECAST, got {_codes(out)}"
    assert any("elsewhere.py" in v.message for v in hits)
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec["predicted"] == ["elsewhere.py"]


def test_forecast_noop_without_code_refs_never_invokes_cli(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])  # but no code_refs
    baseline = _baseline_fixture()
    stub_py, calls_log = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert out == [], out
    assert not calls_log.exists(), "no code_refs -> witness must not be invoked"


# (c) a dirty tree is flagged in the advisory detail AND the record.
def test_forecast_workspace_dirty_flagged(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
        workspace_dirty=True,
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    hits = [
        v
        for v in validate_cascade_forecast(temp_uacp_root, valid_run_id)
        if v.code == "SC_PLAN_CASCADE_FORECAST"
    ]
    assert hits
    assert hits[0].detail["workspace_dirty"] is True
    assert "dirty" in hits[0].message
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec["workspace_dirty"] is True


# (d) a retried plan_exit attempt OVERWRITES the record (last-write-wins = forecast of
#     record is the successful transition's write). No git -> no memo -> each call derives.
def test_forecast_record_last_write_wins_on_retry(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    stub_dir = tmp_path / "cf"

    # First attempt predicts rogue1.py.
    _install_baseline_stub(
        stub_dir,
        _baseline_fixture(
            declared=[_decl("src/a.py", "Alpha", True)],
            neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue1.py", "B1"))],
        ),
    )
    stub_py = stub_dir / "stub.py"
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id)["predicted"] == ["rogue1.py"]

    # Retried attempt now predicts rogue2.py — the record is OVERWRITTEN (last-write-wins).
    (stub_dir / "fixture.json").write_text(
        json.dumps(
            _baseline_fixture(
                declared=[_decl("src/a.py", "Alpha", True)],
                neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue2.py", "B2"))],
            )
        )
    )
    clear_witness_memo()
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id)["predicted"] == ["rogue2.py"]


# (e) closure join: a non-empty predicted ∩ actual appends outcome/precision/recall.
def test_forecast_closure_join_non_empty_pair(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],  # predicts rogue.py
    )
    # A clean diff-mode account so validate()'s cascade witness stays quiet.
    witness = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, _ = _install_dual_stub(tmp_path / "cf", baseline, witness)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    # 1) plan_exit forecast writes predicted == [rogue.py].
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id)["predicted"] == ["rogue.py"]

    # 2) the ACTUAL out-of-scope change lands. The registered ENGINE stays read-only
    # (codex P2): validate() must NOT touch the record; the CLOSURE GATE joins.
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue.py").write_text("# out of scope, exactly as forecast\n")
    validate(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id).get("joined") is None
    from engines.scope_conformance import join_forecast_record

    assert join_forecast_record(temp_uacp_root, valid_run_id) == []

    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec.get("joined") is True
    assert rec["outcome"] == ["rogue.py"]
    assert rec["intersection"] == ["rogue.py"]
    assert rec["precision"] == 1.0
    assert rec["recall"] == 1.0


# (e2) an EMPTY forecast -> precision null and NO false pair (recall over the outcome).
def test_forecast_closure_join_empty_forecast_precision_null(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[],  # no neighbors -> empty forecast
    )
    witness = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, _ = _install_dual_stub(tmp_path / "cf", baseline, witness)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id)["predicted"] == []

    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue.py").write_text("# an actual out-of-scope change\n")
    from engines.scope_conformance import join_forecast_record

    assert join_forecast_record(temp_uacp_root, valid_run_id) == []

    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec.get("joined") is True
    assert rec["precision"] is None, "empty forecast -> precision null (no false pair)"
    assert rec["recall"] == 0.0  # forecast caught none of the one real offender
    assert rec["intersection"] == []


# (f) witness unavailable -> visible warn, and NO record is written.
def test_forecast_unavailable_is_visible_and_writes_no_record(
    temp_uacp_root: Path, valid_run_id: str
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    # No [witness] configured -> unconfigured -> unavailable.

    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    hits = [v for v in out if v.code == "SC_FORECAST_WITNESS_UNAVAILABLE"]
    assert hits, f"expected SC_FORECAST_WITNESS_UNAVAILABLE, got {_codes(out)}"
    assert all(v.severity == "warn" for v in hits)
    # K4: the forecast layer's own code, DISTINCT from the verify-time SC_WITNESS_UNAVAILABLE.
    assert "SC_WITNESS_UNAVAILABLE" not in _codes(out)
    assert _forecast_record(temp_uacp_root, valid_run_id) is None, "no record on unavailable"


def test_forecast_weak_provenance_floor_is_unavailable_no_record(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        ingestion="treesitter",  # weaker than scip
        declared=[_decl("src/a.py", "Alpha", True)],
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert "SC_FORECAST_WITNESS_UNAVAILABLE" in {v.code for v in out}
    assert _forecast_record(temp_uacp_root, valid_run_id) is None


# (h) a malformed forecast record -> SC_FORECAST_JOIN_FAILED at closure, never a crash.
def test_forecast_join_malformed_record_is_flagged(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    # Plant a malformed forecast record (predicted is not a list).
    rec_path = temp_uacp_root / ".uacp" / "verification" / f"{valid_run_id}-cascade-forecast.yaml"
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(yaml.safe_dump({"run_id": valid_run_id, "predicted": "not-a-list"}))

    from engines.scope_conformance import join_forecast_record

    out = join_forecast_record(temp_uacp_root, valid_run_id)
    hits = [v for v in out if v.code == "SC_FORECAST_JOIN_FAILED"]
    assert hits, f"expected SC_FORECAST_JOIN_FAILED, got {_codes(out)}"
    assert all(v.severity == "warn" for v in hits)


def test_forecast_join_unreadable_record_is_flagged(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    rec_path = temp_uacp_root / ".uacp" / "verification" / f"{valid_run_id}-cascade-forecast.yaml"
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text("this: : : not valid yaml: [")

    from engines.scope_conformance import join_forecast_record

    out = join_forecast_record(temp_uacp_root, valid_run_id)
    assert "SC_FORECAST_JOIN_FAILED" in {v.code for v in out}


# (g-lock) no forecast record -> the closure join is a silent no-op (no SC_FORECAST_* noise).
def test_forecast_join_noop_without_record(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _init_git_repo(temp_uacp_root)
    out = validate(temp_uacp_root, valid_run_id)
    assert not any(v.code.startswith("SC_FORECAST") for v in out)


# (memo) the baseline memo keys on HEAD sha — an unchanged HEAD reuses the derivation, and
# a changed claim re-derives; the key never collides with the diff-mode memo.
def test_baseline_memo_reuse_and_reclaim(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    from engines.io import BaselineFacts, derive_baseline_neighborhood, derive_witness

    seed_coherent_run(temp_uacp_root, valid_run_id)
    baseline = _baseline_fixture(declared=[_decl("src/a.py", "Alpha", True)])
    witness = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)], symbols_touched=[("src/a.py", "Alpha")]
    )
    stub_py, calls_log = _install_dual_stub(tmp_path / "cf", baseline, witness)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    _init_git_repo(temp_uacp_root)  # HEAD sha stable across the calls below

    refs_a = [{"file": "src/a.py", "name": "Alpha"}]
    refs_b = [{"file": "src/b.py", "name": "Beta"}]
    r1 = derive_baseline_neighborhood(temp_uacp_root, refs_a)  # exec (1)
    derive_baseline_neighborhood(temp_uacp_root, refs_a)  # memo hit
    derive_baseline_neighborhood(temp_uacp_root, refs_b)  # changed claim -> exec (2)
    assert r1.available and isinstance(r1.facts, BaselineFacts)
    assert calls_log.read_text() == "xx", (
        "baseline memo: reuse on same HEAD+claim, re-derive on new claim"
    )

    # The diff-mode memo is SEPARATE — a diff derivation for the same refs execs again (3),
    # proving no cross-mode collision.
    derive_witness(temp_uacp_root, refs_a)
    assert calls_log.read_text() == "xxx", (
        "diff-mode derivation must not collide with the baseline memo"
    )


def _git_head(root: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


# (K1) stale-dirty flag: a memo HIT recomputes workspace_dirty kernel-side, so a
# clean->dirty transition at the same HEAD is reflected even though the cached account said
# clean (the stub always reports workspace_dirty=False).
def test_forecast_memo_hit_recomputes_workspace_dirty(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
        workspace_dirty=False,  # the stub ALWAYS reports clean
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    clear_witness_memo()
    _init_git_repo(temp_uacp_root)  # clean tree, HEAD stable across the two calls below

    # (1) derive on a CLEAN tree -> record clean, memo populated on HEAD.
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id)["workspace_dirty"] is False

    # (2) dirty the tree (new untracked file), derive again -> MEMO HIT, but the kernel
    # recomputes workspace_dirty fresh -> True in BOTH the record and the advisory.
    (temp_uacp_root / "rogue.py").write_text("# now the tree is dirty\n")
    hits = [
        v
        for v in validate_cascade_forecast(temp_uacp_root, valid_run_id)
        if v.code == "SC_PLAN_CASCADE_FORECAST"
    ]
    assert hits, "forecast still fires (rogue.py neighbor is out of boundary)"
    assert hits[0].detail["workspace_dirty"] is True, "memo-hit must serve FRESH dirtiness"
    assert "dirty" in hits[0].message
    assert _forecast_record(temp_uacp_root, valid_run_id)["workspace_dirty"] is True


# (K1b) the kernel-side dirty recompute FILTERS the witness's own .codeflair/ index cache —
# churn confined to .codeflair/ is NOT run dirtiness.
def test_forecast_workspace_dirty_filters_codeflair_cache(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
        workspace_dirty=True,  # stub claims dirty; the kernel recompute overrides it
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    clear_witness_memo()
    _init_git_repo(temp_uacp_root)  # clean tree
    # ONLY .codeflair/ churn -> must be filtered out -> tree reads CLEAN kernel-side.
    (temp_uacp_root / ".codeflair").mkdir()
    (temp_uacp_root / ".codeflair" / "index.db").write_text("cache\n")

    hits = [
        v
        for v in validate_cascade_forecast(temp_uacp_root, valid_run_id)
        if v.code == "SC_PLAN_CASCADE_FORECAST"
    ]
    assert hits
    assert hits[0].detail["workspace_dirty"] is False, ".codeflair/ churn is not dirtiness"
    assert "dirty" not in hits[0].message


# (K2) an atomic-write FAILURE surfaces as SC_FORECAST_WRITE_FAILED (warn), never a silent
# drop — and does not suppress the forecast advisory itself.
def test_forecast_write_failure_is_visible(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
    )
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))

    from engines import scope_conformance as sc

    monkeypatch.setattr(sc, "write_forecast_record", lambda *a, **k: False)
    out = validate_cascade_forecast(temp_uacp_root, valid_run_id)
    codes = {v.code for v in out}
    assert "SC_FORECAST_WRITE_FAILED" in codes, codes
    assert "SC_PLAN_CASCADE_FORECAST" in codes, "the forecast advisory still fires"
    assert all(v.severity == "warn" for v in out if v.code == "SC_FORECAST_WRITE_FAILED")


# (K3) the record carries base_commit = merge-base(default branch, HEAD) AND the declared-ref
# resolution echo; when HEAD advanced past the branch point, base_commit != graph_stamp.commit
# (the commit-early hindsight audit signature).
def test_forecast_record_carries_base_commit_and_declared_echo(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])

    # main holds the fork point; HEAD advances onto a feature branch beyond it.
    _init_git_repo(temp_uacp_root)  # commit C0 on main
    fork_point = _git_head(temp_uacp_root)
    _git(temp_uacp_root, "checkout", "-q", "-b", "feature")
    (temp_uacp_root / "advance.txt").write_text("beyond the fork\n")
    _git(temp_uacp_root, "add", "-A")
    _git(temp_uacp_root, "commit", "-q", "-m", "advance", "--no-verify")
    head = _git_head(temp_uacp_root)
    assert head != fork_point

    # Pin the stub's graph_stamp.commit to the REAL HEAD so the audit compare is meaningful
    # (base_commit is the fork point, graph_stamp.commit is the advanced HEAD).
    baseline = _baseline_fixture(
        declared=[
            _decl("src/a.py", "Alpha", True),
            _decl("src/a.py", "Ghost", False),  # phantom ref -> resolved False, now VISIBLE
        ],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
    )
    baseline["graph_stamp"] = {"commit": head, "tree_token": head}
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    clear_witness_memo()

    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None
    assert rec["base_commit"] == fork_point, "base_commit is merge-base(main, HEAD)"
    assert rec["base_commit"] != rec["graph_stamp"]["commit"], (
        "HEAD advanced past the fork -> the commit-early hindsight signature"
    )
    echo = {(d["file"], d["name"]): d["resolved"] for d in rec["declared"]}
    assert echo[("src/a.py", "Alpha")] is True
    assert echo[("src/a.py", "Ghost")] is False, "phantom ref is echoed, not swallowed"


def test_forecast_join_absent_write_paths_matches_engine_boundary(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """Post-merge review P2: the join's boundary loading mirrors the engine path —
    ABSENT write_paths normalizes to [] (the strict empty boundary diff-containment
    evaluates), so an existing record is still joined, never silently skipped."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(declared=[_decl("src/a.py", "Alpha", True)], neighborhood=[])
    stub_py, _ = _install_baseline_stub(tmp_path / "cf", baseline)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    assert _forecast_record(temp_uacp_root, valid_run_id) is not None

    # The final scope loses its write_paths key entirely (absent, not []).
    body = _load_scope(temp_uacp_root, valid_run_id)
    body.pop("write_paths", None)
    _write_scope(temp_uacp_root, valid_run_id, body)
    reg = _load_registry(temp_uacp_root)
    reg["active_runs"][0]["write_paths"] = []
    _write_registry(temp_uacp_root, reg)
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue.py").write_text("# out of the empty boundary\n")

    from engines.scope_conformance import join_forecast_record

    assert join_forecast_record(temp_uacp_root, valid_run_id) == []
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec.get("joined") is True, "absent boundary must still join"
    assert "rogue.py" in rec["outcome"]


def test_heartgate_closure_gate_performs_the_join(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """Post-merge review coverage gap: prove validate_closure ITSELF joins (and
    surfaces join failures) — not just the helper called directly."""
    from engines.heartgate.heartgate import Heartgate

    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    _set_code_refs(temp_uacp_root, valid_run_id, [{"file": "src/a.py", "name": "Alpha"}])
    baseline = _baseline_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        neighborhood=[_edge(("src/a.py", "Alpha"), ("rogue.py", "Beta"))],
    )
    witness = _witness_fixture(
        declared=[_decl("src/a.py", "Alpha", True)],
        symbols_touched=[("src/a.py", "Alpha")],
    )
    stub_py, _ = _install_dual_stub(tmp_path / "cf", baseline, witness)
    _configure_witness_cli(monkeypatch, tmp_path, _stub_cli(stub_py))
    validate_cascade_forecast(temp_uacp_root, valid_run_id)
    _init_git_repo(temp_uacp_root)
    (temp_uacp_root / "rogue.py").write_text("# actual out-of-scope\n")

    decision = Heartgate.load(str(temp_uacp_root)).validate_closure(valid_run_id)
    rec = _forecast_record(temp_uacp_root, valid_run_id)
    assert rec is not None and rec.get("joined") is True, "the closure GATE must join"
    assert rec["precision"] == 1.0
    assert decision.decision in ("pass", "warn", "block")  # gate never crashes

    # Failure surfacing: corrupt the record, re-run the gate, the warning is visible.
    rec_path = temp_uacp_root / ".uacp" / "verification" / f"{valid_run_id}-cascade-forecast.yaml"
    rec_path.write_text("this: : : not valid yaml: [")
    decision2 = Heartgate.load(str(temp_uacp_root)).validate_closure(valid_run_id)
    all_lines = list(decision2.blockers) + list(decision2.warnings)
    assert any("SC_FORECAST_JOIN_FAILED" in ln for ln in all_lines), all_lines


def test_join_persistence_failure_is_visible(
    temp_uacp_root: Path, valid_run_id: str, tmp_path: Path, monkeypatch
):
    """PR #94 post-merge review: a computed-but-unpersisted closure join must fire
    SC_FORECAST_WRITE_FAILED, never silently starve the promotion corpus."""
    seed_coherent_run(temp_uacp_root, valid_run_id)
    _declare_write_paths(temp_uacp_root, valid_run_id, ["src/**"])
    rec_path = temp_uacp_root / ".uacp" / "verification" / f"{valid_run_id}-cascade-forecast.yaml"
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(yaml.safe_dump({"run_id": valid_run_id, "predicted": []}))
    _init_git_repo(temp_uacp_root)

    from engines import scope_conformance as _sc

    monkeypatch.setattr(_sc, "write_forecast_record", lambda *a, **k: False)
    out = _sc.join_forecast_record(temp_uacp_root, valid_run_id)
    hits = [v for v in out if v.code == "SC_FORECAST_WRITE_FAILED"]
    assert hits, f"expected SC_FORECAST_WRITE_FAILED, got {_codes(out)}"
    assert all(v.severity == "warn" for v in hits)

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

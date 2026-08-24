"""Unit tests for the Layer 2 correctness-screening FLOOR (design/grounded-governance/03).

``validate_correctness_screening`` makes a correctness screening non-skippable, grounded, and
fixpoint-enforced: when the git witness shows the run changed CODE, VERIFY may not clear unless a
correctness-screening artifact EXISTS, RESOLVES, and COVERS the kernel-produced substrate
(``gitio.diff_content`` over ``merge-base..HEAD``). The substrate identity is a sha256 over the
base + HEAD + diff text, so any fix that moves HEAD makes a prior screening STALE — the fixpoint.

Fixtures use a REAL git-init'd tmp repo for the fire paths (base commit on ``main``, the change on
a feature branch that is HEAD, so there is a real merge-base and a real diff) plus a minimal
projectable ``.uacp`` workspace, mirroring ``test_behavioral_floor.py``.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import yaml

from engines.graph_projection import (
    validate_correctness_findings,
    validate_correctness_screening,
)
from engines.io import diff_content


# --------------------------------------------------------------------------- workspace fixture
def _ws(tmp_path: Path, run: str = "r") -> Path:
    """A minimal .uacp workspace with a registered run manifest (no screening artifact)."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "verification" / run).mkdir(parents=True)
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": {}})
    )
    return tmp_path


def _write_screening(tmp_path: Path, run: str, substrate_hash: str, name: str = "screening") -> None:
    """Place a lenient correctness-screening artifact under verification/{run}/ (slice 3 will add
    the governed writer + schema; this gate loads leniently, keying on kind + substrate_hash)."""
    p = tmp_path / ".uacp" / "verification" / run / f"{name}.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.correctness_screening",
                "run_id": run,
                "substrate_hash": substrate_hash,
            }
        )
    )


# --------------------------------------------------------------------------- git fixture
def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, rel: str, body: str, msg: str) -> None:
    f = path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    _git(path, "add", rel)
    _git(path, "commit", "-q", "-m", msg)


def _code_change_repo(ws: Path, head_body: str = "def x():\n    return 999\n") -> None:
    """A repo whose HEAD (feature) is one CODE change ahead of the default branch (main), so the
    correctness gate sees code changed AND a real merge-base/diff substrate exists."""
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "main")
    _commit(ws, "src/mod.py", "def x():\n    return 1\n", "base")
    _git(ws, "checkout", "-q", "-b", "feature")
    _commit(ws, "src/mod.py", head_body, "change")


def _current_hash(ws: Path) -> str:
    dc = diff_content(Path(ws))
    payload = f"{dc.base_commit or ''}\n{dc.head_commit or ''}\n{dc.text}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _codes(vs: list) -> list[str]:
    return [v.code for v in vs]


# =========================================================================== tests
def test_non_git_dir_is_noop(tmp_path):
    # No git witness / no substrate -> [] (synthetic fixtures).
    ws = _ws(tmp_path)
    assert validate_correctness_screening(ws, "r") == []


def test_code_change_without_screening_fires_missing_warn(tmp_path):
    # Code changed and NO screening artifact -> exactly one CHK_CORRECTNESS_SCREENING_MISSING at
    # the default severity (warn).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["code_changed"] == 1
    assert vs[0].detail["substrate_hash"] == _current_hash(ws)


def test_matching_screening_passes(tmp_path):
    # A screening whose substrate_hash matches the CURRENT diff covers it -> [] (non-vacuity: the
    # SAME fixture without the artifact fires MISSING, per the test above).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    _write_screening(tmp_path, "r", _current_hash(ws))
    assert validate_correctness_screening(ws, "r") == []


def test_stale_screening_fires_stale(tmp_path):
    # A screening built for an OLD diff, then HEAD advances -> the old hash no longer covers ->
    # CHK_CORRECTNESS_SCREENING_STALE (the fixpoint: re-screen the moved delta).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    stale = _current_hash(ws)
    _write_screening(tmp_path, "r", stale)
    # HEAD advances (a fix moves the diff) — the screening's hash is now stale.
    _commit(ws, "src/mod.py", "def x():\n    return 12345\n", "fix")
    assert _current_hash(ws) != stale  # the substrate identity moved
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_STALE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert stale in vs[0].detail["found_hashes"]


def test_docs_only_change_is_exempt(tmp_path):
    # Only docs changed (no code suffix in the change set) -> no screening obligation -> [].
    ws = _ws(tmp_path)
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "main")
    _commit(ws, "README.md", "# base\n", "base")
    _git(ws, "checkout", "-q", "-b", "feature")
    _commit(ws, "docs/note.md", "just docs\n", "change")
    assert validate_correctness_screening(ws, "r") == []


def test_config_block_flips_severity(tmp_path):
    # [verification] correctness_screening = "block" -> the MISSING fire is severity block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text(
        '[verification]\ncorrectness_screening = "block"\n'
    )
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "block"


def test_config_garbage_falls_back_to_warn(tmp_path):
    # A non-{warn,block} value is fail-closed to the SAFE migration default (warn), never block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text(
        '[verification]\ncorrectness_screening = "loud"\n'
    )
    _code_change_repo(ws)
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"


def test_no_merge_base_reports_substrate_unavailable(tmp_path):
    # Code changed but NO default-branch merge-base (only a uniquely-named branch) -> the substrate
    # cannot be produced -> CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE, ALWAYS warn (env fact).
    # The witness sees code via a STAGED (uncommitted) change; HEAD still resolves (base commit),
    # but with no main/master/origin there is no merge-base for diff_content to precipitate.
    ws = _ws(tmp_path)
    _init(ws)
    _git(ws, "checkout", "-q", "-b", "topic-only")
    _commit(ws, "src/mod.py", "def x():\n    return 1\n", "base")
    (ws / "src" / "mod.py").write_text("def x():\n    return 2\n")
    _git(ws, "add", "src/mod.py")
    vs = validate_correctness_screening(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SUBSTRATE_UNAVAILABLE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["error"] == "no merge-base"


# =========================================================================== slice 4: findings gate
def _write_verdict_screening(
    tmp_path: Path,
    run: str,
    substrate_hash: str,
    verdict: str,
    findings: list[dict],
    name: str = "screening",
) -> None:
    """A COVERING correctness-screening artifact carrying a real verdict + findings, under
    verification/{run}/ (the subdir the gate scans + the governed writer's home)."""
    p = tmp_path / ".uacp" / "verification" / run / f"{name}.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.correctness_screening",
                "run_id": run,
                "substrate_hash": substrate_hash,
                "reviewed_range": {"base_commit": "b", "head_commit": "h"},
                "verdict": verdict,
                "findings": findings,
                "screener": {"model": "test-model", "independence_evidence": None},
            }
        )
    )


def _write_fix_artifact(tmp_path: Path, run: str, name: str = "fix") -> str:
    """A run-bound fix artifact under verification/{run}/ that EXISTS + LOADS (so M2's
    _artifact_resolves accepts it). Returns its base-relative path."""
    rel = f"verification/{run}/{name}.yaml"
    (tmp_path / ".uacp" / rel).write_text(yaml.safe_dump({"kind": "uacp.fix", "run_id": run}))
    return rel


def test_findings_gate_noop_without_covering_screening(tmp_path):
    # Code changed, NO screening at all -> the findings gate stays silent (MISSING is the
    # slice-2 floor's job; the findings gate must not double-report).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    assert validate_correctness_findings(ws, "r") == []


def test_clean_verdict_no_findings_block(tmp_path):
    # A COVERING screening with verdict=clean and no findings -> [].
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "clean", [])
    assert validate_correctness_findings(ws, "r") == []


def test_discharged_finding_with_resolving_artifact_clears(tmp_path):
    # verdict=findings, one discharged finding whose handling_artifact_path RESOLVES (run-bound +
    # exists) -> no undispositioned block. Non-vacuity: the nonexistent-path test below fires.
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    fix_rel = _write_fix_artifact(tmp_path, "r")
    finding = {
        "id": "F1",
        "severity": "P1",
        "defect_class": "logic",
        "message": "off-by-one",
        "substrate_ref": "src/mod.py:2",
        "repro": "call x()",
        "disposition": {"kind": "discharged", "handling_artifact_path": fix_rel},
    }
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "findings", [finding])
    assert validate_correctness_findings(ws, "r") == []


def test_discharged_finding_with_nonexistent_artifact_blocks(tmp_path):
    # A discharged finding naming a NONEXISTENT fix path is a label, not a fix -> one
    # CHK_CORRECTNESS_FINDING_UNDISPOSITIONED.
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    finding = {
        "id": "F1",
        "severity": "P1",
        "defect_class": "logic",
        "message": "off-by-one",
        "substrate_ref": "src/mod.py:2",
        "repro": "call x()",
        "disposition": {
            "kind": "discharged",
            "handling_artifact_path": "verification/r/does-not-exist.yaml",
        },
    }
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "findings", [finding])
    vs = validate_correctness_findings(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["finding_id"] == "F1"


def test_adjudicated_finding_missing_cost_blocks(tmp_path):
    # An adjudicated finding missing cost_if_wrong is a partial adjudication -> block (per finding).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    finding = {
        "id": "F2",
        "severity": "P2",
        "defect_class": "style",
        "message": "naming",
        "substrate_ref": "src/mod.py:1",
        "repro": "n/a",
        "disposition": {
            "kind": "adjudicated",
            "decision": "accept",
            "rationale": "cosmetic",
            # cost_if_wrong omitted -> incomplete
        },
    }
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "findings", [finding])
    vs = validate_correctness_findings(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].detail["finding_id"] == "F2"


def test_adjudicated_finding_complete_clears(tmp_path):
    # A complete adjudication (decision + rationale + cost_if_wrong) clears -> [] (non-vacuity vs
    # the missing-cost test above).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    finding = {
        "id": "F2",
        "severity": "P2",
        "defect_class": "style",
        "message": "naming",
        "substrate_ref": "src/mod.py:1",
        "repro": "n/a",
        "disposition": {
            "kind": "adjudicated",
            "decision": "accept",
            "rationale": "cosmetic",
            "cost_if_wrong": "negligible",
        },
    }
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "findings", [finding])
    assert validate_correctness_findings(ws, "r") == []


def test_cannot_verify_verdict_surfaces_inconclusive_warn(tmp_path):
    # verdict=cannot_verify -> CHK_CORRECTNESS_SCREENING_INCONCLUSIVE at warn (abstained, never a
    # silent pass).
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "cannot_verify", [])
    vs = validate_correctness_findings(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_SCREENING_INCONCLUSIVE"], _codes(vs)
    assert vs[0].severity == "warn"


def test_findings_gate_config_block_flips_severity(tmp_path):
    # [verification] correctness_screening = "block" -> the undispositioned finding fires at block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text(
        '[verification]\ncorrectness_screening = "block"\n'
    )
    _code_change_repo(ws)
    finding = {
        "id": "F1",
        "severity": "P1",
        "defect_class": "logic",
        "message": "bug",
        "substrate_ref": "src/mod.py:2",
        "repro": "call x()",
        "disposition": {"kind": "discharged", "handling_artifact_path": "verification/r/ghost.yaml"},
    }
    _write_verdict_screening(tmp_path, "r", _current_hash(ws), "findings", [finding])
    vs = validate_correctness_findings(ws, "r")
    assert _codes(vs) == ["CHK_CORRECTNESS_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "block"


def test_clean_verdict_carrying_findings_is_inconsistent(tmp_path):
    # Codex #172 P1: a `clean` verdict with a non-empty findings array must NOT clear — the label
    # cannot waive unresolved defects. Both the inconsistency AND the undispositioned finding fire.
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    h = _current_hash(ws)
    p = tmp_path / ".uacp" / "verification" / "r" / "screening.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.correctness_screening",
                "run_id": "r",
                "substrate_hash": h,
                "verdict": "clean",
                "findings": [{"id": "F1", "severity": "P1", "message": "leak", "disposition": None}],
            }
        )
    )
    codes = _codes(validate_correctness_findings(ws, "r"))
    assert "CHK_CORRECTNESS_SCREENING_INCONSISTENT" in codes, codes
    assert "CHK_CORRECTNESS_FINDING_UNDISPOSITIONED" in codes, codes


def test_discharge_pointing_at_the_screening_itself_is_self_attestation(tmp_path):
    # screening #172 P1: a "discharged" finding whose fix pointer is the SCREENING artifact itself
    # (or any review/declaration kind) is self-attestation, not a remediation -> undispositioned.
    ws = _ws(tmp_path)
    _code_change_repo(ws)
    h = _current_hash(ws)
    screening_rel = "verification/r/screening.yaml"
    p = tmp_path / ".uacp" / screening_rel
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.correctness_screening",
                "run_id": "r",
                "substrate_hash": h,
                "verdict": "findings",
                "findings": [
                    {
                        "id": "F1",
                        "severity": "P1",
                        "message": "leak",
                        # points at the screening under review -> self-attestation, run-bound + exists
                        "disposition": {"kind": "discharged", "handling_artifact_path": screening_rel},
                    }
                ],
            }
        )
    )
    assert "CHK_CORRECTNESS_FINDING_UNDISPOSITIONED" in _codes(validate_correctness_findings(ws, "r"))

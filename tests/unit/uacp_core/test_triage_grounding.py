"""Unit tests for the M2 TRIAGE grounding gate (design/grounded-governance/04 + 05).

The HEAD of the cascade. ``validate_triage_screening`` + ``validate_triage_findings`` make the
first governed declaration (the scope) non-skippable and grounded against the REAL project root the
scope names: when a run DECLARES scope targets at triage, TRIAGE may not clear clean unless every
declared target RESOLVES in the real tree AND a ``uacp.triage_screening`` artifact EXISTS, RESOLVES,
and COVERS the kernel-produced scope substrate (a sha256 over the sorted
``(target, exists, kind, size)`` tuples), with its findings dispositioned. Any change to the
declared scope OR to the tree it names moves the hash — the fixpoint.

This is the SAME machine as the VERIFY correctness screening; the only difference is the substrate
producer (declared scope targets vs a git diff), so these tests mirror
``test_correctness_screening.py``. Fixtures use a REAL tmp project tree (targets resolve against
``tmp_path``) plus a minimal projectable ``.uacp`` workspace.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from engines.graph_projection import (
    validate_triage_findings,
    validate_triage_screening,
)
from state_machine import _run_forced_triage_grounding_gate


# --------------------------------------------------------------------------- workspace fixture
def _ws(tmp_path: Path, run: str = "r") -> Path:
    """A minimal .uacp workspace with a registered run manifest (no triage/screening artifact)."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "proposals" / run).mkdir(parents=True)
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": {}})
    )
    return tmp_path


def _declare_scope(tmp_path: Path, run: str, targets: list[str]) -> None:
    """Write a uacp.triage artifact declaring scope targets (open-world `scope_targets`), under
    proposals/{run}-triage.yaml — where the gate reads the run's serialized scope."""
    p = tmp_path / ".uacp" / "proposals" / f"{run}-triage.yaml"
    p.write_text(yaml.safe_dump({"kind": "uacp.triage", "run_id": run, "scope_targets": targets}))


def _make_target(tmp_path: Path, rel: str, body: str = "x\n") -> None:
    """Create a REAL file under the project root (tmp_path) so a declared target resolves."""
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)


def _write_screening(
    tmp_path: Path,
    run: str,
    substrate_hash: str,
    *,
    verdict: str = "clean",
    findings: list[dict] | None = None,
    scope: list[str] | None = None,
    name: str = "triage-screening-0",
) -> None:
    """Place a triage-screening artifact under proposals/{run}/ (the subdir the gate scans + the
    governed writer's home). Loaded leniently by the gate (keys on kind + substrate_hash)."""
    p = tmp_path / ".uacp" / "proposals" / run / f"{name}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.triage_screening",
                "run_id": run,
                "substrate_hash": substrate_hash,
                "reviewed_scope": scope or ["src/mod.py"],
                "verdict": verdict,
                "findings": findings or [],
                "screener": {"model": "test-model", "independence_evidence": None},
            }
        )
    )


def _write_fix_artifact(tmp_path: Path, run: str, name: str = "fix") -> str:
    """A run-bound fix artifact under the TRIAGE evidence dir proposals/{run}/ that EXISTS + LOADS
    (so the phase-appropriate _artifact_resolves accepts it — a triage discharge lands under
    proposals/, the real governed-writer root, not the late-phase dirs). Returns its base-rel path."""
    rel = f"proposals/{run}/{name}.yaml"
    dest = tmp_path / ".uacp" / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml.safe_dump({"kind": "uacp.fix", "run_id": run}))
    return rel


def _expected_hash(root: Path, targets: list[str]) -> str:
    """Independent oracle for the substrate identity (mirrors _triage_substrate_hash's formula)."""
    base = root.resolve()
    rows = []
    for t in sorted(set(targets)):
        if any(ch in t for ch in "*?["):
            matches = list(base.glob(t))
            rows.append((t, bool(matches), "glob", len(matches)))
            continue
        p = base / t
        if p.is_dir():
            rows.append((t, True, "dir", 0))
        elif p.is_file():
            rows.append((t, True, "file", p.stat().st_size))
        else:
            rows.append((t, False, "", 0))
    payload = "\n".join(f"{t}\t{int(e)}\t{k}\t{s}" for (t, e, k, s) in rows)
    return hashlib.sha256(payload.encode()).hexdigest()


def _codes(vs: list) -> list[str]:
    return [v.code for v in vs]


# =========================================================================== floor + coverage
def test_no_declared_scope_is_noop(tmp_path):
    # A run that declares NO scope at triage has no substrate -> the gate no-ops (mirrors the
    # correctness floor's 'no code changed'). This is what preserves existing triage->propose runs.
    ws = _ws(tmp_path)
    assert validate_triage_screening(ws, "r") == []
    assert validate_triage_findings(ws, "r") == []


def test_resolving_scope_with_covering_clean_screening_passes(tmp_path):
    # Declared targets resolve + a screening whose substrate_hash matches the current substrate and
    # verdict=clean -> [] (non-vacuity: the same fixture without the screening fires MISSING below).
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets))
    assert validate_triage_screening(ws, "r") == []
    assert validate_triage_findings(ws, "r") == []


def test_nonexistent_target_fires_unresolved(tmp_path):
    # A declared target that resolves to nothing -> TRIAGE_SCOPE_TARGET_UNRESOLVED (the deterministic
    # floor, no agent needed). Here a COVERING screening is present, so MISSING/STALE do NOT fire —
    # isolating the floor: the unresolved-target block stands even when the scope was screened.
    ws = _ws(tmp_path)
    targets = ["src/ghost.py"]  # never created
    _declare_scope(tmp_path, "r", targets)
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets))
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCOPE_TARGET_UNRESOLVED"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["target"] == "src/ghost.py"


def test_resolving_scope_without_screening_fires_missing_warn(tmp_path):
    # Targets resolve but NO screening -> exactly one TRIAGE_SCREENING_MISSING at the default warn.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["declared_targets"] == 1
    assert vs[0].detail["substrate_hash"] == _expected_hash(tmp_path, targets)


def test_stale_screening_fires_stale(tmp_path):
    # A screening built for the OLD scope, then the scope changes (a target added) -> the old hash no
    # longer covers -> TRIAGE_SCREENING_STALE (the fixpoint: re-screen the moved scope).
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    old_targets = ["src/mod.py"]
    stale = _expected_hash(tmp_path, old_targets)
    _write_screening(tmp_path, "r", stale)
    # The declared scope now names a second target — the substrate identity moves.
    _make_target(tmp_path, "src/two.py")
    new_targets = ["src/mod.py", "src/two.py"]
    _declare_scope(tmp_path, "r", new_targets)
    assert _expected_hash(tmp_path, new_targets) != stale
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_STALE"], _codes(vs)
    assert vs[0].severity == "warn"
    assert stale in vs[0].detail["found_hashes"]


def test_glob_target_resolves(tmp_path):
    # A glob target resolves when >=1 path matches under the tree -> no UNRESOLVED; MISSING (no
    # screening) still fires. Proves glob targets are grounded, not treated as literal phantoms.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/a.py")
    _make_target(tmp_path, "src/b.py")
    _declare_scope(tmp_path, "r", ["src/*.py"])
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_MISSING"], _codes(vs)  # resolved, just unscreened


def test_config_block_flips_severity(tmp_path):
    # [triage] scope_grounding = "block" -> the MISSING fire is severity block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[triage]\nscope_grounding = "block"\n')
    _make_target(tmp_path, "src/mod.py")
    _declare_scope(tmp_path, "r", ["src/mod.py"])
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "block"


def test_config_garbage_falls_back_to_warn(tmp_path):
    # A non-{warn,block} value is fail-closed to the SAFE migration default (warn), never block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[triage]\nscope_grounding = "loud"\n')
    _make_target(tmp_path, "src/mod.py")
    _declare_scope(tmp_path, "r", ["src/mod.py"])
    vs = validate_triage_screening(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_MISSING"], _codes(vs)
    assert vs[0].severity == "warn"


# =========================================================================== findings gate
def test_findings_gate_noop_without_covering_screening(tmp_path):
    # Scope declared, NO covering screening -> the findings gate stays silent (MISSING is the floor's
    # job; the findings gate must not double-report).
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    _declare_scope(tmp_path, "r", ["src/mod.py"])
    assert validate_triage_findings(ws, "r") == []


def test_findings_undispositioned_blocks(tmp_path):
    # verdict=findings with a discharged finding naming a NONEXISTENT fix path (a label, not a fix)
    # -> one TRIAGE_FINDING_UNDISPOSITIONED.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    finding = {
        "id": "T1",
        "severity": "P1",
        "defect_class": "scope",
        "message": "target mis-scoped",
        "substrate_ref": "src/mod.py",
        "repro": "inspect",
        "disposition": {"kind": "discharged", "handling_artifact_path": "proposals/r/ghost.yaml"},
    }
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets), verdict="findings", findings=[finding])
    vs = validate_triage_findings(ws, "r")
    assert _codes(vs) == ["TRIAGE_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "warn"
    assert vs[0].detail["finding_id"] == "T1"


def test_discharged_finding_with_resolving_artifact_clears(tmp_path):
    # verdict=findings, one discharged finding whose handling_artifact_path RESOLVES (run-bound +
    # exists) -> no undispositioned block. Non-vacuity vs the nonexistent-path test above.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    fix_rel = _write_fix_artifact(tmp_path, "r")
    finding = {
        "id": "T1",
        "severity": "P1",
        "defect_class": "scope",
        "message": "target mis-scoped",
        "substrate_ref": "src/mod.py",
        "repro": "inspect",
        "disposition": {"kind": "discharged", "handling_artifact_path": fix_rel},
    }
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets), verdict="findings", findings=[finding])
    assert validate_triage_findings(ws, "r") == []


def test_adjudicated_finding_complete_clears(tmp_path):
    # A complete adjudication (decision + rationale + cost_if_wrong) clears -> [].
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    finding = {
        "id": "T2",
        "severity": "P2",
        "defect_class": "granularity",
        "message": "score high",
        "substrate_ref": "src/mod.py",
        "repro": "n/a",
        "disposition": {
            "kind": "adjudicated",
            "decision": "accept",
            "rationale": "entanglement acknowledged",
            "cost_if_wrong": "re-triage",
        },
    }
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets), verdict="findings", findings=[finding])
    assert validate_triage_findings(ws, "r") == []


def test_cannot_verify_verdict_surfaces_inconclusive_warn(tmp_path):
    # verdict=cannot_verify -> TRIAGE_SCREENING_INCONCLUSIVE at warn (abstained, never a silent pass).
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets), verdict="cannot_verify")
    vs = validate_triage_findings(ws, "r")
    assert _codes(vs) == ["TRIAGE_SCREENING_INCONCLUSIVE"], _codes(vs)
    assert vs[0].severity == "warn"


def test_findings_gate_config_block_flips_severity(tmp_path):
    # [triage] scope_grounding = "block" -> the undispositioned finding fires at block.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[triage]\nscope_grounding = "block"\n')
    _make_target(tmp_path, "src/mod.py")
    targets = ["src/mod.py"]
    _declare_scope(tmp_path, "r", targets)
    finding = {
        "id": "T1",
        "severity": "P1",
        "defect_class": "scope",
        "message": "bug",
        "substrate_ref": "src/mod.py",
        "repro": "inspect",
        "disposition": {"kind": "discharged", "handling_artifact_path": "proposals/r/ghost.yaml"},
    }
    _write_screening(tmp_path, "r", _expected_hash(tmp_path, targets), verdict="findings", findings=[finding])
    vs = validate_triage_findings(ws, "r")
    assert _codes(vs) == ["TRIAGE_FINDING_UNDISPOSITIONED"], _codes(vs)
    assert vs[0].severity == "block"


# =========================================================================== forced-gate wrapper
def test_forced_gate_noops_when_not_triage_exit(tmp_path):
    # The forced wrapper self-selects to triage: for any OTHER from_phase it short-circuits to
    # ([], []) BEFORE reading state — even with a broken declared scope in the workspace. This is the
    # phase-scoping the correctness (generic-closure) instance skipped.
    ws = _ws(tmp_path)
    _declare_scope(tmp_path, "r", ["src/ghost.py"])  # would block at triage
    assert _run_forced_triage_grounding_gate(ws, "r", "verify", "resolved") == ([], [], [])
    assert _run_forced_triage_grounding_gate(ws, "r", "plan", "execute") == ([], [], [])


def test_forced_gate_surfaces_advisories_at_triage_exit(tmp_path):
    # At triage exit with a broken scope + default (warn) config, the wrapper returns the findings as
    # ADVISORIES, never blockers — so the transition is NOT blocked (behavior-preserving default),
    # yet the grounding signal is visible.
    ws = _ws(tmp_path)
    _declare_scope(tmp_path, "r", ["src/ghost.py"])
    blockers, advisories, _findings = _run_forced_triage_grounding_gate(ws, "r", "triage", "propose")
    assert blockers == []
    assert any("TRIAGE_SCOPE_TARGET_UNRESOLVED" in a for a in advisories)
    assert any("TRIAGE_SCREENING_MISSING" in a for a in advisories)


def test_forced_gate_blocks_at_triage_exit_when_config_block(tmp_path):
    # With [triage] scope_grounding = "block", the same broken scope yields BLOCKERS -> the
    # transition would be blocked. Non-vacuity vs the warn default above.
    ws = _ws(tmp_path)
    (ws / ".uacp" / "config.toml").write_text('[triage]\nscope_grounding = "block"\n')
    _declare_scope(tmp_path, "r", ["src/ghost.py"])
    blockers, _advisories, _findings = _run_forced_triage_grounding_gate(ws, "r", "triage", "propose")
    assert any("TRIAGE_SCOPE_TARGET_UNRESOLVED" in b for b in blockers)


def test_new_file_under_existing_parent_is_not_a_phantom(tmp_path):
    # Codex #172 P2: TRIAGE runs before execution; a write_path for a NEW file whose PARENT dir
    # exists is a legitimate intended output ('planned'), not a phantom -> no UNRESOLVED.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/existing.py")  # creates the src/ parent
    _declare_scope(tmp_path, "r", ["src/newfile.py"])  # a new file under the existing src/
    codes = _codes(validate_triage_screening(ws, "r"))
    assert "TRIAGE_SCOPE_TARGET_UNRESOLVED" not in codes, codes
    assert codes == ["TRIAGE_SCREENING_MISSING"], codes  # only the (expected) missing-screening


def test_forced_gate_surfaces_structured_findings(tmp_path):
    # Codex #172 P2: the forced grounding gate returns structured findings (a 3rd element) so the
    # transition envelope keeps each finding's detail/path — the graph gate is disabled for TRIAGE.
    ws = _ws(tmp_path)
    _make_target(tmp_path, "src/mod.py")
    _declare_scope(tmp_path, "r", ["src/mod.py"])  # resolves, but no screening -> MISSING advisory
    result = _run_forced_triage_grounding_gate(ws, "r", "triage", "propose")
    assert len(result) == 3, result
    _blockers, _advisories, findings = result
    assert findings, "structured findings must be surfaced"
    assert findings[0]["code"] == "TRIAGE_SCREENING_MISSING"
    assert "detail" in findings[0] and "path" in findings[0]

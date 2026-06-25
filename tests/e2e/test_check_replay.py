"""E2E (capsule #3, slice 0): the replay engine re-runs FROZEN uacp.check.* checks.

Proves the freeze->replay spine end-to-end on the RELATION + artifact planes: a check
registered in the manifest projects as a `check` node (the net-new _project arm), and
`validate_check_replay` re-evaluates it against bound reality — FAIL on a mismatch,
PASS (no violation) on a match, and ERROR (block, never silent pass — #503 class A)
when the bind cannot resolve. No agent code runs at replay; the evaluator is fixed.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
import yaml
from engines.manifest.projection import validate_check_replay


def _init(root: Path, run_id: str) -> None:
    state_machine.handle_init(
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
    )


def _write(root: Path, rel: str, doc: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _register(root: Path, run_id: str, atype: str, rel: str) -> None:
    out = json.loads(
        state_machine.handle_register_artifact(
            {"workspace": str(root), "run_id": run_id, "artifact_type": atype, "path": rel}
        )
    )
    assert out.get("ok") is True, out


def _field_equals_check(target: str, artifact: str, path: str, value: str) -> dict:
    return {
        "kind": "uacp.check.field_equals",
        "id": "chk-1",
        "from": {"target": target, "basis": f"{target} sets {path}"},
        "bind": {"plane": "artifact", "ref": {"artifact": artifact, "path": path}},
        "expect": {"value": value},
        "severity": "block",
    }


def _codes(root: Path, run_id: str) -> set[str]:
    return {v.code for v in validate_check_replay(str(root), run_id)}


def test_field_equals_fails_on_mismatch(temp_uacp_root: Path):
    run_id = "uacp-chk-1"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-data.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "broken"})
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk-1.yaml",
        _field_equals_check("wu-1", data_rel, "status", "ready"),
    )
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk-1.yaml")

    codes = _codes(temp_uacp_root, run_id)
    assert "CHK_FIELD_EQUALS" in codes, codes  # status=broken != ready -> FAIL (block)


def test_failing_check_blocks_regardless_of_declared_severity(temp_uacp_root: Path):
    """Reviewer (MAJOR): the gated agent must not self-demote a FAILING check to non-blocking.
    A field_equals that FAILS, authored with severity 'warn', must STILL emit a block-severity
    violation — "block done if a check fails" is not opt-out by the author."""
    run_id = "uacp-sev-1"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-data.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "broken"})
    check = _field_equals_check("wu-1", data_rel, "status", "ready")
    check["severity"] = "warn"  # agent tries to declare its own failing check non-blocking
    _write(temp_uacp_root, f"verification/{run_id}-chk-1.yaml", check)
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk-1.yaml")

    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_FIELD_EQUALS" and v.severity == "block" for v in vs), vs


def test_field_equals_passes_on_match(temp_uacp_root: Path):
    run_id = "uacp-chk-2"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-data.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk-1.yaml",
        _field_equals_check("wu-1", data_rel, "status", "ready"),
    )
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk-1.yaml")

    assert "CHK_FIELD_EQUALS" not in _codes(temp_uacp_root, run_id)  # match -> no violation


def test_dangling_bind_is_error_block_not_pass(temp_uacp_root: Path):
    """#503 class A: a check whose bound artifact does not resolve is an ERROR (block),
    never a silent pass."""
    run_id = "uacp-chk-3"
    _init(temp_uacp_root, run_id)
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk-1.yaml",
        _field_equals_check("wu-1", f"plans/{run_id}-DOES-NOT-EXIST.yaml", "status", "ready"),
    )
    _register(temp_uacp_root, run_id, "check_1", f"verification/{run_id}-chk-1.yaml")

    violations = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_FIELD_EQUALS" and v.severity == "block" for v in violations), (
        violations
    )


def _obl_run(root: Path, run_id: str, *, assessment_state: str, checkpoint_result: str) -> None:
    """A run whose work_unit wu-1 carries obligation ev-1, an EXECUTE checkpoint, and a
    VERIFY assessment — the substrate an `obligation_satisfied` check reads from the graph."""
    _init(root, run_id)
    _write(
        root,
        f"proposals/{run_id}-proposal.yaml",
        {"kind": "uacp.proposal", "scope": {"in_scope": [{"id": "si-1", "statement": "x"}]}},
    )
    _write(
        root,
        f"plans/{run_id}-piv.yaml",
        {
            "kind": "uacp.phase_intent_verification_contract",
            "work_units": [{"id": "wu-1", "intent": "x", "derives_from": ["si-1"]}],
            "evidence_obligations": [{"id": "ev-1", "work_unit_id": "wu-1"}],
        },
    )
    _write(
        root,
        f"executions/{run_id}-cp-1.yaml",
        {
            "kind": "uacp.execution_checkpoint",
            "checkpoint_id": "cp-1",
            "work_unit_id": "wu-1",
            "checkpoint_type": "after_work_unit",
            "evidence": [{"obligation_id": "ev-1", "result": checkpoint_result, "summary": "x"}],
        },
    )
    _write(
        root,
        f"verification/{run_id}-assessment.yaml",
        {
            "kind": "uacp.piv_assessment",
            "assessments": [{"id": "as-1", "obligation_id": "ev-1", "state": assessment_state}],
        },
    )
    _register(root, run_id, "proposal", f"proposals/{run_id}-proposal.yaml")
    _register(root, run_id, "piv", f"plans/{run_id}-piv.yaml")
    _register(root, run_id, "checkpoint", f"executions/{run_id}-cp-1.yaml")
    _register(root, run_id, "assessment", f"verification/{run_id}-assessment.yaml")


def _obl_check(obligation_id: str) -> dict:
    return {
        "kind": "uacp.check.obligation_satisfied",
        "id": "chk-obl",
        "from": {"target": "wu-1", "basis": f"obligation {obligation_id} is satisfied"},
        "bind": {"plane": "graph", "obligation_id": obligation_id},
        "severity": "block",
    }


def test_obligation_satisfied_passes_when_obligation_verified(temp_uacp_root: Path):
    run_id = "uacp-obl-1"
    _obl_run(temp_uacp_root, run_id, assessment_state="pass", checkpoint_result="pass")
    _write(temp_uacp_root, f"verification/{run_id}-chk-obl.yaml", _obl_check("ev-1"))
    _register(temp_uacp_root, run_id, "check_obl", f"verification/{run_id}-chk-obl.yaml")
    assert "CHK_OBLIGATION_SATISFIED" not in _codes(temp_uacp_root, run_id)


def test_obligation_satisfied_fails_when_unverified_or_blocked(temp_uacp_root: Path):
    # no passing assessment -> FAIL
    run_id = "uacp-obl-2"
    _obl_run(temp_uacp_root, run_id, assessment_state="block", checkpoint_result="pass")
    _write(temp_uacp_root, f"verification/{run_id}-chk-obl.yaml", _obl_check("ev-1"))
    _register(temp_uacp_root, run_id, "check_obl", f"verification/{run_id}-chk-obl.yaml")
    assert "CHK_OBLIGATION_SATISFIED" in _codes(temp_uacp_root, run_id)


def test_obligation_satisfied_unresolvable_bind_is_error_block(temp_uacp_root: Path):
    # #503 class A: a check bound to an obligation that does NOT exist is ERROR (block),
    # never a silent pass — even though the run is otherwise fully verified.
    run_id = "uacp-obl-3"
    _obl_run(temp_uacp_root, run_id, assessment_state="pass", checkpoint_result="pass")
    _write(temp_uacp_root, f"verification/{run_id}-chk-obl.yaml", _obl_check("ev-NOPE"))
    _register(temp_uacp_root, run_id, "check_obl", f"verification/{run_id}-chk-obl.yaml")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_OBLIGATION_SATISFIED" and v.severity == "block" for v in vs), vs


def test_code_plane_check_is_error_for_any_kind(temp_uacp_root: Path):
    # mimo MINOR #2: the code/behavior fail-closed-until-wired guard must apply to ANY kind, so an
    # IMPLEMENTED kind cannot be mislabeled onto an unwired plane to dodge it. A field_equals that
    # declares `plane: code` ERRORs (block) rather than being silently evaluated on the artifact.
    run_id = "uacp-plane-1"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    check = {
        "kind": "uacp.check.field_equals",
        "id": "chk-cp",
        "from": {"target": "wu-1", "basis": "x"},
        "bind": {"plane": "code", "ref": {"artifact": data_rel, "path": "status"}},
        "expect": {"value": "ready"},
        "severity": "block",
    }
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _write(temp_uacp_root, f"verification/{run_id}-chk-cp.yaml", check)
    _register(temp_uacp_root, run_id, "data", data_rel)
    _register(temp_uacp_root, run_id, "check_cp", f"verification/{run_id}-chk-cp.yaml")
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_FIELD_EQUALS" and v.severity == "block" for v in vs), vs


def _integrity_check(target: str, artifact: str) -> dict:
    return {
        "kind": "uacp.check.artifact_integrity",
        "id": "chk-int",
        "from": {"target": target, "basis": f"{artifact} intact"},
        "bind": {"plane": "artifact", "ref": {"artifact": artifact}},
        "severity": "block",
    }


def _watermark(root: Path, run_id: str, rel: str) -> None:
    # Record the watermark over the artifact's EXACT on-disk bytes (what a governed write does).
    from engines.domain.artifact_hashes import record_hash

    from config import base_dir

    raw = (base_dir(root) / rel).read_text(encoding="utf-8")
    record_hash(str(root), run_id, rel, raw)


def _put_integrity_check(root: Path, run_id: str, artifact: str) -> None:
    rel = f"verification/{run_id}-chk-int.yaml"
    _write(root, rel, _integrity_check("wu-1", artifact))
    _register(root, run_id, "check_int", rel)


def test_artifact_integrity_passes_when_watermark_matches(temp_uacp_root: Path):
    """Council (kimi, MAJOR): artifact_integrity was a no-op PASS. It now verifies the artifact's
    content against its recorded watermark — an intact, watermarked artifact passes."""
    run_id = "uacp-int-1"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _watermark(temp_uacp_root, run_id, data_rel)
    _register(temp_uacp_root, run_id, "data", data_rel)
    _put_integrity_check(temp_uacp_root, run_id, data_rel)
    assert "CHK_ARTIFACT_INTEGRITY" not in _codes(temp_uacp_root, run_id)


def test_artifact_integrity_fails_on_tamper(temp_uacp_root: Path):
    # watermark the original, then tamper the file -> content diverges -> FAIL (block).
    run_id = "uacp-int-2"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _watermark(temp_uacp_root, run_id, data_rel)
    # out-of-band edit AFTER the watermark:
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "TAMPERED"})
    _register(temp_uacp_root, run_id, "data", data_rel)
    _put_integrity_check(temp_uacp_root, run_id, data_rel)
    assert "CHK_ARTIFACT_INTEGRITY" in _codes(temp_uacp_root, run_id)


def test_artifact_integrity_unwatermarked_is_error_block(temp_uacp_root: Path):
    # #503 class A: an artifact with NO watermark cannot have its integrity verified -> ERROR
    # (block), NOT a silent pass. This is the fix for the no-op gaming vector (cover every target
    # with trivially-passing integrity checks).
    run_id = "uacp-int-3"
    _init(temp_uacp_root, run_id)
    data_rel = f"plans/{run_id}-d.yaml"  # raw write, never watermarked
    _write(temp_uacp_root, data_rel, {"kind": "uacp.scope", "status": "ready"})
    _register(temp_uacp_root, run_id, "data", data_rel)
    _put_integrity_check(temp_uacp_root, run_id, data_rel)
    vs = validate_check_replay(str(temp_uacp_root), run_id)
    assert any(v.code == "CHK_ARTIFACT_INTEGRITY" and v.severity == "block" for v in vs), vs


def test_edge_exists_graph_plane(temp_uacp_root: Path):
    """A graph-plane check binds to the projected manifest graph (no artifact load)."""
    run_id = "uacp-chk-4"
    _init(temp_uacp_root, run_id)
    # A proposal with a keyed scope item si-1 + a PIV work_unit wu-1 derives_from si-1
    # => the edge (wu-1, derives_from, si-1) exists in the projected graph.
    _write(
        temp_uacp_root,
        f"proposals/{run_id}-proposal.yaml",
        {"kind": "uacp.proposal", "scope": {"in_scope": [{"id": "si-1", "statement": "x"}]}},
    )
    _write(
        temp_uacp_root,
        f"plans/{run_id}-piv.yaml",
        {
            "kind": "uacp.phase_intent_verification_contract",
            "work_units": [{"id": "wu-1", "intent": "x", "derives_from": ["si-1"]}],
        },
    )
    _register(temp_uacp_root, run_id, "proposal", f"proposals/{run_id}-proposal.yaml")
    _register(temp_uacp_root, run_id, "piv", f"plans/{run_id}-piv.yaml")

    # present edge -> PASS; absent edge -> FAIL.
    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk-present.yaml",
        {
            "kind": "uacp.check.edge_exists",
            "id": "chk-present",
            "from": {"target": "si-1", "basis": "si-1 is covered"},
            "bind": {"plane": "graph", "src": "wu-1", "rel": "derives_from", "dst": "si-1"},
            "severity": "block",
        },
    )
    _register(temp_uacp_root, run_id, "check_present", f"verification/{run_id}-chk-present.yaml")
    assert "CHK_EDGE_EXISTS" not in _codes(temp_uacp_root, run_id)

    _write(
        temp_uacp_root,
        f"verification/{run_id}-chk-absent.yaml",
        {
            "kind": "uacp.check.edge_exists",
            "id": "chk-absent",
            "from": {"target": "si-1", "basis": "bogus"},
            "bind": {"plane": "graph", "src": "wu-1", "rel": "derives_from", "dst": "si-NOPE"},
            "severity": "block",
        },
    )
    _register(temp_uacp_root, run_id, "check_absent", f"verification/{run_id}-chk-absent.yaml")
    assert "CHK_EDGE_EXISTS" in _codes(temp_uacp_root, run_id)

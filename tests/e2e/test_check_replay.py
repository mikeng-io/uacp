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
    assert any(
        v.code == "CHK_FIELD_EQUALS" and v.severity == "block" for v in violations
    ), violations


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

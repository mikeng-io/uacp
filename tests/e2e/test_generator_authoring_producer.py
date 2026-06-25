"""E2E (capsule #3, slice 1): the GENERATOR producer contract end-to-end.

The generative-gate-authoring contract (skills/uacp-core/references/generative-gate-authoring.md,
wired into uacp-propose/uacp-plan/uacp-verify) says: each phase authors a uacp.check.* per target
via the governed writer, and the kernel then sees it. This proves that producer path reaches the
FORCED verify_exit gate — a target whose check was authored via `create_entity` satisfies coverage;
a target left unchecked is blocked (`GP_UNCHECKED_TARGET`). Scope: the producer side of node 34
**Layer 1 (structural coverage)** only — the floor (CHK_FLOOR_UNMET) and class entailment
(CHK_CLASS_UNDERCLAIM) have their own unit tests; this exercises the authoring->coverage path.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from engines.graph_projection import validate_graph_invariants
from engines.manifest.entity_writer import create_entity
from state_machine import handle_init, handle_register_artifact


def _init(root: Path, run_id: str) -> None:
    handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})


def _write(root: Path, rel: str, doc: dict) -> None:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _register(root: Path, run_id: str, atype: str, rel: str) -> None:
    out = json.loads(
        handle_register_artifact(
            {"workspace": str(root), "run_id": run_id, "artifact_type": atype, "path": rel}
        )
    )
    assert out.get("ok") is True, out


def _author_check(root: Path, run_id: str, target: str, seq: str) -> None:
    # The producer step the skills drive: author a frozen check via the governed writer. A bland
    # field_present binding the (present) proposal `kind` field — passes replay, declares no class
    # (floor self-limits), bland target text (no underclaim) — so coverage is the only signal.
    res = create_entity(
        str(root),
        run_id,
        "uacp.check.field_present",
        {
            "id": f"chk-{seq}",
            "from": {"target": target, "basis": f"{target} is concretely stated"},
            "bind": {
                "plane": "artifact",
                "ref": {"artifact": f"proposals/{run_id}-p.yaml", "path": "kind"},
            },
            "severity": "block",
        },
        seq=seq,
    )
    assert res.get("ok") is True, res


def _seed_targets(root: Path, run_id: str) -> None:
    # A keyed scope_item si-1 covered by a work_unit wu-1; bland text so only coverage speaks.
    _write(
        root,
        f"proposals/{run_id}-p.yaml",
        {"kind": "uacp.proposal", "scope": {"in_scope": [{"id": "si-1", "statement": "the task"}]}},
    )
    _write(
        root,
        f"plans/{run_id}-piv.yaml",
        {
            "kind": "uacp.phase_intent_verification_contract",
            "work_units": [{"id": "wu-1", "intent": "do the task", "derives_from": ["si-1"]}],
        },
    )
    _register(root, run_id, "proposal", f"proposals/{run_id}-p.yaml")
    _register(root, run_id, "piv", f"plans/{run_id}-piv.yaml")


def _unchecked(root: Path, run_id: str) -> set[str | None]:
    vs = validate_graph_invariants(str(root), run_id, "verify_exit")
    return {v.detail.get("target") for v in vs if v.code == "GP_UNCHECKED_TARGET"}


def test_authored_checks_satisfy_coverage_at_verify_exit(temp_uacp_root: Path):
    run_id = "uacp-gen-1"
    _init(temp_uacp_root, run_id)
    _seed_targets(temp_uacp_root, run_id)
    _author_check(temp_uacp_root, run_id, "si-1", "1")
    _author_check(temp_uacp_root, run_id, "wu-1", "2")
    # both targets authored via the governed writer -> coverage clean at the forced gate
    assert _unchecked(temp_uacp_root, run_id) == set()


def test_unchecked_target_is_blocked_at_verify_exit(temp_uacp_root: Path):
    # the producer side of node 34 Layer 1: a target whose phase did NOT author a check is blocked.
    run_id = "uacp-gen-2"
    _init(temp_uacp_root, run_id)
    _seed_targets(temp_uacp_root, run_id)
    _author_check(temp_uacp_root, run_id, "si-1", "1")  # si-1 covered, wu-1 NOT
    assert _unchecked(temp_uacp_root, run_id) == {"wu-1"}

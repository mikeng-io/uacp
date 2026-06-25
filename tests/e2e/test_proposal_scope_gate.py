"""E2E: the proposal package gate REQUIRES a keyed scope module (D43 Option C).

Closing the package-selection coverage fail-open: a package-selection PROPOSE->PLAN
could mark its `scope` universal-core concern `not_applicable` (or back it with
unstructured markdown), so no keyed scope_items existed and intent coverage was
unverifiable. `validate_adaptive_proposal_package_gate` now requires the scope
concern be `covered` by an artifact carrying keyed `scope.in_scope:[{id,statement}]`.

We isolate the scope requirement the way test_transition_matrix isolates the graph
blocker: assert only on the PRESENCE / ABSENCE of the scope-gate blocker, not on the
whole decision (other unseeded gates may also block — irrelevant here).
"""

from __future__ import annotations

from pathlib import Path

import state_machine
import yaml
from core import Heartgate

from tests.e2e.test_full_lifecycle import _na_block, _seed_proposal_package

_COVERED_MSG = "scope must be 'covered' by a keyed scope module"
_KEYED_MSG = "scope artifact must declare"


def _init(root: Path, run_id: str) -> None:
    # _seed_proposal_package now REGISTERS the keyed scope module (Option B), which
    # needs a run manifest — so each scope-gate case initialises the run first.
    state_machine.handle_init(
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"}
    )


def _blockers(root: Path, run_id: str) -> list[str]:
    return (
        Heartgate.load(str(root))
        .validate_transition(
            {
                "from_phase": "propose",
                "to_phase": "plan",
                "run_id": run_id,
                "artifact_path": "plans/test.yaml",
            }
        )
        .blockers
    )


def _selection_path(root: Path, run_id: str) -> Path:
    return root / ".uacp" / "proposals" / f"{run_id}-package-selection.yaml"


def test_keyed_scope_module_satisfies_the_gate(temp_uacp_root: Path, valid_run_id: str):
    # _seed_proposal_package now emits a keyed scope module + scope status=covered.
    _init(temp_uacp_root, valid_run_id)
    _seed_proposal_package(temp_uacp_root, valid_run_id)
    blockers = _blockers(temp_uacp_root, valid_run_id)
    assert not any(_COVERED_MSG in b or _KEYED_MSG in b for b in blockers), blockers


def test_not_applicable_scope_is_blocked(temp_uacp_root: Path, valid_run_id: str):
    _init(temp_uacp_root, valid_run_id)
    _seed_proposal_package(temp_uacp_root, valid_run_id)
    # Revert the scope concern to not_applicable — the pre-D43 bypass.
    sel = yaml.safe_load(_selection_path(temp_uacp_root, valid_run_id).read_text())
    sel["universal_core"]["scope"] = _na_block()
    _selection_path(temp_uacp_root, valid_run_id).write_text(yaml.safe_dump(sel, sort_keys=False))

    blockers = _blockers(temp_uacp_root, valid_run_id)
    assert any(_COVERED_MSG in b for b in blockers), blockers


def test_unstructured_scope_module_is_blocked(temp_uacp_root: Path, valid_run_id: str):
    _init(temp_uacp_root, valid_run_id)
    _seed_proposal_package(temp_uacp_root, valid_run_id)
    # Scope concern stays 'covered' but the module carries BARE-STRING intents
    # (not keyed {id,statement}) — no scope_item nodes can be projected.
    sm = temp_uacp_root / ".uacp" / "proposals" / valid_run_id / "scope-module.yaml"
    sm.write_text(
        yaml.safe_dump(
            {"kind": "uacp.proposal", "scope": {"in_scope": ["a bare intent"], "out_of_scope": []}},
            sort_keys=False,
        )
    )
    blockers = _blockers(temp_uacp_root, valid_run_id)
    assert any(_KEYED_MSG in b for b in blockers), blockers

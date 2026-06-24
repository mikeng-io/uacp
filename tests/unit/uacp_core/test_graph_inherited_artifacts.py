"""graph_projection must project a run's inherited_artifacts, not only its own.

Goal-chained (goal-driven) runs REUSE parent prior-phase outputs: handle_init copies
the parent's triage/proposal/plan artifact refs into the child manifest's
`inherited_artifacts`, NOT its own `artifacts`. If the projection ignores
inherited_artifacts, a child run that reuses a parent proposal/plan projects an
EMPTY coverage graph — so a dropped intent in the inherited proposal silently
passes. This is the review-surfaced blind spot (node 15).

Teeth: a child manifest whose inherited proposal declares two intents but whose
inherited plan covers only one must report GP_UNCOVERED_INTENT for the dropped one.
The test FAILS before the fix (inherited_artifacts unprojected -> empty graph -> no
finding) and passes after.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from engines.graph_projection import validate_graph_projection


def _write(p: Path, doc: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False))


def test_inherited_proposal_plan_are_projected_for_coverage(temp_uacp_root: Path):
    run_id = "uacp-test-child"
    base = temp_uacp_root / ".uacp"

    # Inherited parent outputs: two declared intents, only one covered by a work_unit.
    _write(
        base / "proposals" / f"{run_id}-prop.yaml",
        {
            "kind": "uacp.proposal",
            "scope": {
                "in_scope": [
                    {"id": "si-1", "statement": "covered intent"},
                    {"id": "si-2", "statement": "DROPPED intent"},
                ],
                "out_of_scope": [],
            },
        },
    )
    _write(
        base / "plans" / f"{run_id}-plan.yaml",
        {"kind": "uacp.plan", "work_units": [{"id": "wu-1", "derives_from": ["si-1"]}]},
    )

    # Child manifest: own artifacts EMPTY; the proposal/plan live in inherited_artifacts
    # (exactly how handle_init records reused parent prior-phase outputs).
    _write(
        base / "state" / "runs" / f"{run_id}.yaml",
        {
            "run_id": run_id,
            "status": "active",
            "current_phase": "plan",
            "artifacts": {},
            "inherited_artifacts": {
                "proposal": f"proposals/{run_id}-prop.yaml",
                "plan": f"plans/{run_id}-plan.yaml",
            },
        },
    )

    violations = validate_graph_projection(temp_uacp_root, run_id)
    codes = [v.code for v in violations]
    assert "GP_UNCOVERED_INTENT" in codes, f"expected dropped si-2 to be caught; got {codes}"
    # And it is specifically the dropped intent, not a false hit on the covered one.
    uncovered = [v for v in violations if v.code == "GP_UNCOVERED_INTENT"]
    assert any("si-2" in v.detail.get("scope_item", "") for v in uncovered), uncovered
    assert not any("si-1" in v.detail.get("scope_item", "") for v in uncovered), uncovered

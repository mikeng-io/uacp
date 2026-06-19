"""Unit tests for the graph_projection structural-integrity engine (Phase A).

Covers the structural closure checks (always-block) and confirms the progress
check (`unverified`) is NOT emitted (it is phase-gated; final-review T2).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from engines.graph_projection import validate_graph_projection


def _prop(items: list) -> dict:
    return {"kind": "uacp.proposal", "scope": {"in_scope": items, "out_of_scope": []}}


def _plan(wus: list) -> dict:
    return {"kind": "uacp.plan", "work_units": wus}


def _ws(tmp_path: Path, run: str, proposal: dict, plan: dict, extra_docs: list | None = None) -> Path:
    """Build a minimal .uacp workspace: a run manifest with an artifacts map + the artifacts."""
    base = tmp_path / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "proposals").mkdir()
    (base / "plans").mkdir()
    arts = {"proposal": "proposals/p.yaml", "plan": "plans/p.yaml"}
    (base / "proposals" / "p.yaml").write_text(yaml.safe_dump(proposal))
    (base / "plans" / "p.yaml").write_text(yaml.safe_dump(plan))
    for i, doc in enumerate(extra_docs or [], 1):
        (base / "plans" / f"x{i}.yaml").write_text(yaml.safe_dump(doc))
        arts[f"x{i}"] = f"plans/x{i}.yaml"
    (base / "state" / "runs" / f"{run}.yaml").write_text(
        yaml.safe_dump({"kind": "uacp.run_state", "run_id": run, "artifacts": arts})
    )
    return tmp_path


def _codes(vs):
    return sorted(v.code for v in vs)


def test_clean_run_is_sound(tmp_path):
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1", "statement": "A"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]}]))
    assert validate_graph_projection(ws, "r") == []


def test_dropped_intent_is_uncovered(tmp_path):
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1"}, {"id": "si-2"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]}]))
    vs = validate_graph_projection(ws, "r")
    uncovered = [v.detail.get("scope_item") for v in vs if v.code == "GP_UNCOVERED_INTENT"]
    assert uncovered == ["si-2"]
    assert all(v.severity == "block" for v in vs)


def test_orphan_work_unit(tmp_path):
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]}, {"id": "wu-x"}]))
    vs = validate_graph_projection(ws, "r")
    assert [v.detail.get("work_unit") for v in vs if v.code == "GP_ORPHAN_WORK_UNIT"] == ["wu-x"]


def test_phantom_edge(tmp_path):
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]},
                    {"id": "wu-2", "derives_from": ["ghost"]}]))
    vs = validate_graph_projection(ws, "r")
    assert any(v.code == "GP_PHANTOM_EDGE" and v.detail.get("dst") == "ghost" for v in vs)


def test_inprogress_is_structurally_sound(tmp_path):
    # proposal+plan only (no EXECUTE/VERIFY): structurally sound. `unverified` is
    # phase-gated and must NOT appear as a structural violation here (T2).
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]}]))
    assert validate_graph_projection(ws, "r") == []


def test_contradicted_assessment(tmp_path):
    ws = _ws(tmp_path, "r", _prop([{"id": "si-1"}]),
             _plan([{"id": "wu-1", "derives_from": ["si-1"]},
                    {"id": "ev-1", "work_unit_id": "wu-1"}]),  # (plan-level obligation; id-only)
             extra_docs=[
                 {"kind": "uacp.execution",
                  "checkpoints": [{"id": "cp-1", "work_unit_id": "wu-1", "result": "fail"}]},
                 {"kind": "uacp.piv_assessment",
                  "assessments": [{"id": "as-1", "work_unit_id": "wu-1",
                                   "evidence_refs": ["cp-1"], "result": "pass"}]},
             ])
    vs = validate_graph_projection(ws, "r")
    assert any(v.code == "GP_CONTRADICTED" for v in vs)


def test_legacy_bare_strings_read_as_uncovered(tmp_path):
    # legacy form (bare-string in_scope, no derives_from) -> all uncovered (flags pre-keys run)
    ws = _ws(tmp_path, "r", _prop(["legacy intent A", "legacy intent B"]),
             _plan([{"id": "wu-1"}]))
    vs = validate_graph_projection(ws, "r")
    assert sum(1 for v in vs if v.code == "GP_UNCOVERED_INTENT") == 2
    assert any(v.code == "GP_ORPHAN_WORK_UNIT" for v in vs)


def test_never_raises_on_missing_manifest(tmp_path):
    assert validate_graph_projection(tmp_path, "nope") == []

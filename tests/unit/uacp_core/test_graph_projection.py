"""Unit tests for the graph_projection structural-integrity engine (Phase A).

Covers the structural closure checks (always-block) and confirms the progress
check (`unverified`) is NOT emitted (it is phase-gated; final-review T2).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from engines.graph_projection import (
    validate_graph_invariants,
    validate_graph_projection,
)


def _prop(items: list) -> dict:
    return {"kind": "uacp.proposal", "scope": {"in_scope": items, "out_of_scope": []}}


def _plan(wus: list) -> dict:
    return {"kind": "uacp.plan", "work_units": wus}


def _piv(obls: list) -> dict:
    return {"kind": "uacp.piv", "evidence_obligations": obls}


def _exec(checkpoint_id: str, work_unit_id: str, result: str = "pass") -> dict:
    # Real execution_checkpoint shape (D42): ONE doc per checkpoint — top-level checkpoint_id +
    # work_unit_id + evidence[]; the checkpoint outcome rolls up from evidence[].result. `result`
    # must be a real outcome ({pass,warn,block,deferred}); the old spike used {pass,fail}.
    return {
        "kind": "uacp.execution_checkpoint",
        "checkpoint_id": checkpoint_id,
        "work_unit_id": work_unit_id,
        "evidence": [{"obligation_id": "ev-1", "result": result, "summary": "x"}],
    }


def _verif(asmts: list) -> dict:
    return {"kind": "uacp.piv_assessment", "assessments": asmts}


def _ws(
    tmp_path: Path, run: str, proposal: dict, plan: dict, extra_docs: list | None = None
) -> Path:
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


def test_clean_run_is_sound(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1", "statement": "A"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
    )
    assert validate_graph_projection(ws, "r") == []


def test_dropped_intent_is_uncovered(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}, {"id": "si-2"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
    )
    vs = validate_graph_projection(ws, "r")
    uncovered = [v.detail.get("scope_item") for v in vs if v.code == "GP_UNCOVERED_INTENT"]
    assert uncovered == ["si-2"]
    assert all(v.severity == "block" for v in vs)


def test_orphan_work_unit(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}, {"id": "wu-x"}]),
    )
    vs = validate_graph_projection(ws, "r")
    assert [v.detail.get("work_unit") for v in vs if v.code == "GP_ORPHAN_WORK_UNIT"] == ["wu-x"]


def test_phantom_edge(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan(
            [{"id": "wu-1", "derives_from": ["si-1"]}, {"id": "wu-2", "derives_from": ["ghost"]}]
        ),
    )
    vs = validate_graph_projection(ws, "r")
    assert any(v.code == "GP_PHANTOM_EDGE" and v.detail.get("dst") == "ghost" for v in vs)


def test_inprogress_is_structurally_sound(tmp_path):
    # proposal+plan only (no EXECUTE/VERIFY): structurally sound. `unverified` is
    # phase-gated and must NOT appear as a structural violation here (T2).
    ws = _ws(
        tmp_path, "r", _prop([{"id": "si-1"}]), _plan([{"id": "wu-1", "derives_from": ["si-1"]}])
    )
    assert validate_graph_projection(ws, "r") == []


def test_contradicted_assessment(tmp_path):
    # A checkpoint that rolled up to 'block' (failing evidence) but a passing assessment over it.
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "block"),  # checkpoint failed (block)
            _verif(
                [{"id": "as-1", "work_unit_id": "wu-1", "evidence_refs": ["cp-1"], "state": "pass"}]
            ),  # but assessment claims pass
        ],
    )
    vs = validate_graph_projection(ws, "r")
    assert any(v.code == "GP_CONTRADICTED" for v in vs)


def test_contradicted_via_obligation_id_join_binds_on_real_data(tmp_path):
    # GN3 council: the REAL assessment<->checkpoint join is the shared obligation_id (evidence_refs is
    # producer-absent free-text). A pass assessment for an obligation whose checkpoint evidence is
    # block must be GP_CONTRADICTED even with NO evidence_refs.
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "block"),  # evidence for obligation ev-1 is block
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),  # no evidence_refs
        ],
    )
    assert "GP_CONTRADICTED" in _codes_set(validate_graph_projection(ws, "r"))
    # non-vacuity: pass evidence for the same obligation -> NOT contradicted
    ws_ok = _ws(
        tmp_path / "ok",
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "pass"),
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
        ],
    )
    assert "GP_CONTRADICTED" not in _codes_set(validate_graph_projection(ws_ok, "r"))


def test_legacy_bare_strings_read_as_uncovered(tmp_path):
    # legacy form (bare-string in_scope, no derives_from) -> all uncovered (flags pre-keys run)
    ws = _ws(tmp_path, "r", _prop(["legacy intent A", "legacy intent B"]), _plan([{"id": "wu-1"}]))
    vs = validate_graph_projection(ws, "r")
    assert sum(1 for v in vs if v.code == "GP_UNCOVERED_INTENT") == 2
    assert any(v.code == "GP_ORPHAN_WORK_UNIT" for v in vs)


def test_never_raises_on_missing_manifest(tmp_path):
    assert validate_graph_projection(tmp_path, "nope") == []


# ====================================================================
# Phase-keyed structural gates (D35): validate_graph_invariants(ws, run, scope)
# runs only the checks whose inputs first exist at that transition gate.
#   plan_exit    -> uncovered / orphan / phantom + obligation-coverage
#   execute_exit -> checkpoint-coverage
#   verify_exit  -> unverified + contradicted
# ====================================================================


def _covered_run(
    tmp_path,
    *,
    obligation=True,
    checkpoint=True,
    assessment=True,
    checkpoint_result="pass",
    assessment_result="pass",
):
    """A run covered through whichever layers are requested (defaults: fully covered).

    proposal si-1 <- plan wu-1 (derives_from) <- piv ev-1 <- exec cp-1 <- verify as-1.
    """
    extra: list = []
    if obligation:
        extra.append(_piv([{"id": "ev-1", "work_unit_id": "wu-1"}]))
    if checkpoint:
        extra.append(_exec("cp-1", "wu-1", checkpoint_result))
    if assessment:
        extra.append(
            _verif(
                [
                    {
                        "id": "as-1",
                        "work_unit_id": "wu-1",
                        "evidence_refs": ["cp-1"],
                        "state": assessment_result,
                    }
                ]
            )
        )
    return _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=extra,
    )


def _codes_set(vs):
    return {v.code for v in vs}


# ---------------------------------------------------------------- plan_exit
def test_plan_exit_blocks_dropped_intent(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}, {"id": "si-2"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[_piv([{"id": "ev-1", "work_unit_id": "wu-1"}])],
    )
    vs = validate_graph_invariants(ws, "r", "plan_exit")
    assert [v.detail.get("scope_item") for v in vs if v.code == "GP_UNCOVERED_INTENT"] == ["si-2"]
    assert all(v.severity == "block" for v in vs)


def test_plan_exit_flags_orphan_and_phantom(tmp_path):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan(
            [
                {"id": "wu-1", "derives_from": ["si-1"]},
                {"id": "wu-x"},  # orphan: no derives_from
                {"id": "wu-2", "derives_from": ["ghost"]},
            ]
        ),  # phantom: ghost si
        extra_docs=[
            _piv(
                [
                    {"id": "ev-1", "work_unit_id": "wu-1"},
                    {"id": "ev-2", "work_unit_id": "wu-x"},
                    {"id": "ev-3", "work_unit_id": "wu-2"},
                ]
            )
        ],
    )
    codes = _codes_set(validate_graph_invariants(ws, "r", "plan_exit"))
    assert "GP_ORPHAN_WORK_UNIT" in codes
    assert "GP_PHANTOM_EDGE" in codes


def test_plan_exit_flags_work_unit_without_obligation(tmp_path):
    ws = _ws(
        tmp_path, "r", _prop([{"id": "si-1"}]), _plan([{"id": "wu-1", "derives_from": ["si-1"]}])
    )  # no evidence_obligation
    vs = validate_graph_invariants(ws, "r", "plan_exit")
    assert any(
        v.code == "GP_WORK_UNIT_NO_OBLIGATION" and v.detail.get("work_unit") == "wu-1" for v in vs
    )


def test_plan_exit_clean_passes_non_vacuously(tmp_path):
    # Non-vacuity guard: the SAME fixture with the obligation removed DOES fire,
    # proving the clean pass is a real pass over a populated graph, not "nothing
    # to check". (The good run really carries si-1 <- wu-1 <- ev-1.)
    broken = validate_graph_invariants(
        _covered_run(tmp_path / "bad", obligation=False), "r", "plan_exit"
    )
    assert any(v.code == "GP_WORK_UNIT_NO_OBLIGATION" for v in broken)
    assert validate_graph_invariants(_covered_run(tmp_path / "ok"), "r", "plan_exit") == []


def test_plan_exit_ignores_later_layer_checks(tmp_path):
    # A run covered through obligations but with NO checkpoint/assessment yet is
    # SOUND at plan_exit — execute/verify-layer codes must NOT appear here.
    ws = _covered_run(tmp_path, checkpoint=False, assessment=False)
    codes = _codes_set(validate_graph_invariants(ws, "r", "plan_exit"))
    assert codes == set()


# ------------------------------------------------------------- execute_exit
def test_execute_exit_flags_work_unit_without_checkpoint(tmp_path):
    ws = _covered_run(tmp_path, checkpoint=False, assessment=False)
    vs = validate_graph_invariants(ws, "r", "execute_exit")
    assert any(
        v.code == "GP_WORK_UNIT_NO_CHECKPOINT" and v.detail.get("work_unit") == "wu-1" for v in vs
    )


def test_execute_exit_clean_passes_non_vacuously(tmp_path):
    # break: drop the checkpoint -> fires; fix: checkpoint present -> silent.
    broken = validate_graph_invariants(
        _covered_run(tmp_path / "bad", checkpoint=False, assessment=False), "r", "execute_exit"
    )
    assert any(v.code == "GP_WORK_UNIT_NO_CHECKPOINT" for v in broken)
    ws = _covered_run(
        tmp_path / "ok", assessment=False
    )  # checkpoint present; assessment not needed
    assert validate_graph_invariants(ws, "r", "execute_exit") == []


# -------------------------------------------------------------- verify_exit
def test_verify_exit_flags_unverified(tmp_path):
    # checkpoint present and passing, but NO passing assessment -> unverified
    ws = _covered_run(tmp_path, assessment=False)
    vs = validate_graph_invariants(ws, "r", "verify_exit")
    assert any(v.code == "GP_UNVERIFIED" and v.detail.get("work_unit") == "wu-1" for v in vs)


def test_verify_exit_failing_assessment_is_unverified(tmp_path):
    # an assessment that did not pass does NOT satisfy verification
    ws = _covered_run(tmp_path, assessment_result="block", checkpoint_result="pass")
    codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
    assert "GP_UNVERIFIED" in codes


def test_verify_exit_flags_contradicted(tmp_path):
    # pass assessment over a FAILED (block) evidence checkpoint -> contradicted
    ws = _covered_run(tmp_path, checkpoint_result="block", assessment_result="pass")
    codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
    assert "GP_CONTRADICTED" in codes


def test_verify_exit_warn_or_deferred_under_pass_is_not_contradicted(tmp_path):
    # GN2 review F1: ONLY `block` is a true contradiction. A pass assessment over a warn/deferred
    # checkpoint is a legitimate close-with-deferred (VALID_NEXT_PHASE_READINESS allows it), NOT a
    # contradiction. Paired with the block case above for non-vacuity.
    for outcome in ("warn", "deferred"):
        ws = _covered_run(tmp_path / outcome, checkpoint_result=outcome, assessment_result="pass")
        codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
        assert "GP_CONTRADICTED" not in codes, (outcome, codes)


def test_verify_exit_clean_passes_non_vacuously(tmp_path):
    # break: drop the passing assessment -> fires unverified; fix -> silent.
    broken = validate_graph_invariants(
        _covered_run(tmp_path / "bad", assessment=False), "r", "verify_exit"
    )
    assert any(v.code == "GP_UNVERIFIED" for v in broken)
    assert validate_graph_invariants(_covered_run(tmp_path / "ok"), "r", "verify_exit") == []


# ------------------------------------------------------- scope / robustness
def test_unknown_scope_is_a_block_violation(tmp_path):
    vs = validate_graph_invariants(_covered_run(tmp_path), "r", "bogus_exit")
    assert len(vs) == 1 and vs[0].severity == "block"
    assert vs[0].code == "GP0_UNKNOWN_SCOPE"


def test_invariants_never_raise_on_missing_manifest(tmp_path):
    assert validate_graph_invariants(tmp_path, "nope", "plan_exit") == []


def test_terminal_projection_unchanged_by_new_checks(tmp_path):
    # validate_graph_projection (closure) must NOT emit the new phase-gated codes
    # (obligation/checkpoint/unverified) — they are transition-gated, not terminal.
    ws = _covered_run(tmp_path, obligation=False, checkpoint=False, assessment=False)
    codes = _codes_set(validate_graph_projection(ws, "r"))
    assert "GP_WORK_UNIT_NO_OBLIGATION" not in codes
    assert "GP_WORK_UNIT_NO_CHECKPOINT" not in codes
    assert "GP_UNVERIFIED" not in codes

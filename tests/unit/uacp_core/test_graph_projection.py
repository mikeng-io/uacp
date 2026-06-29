"""Unit tests for the graph_projection structural-integrity engine (Phase A).

Covers the structural closure checks (always-block) and confirms the progress
check (`unverified`) is NOT emitted (it is phase-gated; final-review T2).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from engines.graph_projection import (
    validate_check_floor,
    validate_graph_invariants,
    validate_graph_projection,
)


def _prop(items: list) -> dict:
    return {"kind": "uacp.proposal", "scope": {"in_scope": items, "out_of_scope": []}}


def _plan(wus: list) -> dict:
    return {"kind": "uacp.plan", "work_units": wus}


def _piv(obls: list) -> dict:
    return {"kind": "uacp.piv", "evidence_obligations": obls}


def _exec(
    checkpoint_id: str,
    work_unit_id: str,
    result: str = "pass",
    checkpoint_type: str = "after_work_unit",
) -> dict:
    # Real execution_checkpoint shape (D42): ONE doc per checkpoint — top-level checkpoint_id +
    # work_unit_id + checkpoint_type + evidence[]; outcome rolls up from evidence[].result. `result`
    # must be a real outcome ({pass,warn,block,deferred}). Only a checkpoint_type=remediation pass
    # clears a prior block.
    return {
        "kind": "uacp.execution_checkpoint",
        "checkpoint_id": checkpoint_id,
        "work_unit_id": work_unit_id,
        "checkpoint_type": checkpoint_type,
        "evidence": [{"obligation_id": "ev-1", "result": result, "summary": "x"}],
    }


def _verif(asmts: list) -> dict:
    return {"kind": "uacp.piv_assessment", "assessments": asmts}


def _check(check_id: str, target: str, kind: str = "uacp.check.field_present") -> dict:
    # A FROZEN uacp.check.* doc (capsule #3). It projects as a `check` node + a
    # `measured_by` edge to its `from.target`. The coverage gate reads only that edge
    # and check-node presence — the bind/expect payload is the replay engine's concern,
    # not coverage's, so it is kept minimal here.
    return {
        "kind": kind,
        "id": check_id,
        "from": {"target": target, "basis": f"{target} proven"},
        "bind": {"plane": "artifact", "ref": {"artifact": "plans/p.yaml", "path": "kind"}},
        "expect": {},
        "severity": "block",
    }


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


def test_remediation_pass_clears_earlier_block_no_contradiction(tmp_path):
    # GN3 external (Kimi #1): a block cleared by a REMEDIATION-checkpoint pass for the same obligation
    # must NOT flag a pass assessment as contradicted.
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "block"),  # initial checkpoint: block
            _exec("cp-2", "wu-1", "pass", checkpoint_type="remediation"),  # remediation: clears it
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
        ],
    )
    assert "GP_CONTRADICTED" not in _codes_set(validate_graph_projection(ws, "r"))


def test_regression_block_after_plain_pass_is_contradicted(tmp_path):
    # GN3 external (Codex P2 r2): order-blind set logic must NOT let an earlier PLAIN pass clear a
    # LATER block. Only a remediation pass clears — a plain pass then a block (regression) on the same
    # obligation, under a pass assessment, IS a contradiction.
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "pass"),  # plain after_work_unit pass (does NOT clear)
            _exec("cp-2", "wu-1", "block"),  # later regression: block
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
        ],
    )
    assert "GP_CONTRADICTED" in _codes_set(validate_graph_projection(ws, "r"))


def test_declared_intents_with_no_coverage_read_as_uncovered(tmp_path):
    # An intent that NOTHING derives from is uncovered whether or not any derives_from
    # edge exists — _check_uncovered fires on scope PRESENCE, matching the projection's
    # contract that a legacy/bare-string scope_item "reads as uncovered, never silently
    # passing it". Here both intents are uncovered (the work_unit declares no derives_from).
    # ORPHAN, by contrast, stays adoption-gated: a work_unit with no derives_from in a run
    # that has adopted NO coverage edges is not flooded as orphan.
    ws = _ws(tmp_path, "r", _prop(["legacy intent A", "legacy intent B"]), _plan([{"id": "wu-1"}]))
    vs = validate_graph_projection(ws, "r")
    assert sum(v.code == "GP_UNCOVERED_INTENT" for v in vs) == 2, [v.code for v in vs]
    assert not any(v.code == "GP_ORPHAN_WORK_UNIT" for v in vs)


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


def test_verify_exit_assessment_without_work_unit_id_binds_via_obligation(tmp_path):
    # GN3 external (Kimi+Codex): a passing assessment carrying only obligation_id (the REAL PIV shape,
    # no work_unit_id) still verifies its work_unit TRANSITIVELY via obligation_for — not GP_UNVERIFIED.
    def _run(state):
        return _ws(
            tmp_path / state,
            "r",
            _prop([{"id": "si-1"}]),
            _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
            extra_docs=[
                _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
                _exec("cp-1", "wu-1", "pass"),
                _verif(
                    [{"id": "as-1", "obligation_id": "ev-1", "state": state}]
                ),  # no work_unit_id
            ],
        )

    assert "GP_UNVERIFIED" not in _codes_set(
        validate_graph_invariants(_run("pass"), "r", "verify_exit")
    )
    # non-vacuity: a non-pass assessment via the same obligation does NOT verify
    assert "GP_UNVERIFIED" in _codes_set(
        validate_graph_invariants(_run("block"), "r", "verify_exit")
    )


def test_verify_exit_clean_passes_non_vacuously(tmp_path):
    # break: drop the passing assessment -> fires unverified; fix -> silent.
    broken = validate_graph_invariants(
        _covered_run(tmp_path / "bad", assessment=False), "r", "verify_exit"
    )
    assert any(v.code == "GP_UNVERIFIED" for v in broken)
    assert validate_graph_invariants(_covered_run(tmp_path / "ok"), "r", "verify_exit") == []


# ------------------------------------------- verify_exit: check-coverage (L1, slice 0b)
# GP_UNCHECKED_TARGET (design node 34 Layer 1): once a run has ADOPTED the generative
# gate (>=1 projected `check` node), EVERY scope_item/work_unit must be `measured_by`
# >=1 check. Self-gates on adoption (like ORPHAN on derives_from) so the existing
# suite — which authors no checks — is never flooded.


def _checked_run(tmp_path, *, checks):
    """A fully-covered run (si-1 <- wu-1 <- ev-1 <- cp-1 <- as-1) plus the given
    uacp.check.* docs, so the check-coverage gate is exercised at verify_exit."""
    return _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "pass"),
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
            *checks,
        ],
    )


def test_verify_exit_blocks_unchecked_target(tmp_path):
    # The gate is adopted (a check measures si-1) but wu-1 is measured_by nothing.
    ws = _checked_run(tmp_path, checks=[_check("chk-1", "si-1")])
    vs = validate_graph_invariants(ws, "r", "verify_exit")
    targets = [v.detail.get("target") for v in vs if v.code == "GP_UNCHECKED_TARGET"]
    assert targets == ["wu-1"], [v.code for v in vs]
    assert all(v.severity == "block" for v in vs if v.code == "GP_UNCHECKED_TARGET")


def test_verify_exit_check_coverage_passes_non_vacuously(tmp_path):
    # break: only si-1 is checked -> wu-1 fires; fix: both checked -> silent.
    broken = validate_graph_invariants(
        _checked_run(tmp_path / "bad", checks=[_check("chk-1", "si-1")]), "r", "verify_exit"
    )
    assert any(v.code == "GP_UNCHECKED_TARGET" for v in broken)
    ok = _checked_run(tmp_path / "ok", checks=[_check("chk-1", "si-1"), _check("chk-2", "wu-1")])
    assert "GP_UNCHECKED_TARGET" not in _codes_set(validate_graph_invariants(ok, "r", "verify_exit"))


def test_verify_exit_check_coverage_self_gates_on_adoption(tmp_path):
    # A fully-covered run with NO check nodes (the entire existing suite shape) must NOT
    # flood GP_UNCHECKED_TARGET — the gate is adoption-gated, like ORPHAN.
    ws = _covered_run(tmp_path)
    assert "GP_UNCHECKED_TARGET" not in _codes_set(
        validate_graph_invariants(ws, "r", "verify_exit")
    )


def _failing_field_equals(check_id: str, target: str) -> dict:
    # binds to the plan doc's `kind` (= "uacp.plan") but expects a wrong value -> FAIL on replay.
    return {
        "kind": "uacp.check.field_equals",
        "id": check_id,
        "from": {"target": target, "basis": f"{target} sets kind"},
        "bind": {"plane": "artifact", "ref": {"artifact": "plans/p.yaml", "path": "kind"}},
        "expect": {"value": "WRONG-VALUE"},
        "severity": "block",
    }


def test_verify_exit_replays_checks_and_blocks_on_failure(tmp_path):
    # Fix C (reviewer): replay runs on the FORCED verify_exit path — a FAILING frozen check
    # blocks the VERIFY exit, not only at closure. Coverage proves a check exists per target;
    # replay proves the checks PASS. Both targets are covered so only the replay FAIL fires.
    ws = _checked_run(
        tmp_path,
        checks=[
            _check("chk-1", "si-1"),
            _check("chk-2", "wu-1"),
            _failing_field_equals("chk-f", "wu-1"),
        ],
    )
    codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
    assert "CHK_FIELD_EQUALS" in codes, codes


def test_verify_exit_flags_phantom_check_target(tmp_path):
    # Fix B (reviewer): a check whose from.target is a ghost node is caught as a phantom edge
    # at the verify_exit gate, not only at terminal closure.
    ws = _checked_run(
        tmp_path,
        checks=[_check("chk-1", "si-1"), _check("chk-2", "wu-1"), _check("chk-g", "GHOST-NODE")],
    )
    codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
    assert "GP_PHANTOM_EDGE" in codes, codes


def test_known_l1_gap_irrelevant_binding_passes_today(tmp_path):
    # KNOWN L1 LIMITATION pinned (mimo #4 + the _check_unchecked_target honest-limit comment):
    # coverage proves a check NAMES each target, NOT that its bind is RELEVANT to it. Here BOTH
    # targets are "covered" by field_present checks binding an UNRELATED-but-present artifact field
    # (plans/p.yaml#kind) — coverage is satisfied AND replay passes, though the checks prove nothing
    # about si-1/wu-1. Closing this is L2 (required-kinds floor) + L3 (council) + the code plane.
    # When L2 lands and entails relevance, THIS test should change (it documents the current gap).
    ws = _checked_run(tmp_path, checks=[_check("chk-1", "si-1"), _check("chk-2", "wu-1")])
    codes = _codes_set(validate_graph_invariants(ws, "r", "verify_exit"))
    assert "GP_UNCHECKED_TARGET" not in codes  # both targets NAMED -> coverage satisfied
    assert not any(c.startswith("CHK_") for c in codes)  # irrelevant-but-present -> replay passes


# ------------------------------------------- the required-kinds FLOOR (L2, slice 2)
# CHK_FLOOR_UNMET (design node 34 Layer 2): a target whose checks declare class X must carry
# >=1 check of a floor[X]-required kind. Closes the weakness coverage can't — a present-but-weak
# check (field_present on a "wire up X" target). The floor self-limits to DECLARED classes; an
# undeclared class places no floor requirement (that omission is Layer 2b's content cross-check).


def _class_check(check_id: str, target: str, cls: str, kind: str) -> dict:
    return {
        "kind": kind,
        "id": check_id,
        "from": {"target": target, "class": cls, "basis": f"{target} is {cls}"},
        "bind": {"plane": "artifact", "ref": {"artifact": "plans/p.yaml", "path": "kind"}},
        "expect": {"value": "uacp.plan"},
        "severity": "block",
    }


def test_floor_unmet_when_class_demands_a_stronger_kind(tmp_path):
    # wu-1's check declares class `sets_value` (floor: field_equals) but is a field_present -> unmet.
    ws = _checked_run(
        tmp_path,
        checks=[_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_present")],
    )
    vs = validate_check_floor(ws, "r")
    unmet = [v.detail.get("target") for v in vs if v.code == "CHK_FLOOR_UNMET"]
    assert unmet == ["wu-1"], [v.code for v in vs]
    assert all(v.severity == "block" for v in vs if v.code == "CHK_FLOOR_UNMET")


def test_floor_met_non_vacuously(tmp_path):
    # break: sets_value target carries only field_present -> unmet; fix: a field_equals -> silent.
    broken = validate_check_floor(
        _checked_run(
            tmp_path / "bad",
            checks=[_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_present")],
        ),
        "r",
    )
    assert any(v.code == "CHK_FLOOR_UNMET" for v in broken)
    ok = _checked_run(
        tmp_path / "ok",
        checks=[_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_FLOOR_UNMET" not in _codes_set(validate_check_floor(ok, "r"))


def test_floor_code_plane_class_blocks_until_wired(tmp_path):
    # a `wires_symbol` target requires uacp.check.symbol_resolves (code plane, not yet authorable),
    # so NO present check satisfies it -> CHK_FLOOR_UNMET, by design (block-until-wired, node 32).
    ws = _checked_run(
        tmp_path,
        checks=[_class_check("chk-1", "wu-1", "wires_symbol", "uacp.check.field_equals")],
    )
    assert "CHK_FLOOR_UNMET" in _codes_set(validate_check_floor(ws, "r"))


def test_load_floor_malformed_entry_keeps_default(tmp_path):
    # MAJOR (kimi): a malformed per-entry value (scalar, not a list) must NOT silently weaken the
    # floor — it falls back to the shipped default for that class (fail-closed, matching the comment).
    from engines.domain.verification_floor import load_floor

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "verification-floor.yaml").write_text(
        "target_class_floor:\n  sets_value: uacp.check.field_present\n", encoding="utf-8"
    )
    floor = load_floor(tmp_path)
    assert floor.get("sets_value") == ("uacp.check.field_equals",)  # default, not the scalar


def test_load_floor_partial_override_keeps_other_defaults(tmp_path):
    # MINOR (kimi+Claude): a partial YAML must not silently DROP the floor for omitted classes.
    # Merge over the default: the listed class is overridden; omitted classes retain their default.
    from engines.domain.verification_floor import load_floor

    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "verification-floor.yaml").write_text(
        "target_class_floor:\n  sets_value: [uacp.check.field_present]\n", encoding="utf-8"
    )
    floor = load_floor(tmp_path)
    assert floor["sets_value"] == ("uacp.check.field_present",)  # explicit override honored
    assert floor.get("wires_symbol") == ("uacp.check.symbol_resolves",)  # default RETAINED


def test_floor_undeclared_class_places_no_requirement(tmp_path):
    # a check with NO from.class -> the floor self-limits (omission is Layer 2b's concern), so a
    # field_present check on wu-1 with no declared class does NOT fire CHK_FLOOR_UNMET.
    ws = _checked_run(tmp_path, checks=[_check("chk-1", "wu-1")])  # _check sets no class
    assert "CHK_FLOOR_UNMET" not in _codes_set(validate_check_floor(ws, "r"))


# ----------------------------------------- Layer 2b: class ENTAILMENT (CHK_CLASS_UNDERCLAIM)
# Derive a candidate class from the target's OWN intent text; if the declared class is WEAKER than
# the content implies, the agent under-classified to satisfy the floor with a weak kind -> block.


def _run_with_intent(tmp_path, intent: str, checks: list) -> Path:
    return _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"], "intent": intent}]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "pass"),
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
            *checks,
        ],
    )


def test_underclaim_when_declared_weaker_than_content(tmp_path):
    # intent "wire up the /settle route" implies wires_symbol, but the check declares sets_value.
    ws = _run_with_intent(
        tmp_path,
        "wire up the /settle route handler",
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    from engines.graph_projection import validate_class_underclaim

    vs = validate_class_underclaim(ws, "r")
    under = [v.detail.get("target") for v in vs if v.code == "CHK_CLASS_UNDERCLAIM"]
    assert under == ["wu-1"], [v.code for v in vs]
    assert all(v.severity == "block" for v in vs if v.code == "CHK_CLASS_UNDERCLAIM")


def test_underclaim_non_vacuous(tmp_path):
    from engines.graph_projection import validate_class_underclaim

    # break: declare sets_value for a "register the route" intent -> underclaim
    broken = validate_class_underclaim(
        _run_with_intent(
            tmp_path / "bad",
            "register the webhook route",
            [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
        ),
        "r",
    )
    assert any(v.code == "CHK_CLASS_UNDERCLAIM" for v in broken)
    # fix: declare wires_symbol (matches content) -> no underclaim
    ok = _run_with_intent(
        tmp_path / "ok",
        "register the webhook route",
        [_class_check("chk-1", "wu-1", "wires_symbol", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(ok, "r"))


def test_underclaim_catches_omitted_class(tmp_path):
    # the omit-from.class dodge: a check with NO declared class on a "wire up" target still
    # underclaims (declared rank 0 < content-implied wires_symbol).
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_intent(
        tmp_path, "mount the /settle route", [_check("chk-1", "wu-1")]  # _check sets no class
    )
    assert "CHK_CLASS_UNDERCLAIM" in _codes_set(validate_class_underclaim(ws, "r"))


def test_underclaim_no_false_fire_on_substring_keywords(tmp_path):
    # MAJOR (council, all 3 reviewers): substring matching false-BLOCKED honest weak-class work
    # whose intent merely CONTAINS a keyword as a substring. Word-boundary matching closes it.
    from engines.graph_projection import validate_class_underclaim

    benign = [
        "configure the list of registered users",  # 'register' in 'registered'
        "reroute the running total into the summary",  # 'route' in 'reroute'
        "compute the router latency metric",  # 'route' in 'router'
    ]
    for i, intent in enumerate(benign):
        ws = _run_with_intent(
            tmp_path / f"b{i}",
            intent,
            [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
        )
        assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(
            validate_class_underclaim(ws, "r")
        ), intent


def test_underclaim_reads_expected_outputs(tmp_path):
    # MAJOR (kimi): node 34 derives the candidate from intent / expected_outputs. Strong content
    # hidden in expected_outputs (bland intent) must still be caught.
    from engines.graph_projection import validate_class_underclaim

    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan(
            [
                {
                    "id": "wu-1",
                    "derives_from": ["si-1"],
                    "intent": "do the settle task",  # bland
                    "expected_outputs": "the /settle route is registered and mounted",  # strong
                }
            ]
        ),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": "wu-1"}]),
            _exec("cp-1", "wu-1", "pass"),
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
            _class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals"),
        ],
    )
    assert "CHK_CLASS_UNDERCLAIM" in _codes_set(validate_class_underclaim(ws, "r"))


def test_no_underclaim_without_strong_keyword(tmp_path):
    # conservative: an intent with no strong keyword does NOT false-fire (a false block is worse
    # than a missed underclaim — Layer 3 owns the residual).
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_intent(
        tmp_path,
        "compute the running total for the invoice",
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(ws, "r"))


def test_check_coverage_is_a_terminal_closure_backstop(tmp_path):
    # Council (opencode, MAJOR): coverage is enforced at the verify_exit TRANSITION, but the
    # closure sweep (run_all_engines -> validate_graph_projection) is the ONE gate that runs on
    # EVERY closure regardless of path. So GP_UNCHECKED_TARGET is ALSO in the terminal set as a
    # backstop — a run that adopted checks but left a target uncovered is caught at closure even if
    # some path bypassed the verify_exit transition. Adoption-gated, so a no-check run stays silent.
    ws = _checked_run(tmp_path, checks=[_check("chk-1", "si-1")])  # wu-1 uncovered
    assert "GP_UNCHECKED_TARGET" in _codes_set(validate_graph_projection(ws, "r"))
    # non-flood: a fully-covered run with NO checks is silent at terminal (adoption-gated)
    clean = _covered_run(tmp_path / "ok")
    assert "GP_UNCHECKED_TARGET" not in _codes_set(validate_graph_projection(clean, "r"))


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
    assert "GP_UNCHECKED_TARGET" not in codes


# ============================================================================================
# PROTOTYPE (class-underclaim grounding retarget) — DARK-REGRESSION DEMONSTRATION
# --------------------------------------------------------------------------------------------
# Decision experiment for the artifact content/relation B1 redesign (MD = semantic content the
# agent comprehends; YAML = relations the code measures). validate_class_underclaim today
# COMPREHENDS in code: it keyword-greps the target's own prose (intent / expected_outputs /
# statement, projection.py:979) to derive a candidate class, then blocks if the declared class is
# weaker. Under B1, that prose relocates to Markdown and leaves the projected node — so the gate
# silently stops firing on a still-genuine underclaim. The council flagged this "dark regression"
# (no test fires) abstractly; this test makes it concrete and runnable. It is the BEFORE half of
# the experiment: it should PASS now (documenting the break) and is the regression the retarget
# (measure a DECLARED relation, not prose) must close.
# ============================================================================================


def test_PROTO_underclaim_dark_regression_when_prose_relocates_to_md(tmp_path):
    from engines.graph_projection import validate_class_underclaim

    # A — TODAY: strong content "wire up the /settle route" lives in YAML intent, but the check
    # declares the weak class sets_value. The gate reads the prose, derives wires_symbol, and FIRES.
    today = _run_with_intent(
        tmp_path / "today",
        "wire up the /settle route handler",
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" in _codes_set(validate_class_underclaim(today, "r"))

    # B — B1: the SAME genuine underclaim, but the strong content has moved to Markdown and is no
    # longer in the projected node (simulated by an empty intent). Same weak declared class.
    # The gate has no prose to grep -> candidate_class("") is None -> it SILENTLY PASSES.
    relocated = _run_with_intent(
        tmp_path / "relocated",
        "",  # prose now lives in MD, invisible to the YAML projection
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(relocated, "r"))

    # The contrast IS the dark regression: identical mis-classification, teeth in A, none in B —
    # and nothing errors. This is exactly the failure the grounding retarget must eliminate.


def _run_with_wu(tmp_path, wu: dict, checks: list) -> Path:
    # Like _run_with_intent, but the caller supplies the whole work_unit dict (so it can set the
    # PROTOTYPE `entailed_class` independent-oracle field alongside / instead of intent prose).
    return _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([wu]),
        extra_docs=[
            _piv([{"id": "ev-1", "work_unit_id": wu["id"]}]),
            _exec("cp-1", wu["id"], "pass"),
            _verif([{"id": "as-1", "obligation_id": "ev-1", "state": "pass"}]),
            *checks,
        ],
    )


def test_PROTO_retarget_restores_teeth_via_entailed_class_without_prose(tmp_path):
    # STEP 3 — the retarget. B1 world: the prose lives in Markdown (intent=""), so the keyword
    # oracle is blind. But an INDEPENDENT oracle (code-plane entailment from the real symbol, or an
    # independent judge reading the MD) entails wires_symbol, carried as the declared relation
    # `entailed_class`. The checks still declare the weak sets_value. The gate fires by MEASURING
    # declared(1) < entailed(3) — with NO prose read. Teeth restored under B1.
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_wu(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "entailed_class": "wires_symbol"},
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    under = [v for v in validate_class_underclaim(ws, "r") if v.code == "CHK_CLASS_UNDERCLAIM"]
    assert [v.detail.get("target") for v in under] == ["wu-1"]
    # ...and it fired on the GROUNDED relation, not on prose:
    assert under[0].detail.get("oracle_source") == "entailed_class"

    # non-vacuity: declare wires_symbol to match the entailed class -> honest -> no underclaim.
    ok = _run_with_wu(
        tmp_path / "ok",
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "entailed_class": "wires_symbol"},
        [_class_check("chk-1", "wu-1", "wires_symbol", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(ok, "r"))


def test_PROTO_independence_is_the_crux_no_oracle_no_catch(tmp_path):
    # STEP 4 — the residual / the load-bearing finding. B1 world with NEITHER prose (it's in MD)
    # NOR an independent `entailed_class`: the gate degrades to the floor and the underclaim catch
    # is GONE. This proves the catch is fundamentally an INDEPENDENCE check — a field the AGENT
    # controls preserves nothing (it would just be declared weak too). So B1 viability for this gate
    # REQUIRES sourcing `entailed_class` independently: code-plane entailment (deterministic,
    # preferred) or an independent judge (semantic). The gate mechanics retarget cleanly; the real
    # dependency is the oracle source.
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_wu(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": ""},  # no prose, no independent oracle
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(ws, "r"))

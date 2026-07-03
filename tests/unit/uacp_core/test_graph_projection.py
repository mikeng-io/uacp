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
    assert "GP_UNCHECKED_TARGET" not in _codes_set(
        validate_graph_invariants(ok, "r", "verify_exit")
    )


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
        tmp_path,
        "mount the /settle route",
        [_check("chk-1", "wu-1")],  # _check sets no class
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
        assert "CHK_CLASS_UNDERCLAIM" not in _codes_set(validate_class_underclaim(ws, "r")), intent


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


# ============================================================================================
# SLICE 1 — anchor primitive (INERT). YAML relation-node carries `anchor: "file.md#id"`; the
# projection records an `anchored_to` edge; an anchor that points at a missing/empty MD section
# is a FAIL (not a silent pass). Nodes WITHOUT an anchor are untouched (zero behavior change).
# ============================================================================================


def _ws_anchor(tmp_path, anchor, md_relpath=None, md_body=None):
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1", "statement": "A", "anchor": anchor}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
    )
    if md_relpath is not None:
        p = tmp_path / ".uacp" / md_relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md_body, encoding="utf-8")
    return ws


def test_anchor_records_anchored_to_edge(tmp_path):
    from engines.manifest.projection import _load_and_project

    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## si-1\nreal content\n")
    graph = _load_and_project(ws, "r")
    assert graph is not None
    _, edges = graph
    assert any(
        e["src"] == "si-1" and e["rel"] == "anchored_to" and e["dst"] == "proposals/a.md#si-1"
        for e in edges
    ), edges


def test_anchor_resolution_pass(tmp_path):
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## si-1\nreal content\n")
    assert validate_anchor_resolution(ws, "r") == []


def test_anchor_resolution_fail_missing_file(tmp_path):
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "proposals/missing.md#si-1")  # no MD written
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws, "r"))


def test_anchor_resolution_fail_missing_section(tmp_path):
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## other\nx\n")
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws, "r"))


def test_anchor_resolution_fail_empty_section(tmp_path):
    from engines.graph_projection import validate_anchor_resolution

    # heading present but body empty (next heading immediately follows) -> FAIL, not silent pass.
    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## si-1\n\n## next\nx\n")
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws, "r"))


def test_anchor_inert_when_absent(tmp_path):
    # No anchor declared -> no anchored_to edge, no anchor violation. Zero behavior change.
    from engines.graph_projection import validate_anchor_resolution
    from engines.manifest.projection import _load_and_project

    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1", "statement": "A"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
    )
    graph = _load_and_project(ws, "r")
    assert graph is not None
    _, edges = graph
    assert not any(e["rel"] == "anchored_to" for e in edges)
    assert validate_anchor_resolution(ws, "r") == []


# ============================================================================================
# SLICE 2 — anchor binding mode for checks (field_present / field_equals).
# A frozen check with `bind.ref.anchor` resolves the anchored MD section and asserts ONLY
# that the section is present and non-empty.  The existing YAML field-path binding is
# untouched when no anchor is present (additive opt-in).
# Violation code for a failing field_present replay: CHK_FIELD_PRESENT.
# ============================================================================================


def _ws_check_anchor(tmp_path, anchor, md_relpath=None, md_body=None):
    """Workspace with a field_present check whose bind uses anchor mode (no artifact key)."""
    check_doc = {
        "kind": "uacp.check.field_present",
        "id": "chk-a",
        "from": {"target": "si-1", "basis": "si-1 present"},
        "bind": {"plane": "artifact", "ref": {"anchor": anchor}},
        "expect": {},
        "severity": "block",
    }
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[check_doc],
    )
    if md_relpath is not None:
        p = tmp_path / ".uacp" / md_relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md_body, encoding="utf-8")
    return ws


def test_anchor_check_field_present_pass_on_resolvable_section(tmp_path):
    # Case 1: anchor points at a real, non-empty section -> replay PASS (no violation).
    from engines.manifest.projection import validate_check_replay

    ws = _ws_check_anchor(
        tmp_path,
        "proposals/a.md#intro",
        "proposals/a.md",
        "## intro\nreal content here\n",
    )
    violations = validate_check_replay(ws, "r")
    chk_violations = [v for v in violations if v.detail.get("check") == "chk-a"]
    assert chk_violations == [], chk_violations


def test_anchor_check_field_present_fail_on_missing_file(tmp_path):
    # Case 2a: anchor target file absent -> replay FAIL -> CHK_FIELD_PRESENT emitted.
    from engines.manifest.projection import validate_check_replay

    ws = _ws_check_anchor(tmp_path, "proposals/missing.md#intro")  # no MD written
    violations = validate_check_replay(ws, "r")
    assert "CHK_FIELD_PRESENT" in _codes_set(violations), violations
    # non-vacuity: contrast with case 1 above (no violation when section resolves).


def test_anchor_check_field_present_fail_on_empty_section(tmp_path):
    # Case 2b: section heading present but body empty -> replay FAIL -> CHK_FIELD_PRESENT.
    from engines.manifest.projection import validate_check_replay

    ws = _ws_check_anchor(
        tmp_path,
        "proposals/a.md#intro",
        "proposals/a.md",
        "## intro\n\n## next\ncontent\n",  # intro body is empty
    )
    violations = validate_check_replay(ws, "r")
    assert "CHK_FIELD_PRESENT" in _codes_set(violations), violations


def test_anchor_check_additive_legacy_artifact_path_pass(tmp_path):
    # Case 3a (additive): a check with the legacy bind.ref.artifact+path (no anchor) still
    # resolves via the YAML field path — anchor mode did not break the existing path.
    from engines.manifest.projection import validate_check_replay

    # _check() produces a field_present binding plans/p.yaml#kind which exists -> PASS.
    ws = _checked_run(tmp_path, checks=[_check("chk-legacy", "si-1")])
    violations = validate_check_replay(ws, "r")
    legacy_v = [v for v in violations if v.detail.get("check") == "chk-legacy"]
    assert legacy_v == [], legacy_v


def test_anchor_check_additive_legacy_artifact_path_fail(tmp_path):
    # Case 3b (additive): a failing legacy field_equals (wrong expected value) still fires
    # CHK_FIELD_EQUALS — anchor mode did not swallow the existing YAML path failure.
    from engines.manifest.projection import validate_check_replay

    ws = _checked_run(tmp_path, checks=[_failing_field_equals("chk-bad", "wu-1")])
    violations = validate_check_replay(ws, "r")
    assert "CHK_FIELD_EQUALS" in _codes_set(violations), violations


# ============================================================================================
# SLICE 1+2 — REVIEW FIXES (council + codex black-box). Reproductions of the findings:
# B1 validate_anchor_resolution unwired; B2 anchored_to trips GP_PHANTOM_EDGE; M3 path traversal;
# M4 subsection-content false-empty; m5 field_equals+anchor degrades; m6 fenced headings; m8 dup.
# These run the FULL wired sweep on an anchored manifest — the coverage the isolated tests missed.
# ============================================================================================


def test_anchor_full_sweep_valid_no_phantom_no_unresolved(tmp_path):
    # B1+B2: a VALID anchored scope_item must NOT trip GP_PHANTOM_EDGE and must pass resolution
    # under the real wired gate (validate_graph_projection), not just the direct validator.
    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## si-1\nreal content\n")
    codes = _codes_set(validate_graph_projection(ws, "r"))
    assert "GP_PHANTOM_EDGE" not in codes, codes
    assert "GP_ANCHOR_UNRESOLVED" not in codes, codes


def test_anchor_full_sweep_broken_caught_not_phantom(tmp_path):
    # B1: a broken anchor FAILs via the wired closure gate; B2: NOT via a phantom-edge false block.
    ws = _ws_anchor(tmp_path, "proposals/missing.md#si-1")  # no MD written
    codes = _codes_set(validate_graph_projection(ws, "r"))
    assert "GP_ANCHOR_UNRESOLVED" in codes, codes
    assert "GP_PHANTOM_EDGE" not in codes, codes


def test_anchor_wired_at_phase_gate(tmp_path):
    # B1: a broken anchor is also caught at a phase-exit gate, not only at closure.
    ws = _ws_anchor(tmp_path, "proposals/missing.md#si-1")
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_graph_invariants(ws, "r", "plan_exit"))


def test_anchor_rejects_path_traversal(tmp_path):
    # M3: an anchor escaping the governed root FAILs even if the outside file exists.
    from engines.graph_projection import validate_anchor_resolution

    (tmp_path / "SECRET.md").write_text("## si-1\nsecret\n", encoding="utf-8")  # OUTSIDE .uacp
    ws = _ws_anchor(tmp_path, "../SECRET.md#si-1")  # no in-namespace md
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws, "r"))


def test_anchor_section_with_subsection_content(tmp_path):
    # M4: content under a deeper subheading counts — the parent section is NOT falsely empty.
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(
        tmp_path,
        "proposals/a.md#si-1",
        "proposals/a.md",
        "## si-1\n### detail\nreal content under a subsection\n",
    )
    assert validate_anchor_resolution(ws, "r") == []


def test_anchor_ignores_heading_in_fenced_code(tmp_path):
    # m6: a heading inside a ``` fence is not a real section.
    from engines.graph_projection import validate_anchor_resolution

    body = "## si-1\n```\n## not-real\n```\nreal content\n"
    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", body)
    assert validate_anchor_resolution(ws, "r") == []
    # anchoring AT the fenced fake heading must FAIL (it is not a section).
    ws2 = _ws_anchor(tmp_path / "b", "proposals/a.md#not-real", "proposals/a.md", body)
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws2, "r"))


def test_anchor_duplicate_heading_first_empty_second_content(tmp_path):
    # m8: first matching heading empty, second has content -> PASS (any matching section non-empty).
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1", "proposals/a.md", "## si-1\n\n## si-1\nbody\n")
    assert validate_anchor_resolution(ws, "r") == []


def test_field_equals_anchor_errors(tmp_path):
    # m5: field_equals + anchor has no presence-only semantics -> ERROR (replay surfaces CHK_FIELD_EQUALS).
    check_doc = {
        "kind": "uacp.check.field_equals",
        "id": "chk-a",
        "from": {"target": "si-1", "basis": "x"},
        "bind": {"plane": "artifact", "ref": {"anchor": "proposals/a.md#si-1"}},
        "expect": {"value": "whatever"},
        "severity": "block",
    }
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[check_doc],
    )
    p = tmp_path / ".uacp" / "proposals" / "a.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("## si-1\nbody\n", encoding="utf-8")
    from engines.graph_projection import validate_check_replay

    vs = validate_check_replay(ws, "r")
    assert any(v.code == "CHK_FIELD_EQUALS" and v.detail.get("status") == "ERROR" for v in vs), vs


def test_anchor_empty_string_is_broken_not_absent(tmp_path):
    # codex re-review (major): an EXPLICITLY declared but empty anchor ("") must FAIL, not silently
    # degrade to "no anchor". Only a truly ABSENT anchor key is inert.
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "")  # anchor: "" declared on si-1, no MD
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_anchor_resolution(ws, "r"))
    # and it surfaces through the wired closure gate too
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(validate_graph_projection(ws, "r"))


def test_check_empty_anchor_is_declared_not_legacy_fallback(tmp_path):
    # codex bot P2 (#70): a check with bind.ref.anchor="" + a valid legacy artifact/path must NOT
    # silently fall back to the legacy binding — a declared-but-empty anchor is broken -> ERROR.
    from engines.graph_projection import validate_check_replay

    check_doc = {
        "kind": "uacp.check.field_present",
        "id": "chk-a",
        "from": {"target": "si-1", "basis": "x"},
        # empty anchor declared ALONGSIDE a legacy artifact/path that would otherwise PASS
        "bind": {
            "plane": "artifact",
            "ref": {"anchor": "", "artifact": "plans/p.yaml", "path": "kind"},
        },
        "expect": {},
        "severity": "block",
    }
    ws = _ws(
        tmp_path,
        "r",
        _prop([{"id": "si-1"}]),
        _plan([{"id": "wu-1", "derives_from": ["si-1"]}]),
        extra_docs=[check_doc],
    )
    vs = validate_check_replay(ws, "r")
    assert any(v.code == "CHK_FIELD_PRESENT" and v.detail.get("status") == "ERROR" for v in vs), vs


def test_anchor_mismatched_fence_marker_stays_fenced(tmp_path):
    # codex P2 #70: a ~~~ line inside a ``` block must NOT close the ``` fence; a heading after it
    # is still inside the code block, not a real section.
    from engines.graph_projection import validate_anchor_resolution

    body = "## si-1\n```\n~~~\n## fake\n```\nreal\n"
    ws = _ws_anchor(tmp_path, "proposals/a.md#fake", "proposals/a.md", body)
    assert "GP_ANCHOR_UNRESOLVED" in _codes_set(
        validate_anchor_resolution(ws, "r")
    )  # #fake is code
    ws2 = _ws_anchor(tmp_path / "b", "proposals/a.md#si-1", "proposals/a.md", body)
    assert validate_anchor_resolution(ws2, "r") == []  # #si-1 still resolves (non-empty body)


def test_malformed_entailed_class_fails_closed(tmp_path):
    # codex P2 #70: a present-but-UNKNOWN entailed_class (typo) must fail closed, not silently
    # degrade to "no oracle" and let a weak declared class pass.
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_wu(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "entailed_class": "wire_symbol"},
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    assert "CHK_ENTAILED_CLASS_INVALID" in _codes_set(validate_class_underclaim(ws, "r"))


def test_anchor_undecodable_markdown_is_error_not_crash(tmp_path):
    # codex P2 #70: invalid UTF-8 in an anchor target raises UnicodeDecodeError (a ValueError, NOT
    # an OSError) — it must be caught and returned as a violation, never escape as an exception.
    from engines.graph_projection import validate_anchor_resolution

    ws = _ws_anchor(tmp_path, "proposals/a.md#si-1")  # anchor declared, write the file ourselves
    p = tmp_path / ".uacp" / "proposals" / "a.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"## si-1\n\xff\xfe not valid utf-8\n")
    codes = _codes_set(validate_anchor_resolution(ws, "r"))  # must NOT raise
    assert "GP_ANCHOR_UNRESOLVED" in codes


def test_malformed_entailed_class_blocks_with_no_checks(tmp_path):
    # codex P2 #70 follow-on: a malformed entailed_class must block even when the target has NO
    # inbound checks yet (pre-adoption / zero-check) — i.e. BEFORE the no-checks early-exit.
    from engines.graph_projection import validate_class_underclaim

    ws = _run_with_wu(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "entailed_class": "wire_symbol"},
        [],  # no checks at all
    )
    assert "CHK_ENTAILED_CLASS_INVALID" in _codes_set(validate_class_underclaim(ws, "r"))


# ============================================================================================
# CLASS WITNESS (design node 03 — witness #2). A scope_item/work_unit declares `code_refs`; the
# gate derives the codeflair connectivity witness ONCE, maps each honored ref's inbound fan-in to
# a class (witness_class), and feeds a RAISE-ONLY max-rank oracle. Driven through a STUB CLI
# resolved from operator config (the FAITHFUL path — proves the trust root reads operator config,
# never derive_witness monkeypatched). Workspace under tmp_path/'ws', stub under tmp_path/'cf' so
# the CLI resolves OUTSIDE the run workspace (the trust root rejects a run-mutable prober).
# ============================================================================================
import json as _cw_json  # noqa: E402
import sys as _cw_sys  # noqa: E402

import engines.io.witnessio as _cw_witnessio  # noqa: E402
from engines.io import clear_witness_memo as _cw_clear_memo  # noqa: E402

_CW_STUB_SRC = (
    "import pathlib, sys\n"
    "here = pathlib.Path(__file__).resolve().parent\n"
    "with (here / 'calls.log').open('a') as _f:\n"
    "    _f.write('x')\n"
    "sys.stdout.write((here / 'fixture.json').read_text())\n"
)


def _cw_fixture(
    *,
    symbols_touched=None,
    declared=None,
    neighborhood=None,
    inbound_counts=None,
    ingestion="scip",
):
    return {
        "graph_stamp": {"commit": "deadbeef", "tree_token": "t1"},
        "ingestion": ingestion,
        "symbols_touched": [{"file": f, "name": n} for f, n in (symbols_touched or [])],
        "neighborhood": neighborhood or [],
        "declared": declared or [],
        "unresolved_touched": [],
        "inbound_counts": inbound_counts or {},
    }


def _cw_configure(monkeypatch, tmp_path, fixture):
    """Install the stub CLI + fixture under tmp_path/'cf' (outside the workspace root) and point
    the KERNEL-DEFAULT [witness].codeflair_cli at it. Returns the calls.log path (created iff the
    stub actually runs). Clears the process-global witness memo for isolation."""
    cf = tmp_path / "cf"
    cf.mkdir(parents=True, exist_ok=True)
    (cf / "stub.py").write_text(_CW_STUB_SRC)
    (cf / "fixture.json").write_text(_cw_json.dumps(fixture))
    op = tmp_path / "operator-uacp.toml"
    cli = f"{_cw_json.dumps(_cw_sys.executable)[1:-1]} {cf / 'stub.py'}"
    op.write_text(f"[witness]\ncodeflair_cli = {_cw_json.dumps(cli)}\n")
    monkeypatch.setattr(_cw_witnessio, "_operator_config_path", lambda: op)
    _cw_clear_memo()
    return cf / "calls.log"


def _cw_unconfigure(monkeypatch, tmp_path):
    """Point operator config at a toml with NO [witness] table -> witness UNCONFIGURED
    (deterministic 'not configured' unavailable, independent of the repo's real config)."""
    op = tmp_path / "operator-empty.toml"
    op.write_text("[other]\nx = 1\n")
    monkeypatch.setattr(_cw_witnessio, "_operator_config_path", lambda: op)
    _cw_clear_memo()


def _cw_ws(tmp_path, wu, checks):
    # Workspace under tmp_path/'ws' (disjoint from the stub at tmp_path/'cf').
    return _run_with_wu(tmp_path / "ws", wu, checks)


def _cw_codes(vs):
    return {v.code for v in vs}


# ---------------------------------------------------------------- deliverable 1: projection carry
def test_code_refs_carry_onto_nodes_and_defensive_none(tmp_path):
    from engines.manifest.projection import _load_and_project

    ws = _ws(
        tmp_path,
        "r",
        _prop(
            [
                {"id": "si-1", "statement": "x", "code_refs": [{"file": "a.py", "name": "A"}]},
                {"id": "si-2", "statement": "y", "code_refs": "bogus"},  # not a list -> None
            ]
        ),
        _plan(
            [
                {
                    "id": "wu-1",
                    "derives_from": ["si-1"],
                    "code_refs": [{"file": "b.py", "name": "B"}],
                },
                {
                    "id": "wu-2",
                    "derives_from": ["si-2"],
                    "code_refs": [{"name": "noFile"}],
                },  # -> None
            ]
        ),
    )
    nodes, _ = _load_and_project(ws, "r")
    assert nodes["si-1"]["code_refs"] == [{"file": "a.py", "name": "A"}]
    assert nodes["si-2"]["code_refs"] is None
    assert nodes["wu-1"]["code_refs"] == [{"file": "b.py", "name": "B"}]
    assert nodes["wu-2"]["code_refs"] is None  # missing 'file' -> malformed -> None


# ---------------------------------------------------------------- deliverable 2: heuristic branches
def test_witness_class_heuristic_branches():
    from engines.domain.verification_floor import witness_class

    assert witness_class(0) == "sets_value"  # no inbound
    assert witness_class(1) == "wires_symbol"  # wired-in
    assert witness_class(5) == "wires_symbol"
    assert witness_class(31) == "wires_symbol"  # just under the broad bound
    assert witness_class(32) == "changes_behavior"  # broad fan-in (default bound)
    assert witness_class(200) == "changes_behavior"
    assert witness_class(3, broad_bound=2) == "changes_behavior"  # bound is a parameter
    # never expresses ensures_obligation (rank 2) — connectivity cannot say obligation.
    assert "ensures_obligation" not in {witness_class(n) for n in range(0, 100)}
    # defensive: a garbled/negative count degrades to the weakest class, never raises.
    assert witness_class(-1) == "sets_value"


# heuristic branches THROUGH the gate oracle (witness class becomes the code_witness oracle) -----
def _cw_underclaim_branch(tmp_path, monkeypatch, *, inbound):
    # A wu with one touched, declared code_ref at `inbound` fan-in and a NO-CLASS check (rank 0),
    # no prose, no entailed_class -> the witness class is the sole oracle; underclaim names it.
    fixture = _cw_fixture(
        symbols_touched=[("m.py", "Sym")],
        declared=[{"file": "m.py", "name": "Sym", "resolved": True}],
        inbound_counts={"m.py:Sym": inbound},
    )
    _cw_configure(monkeypatch, tmp_path, fixture)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "code_refs": [{"file": "m.py", "name": "Sym"}],
        },
        [_check("chk-1", "wu-1")],  # no declared class -> rank 0
    )
    from engines.graph_projection import validate_class_underclaim

    return [v for v in validate_class_underclaim(ws, "r") if v.code == "CHK_CLASS_UNDERCLAIM"]


def test_witness_branch_zero_inbound_is_sets_value(tmp_path, monkeypatch):
    hits = _cw_underclaim_branch(tmp_path, monkeypatch, inbound=0)
    assert [h.detail.get("candidate") for h in hits] == ["sets_value"]
    assert hits[0].detail.get("oracle_source") == "code_witness"


def test_witness_branch_one_inbound_is_wires_symbol(tmp_path, monkeypatch):
    hits = _cw_underclaim_branch(tmp_path, monkeypatch, inbound=1)
    assert [h.detail.get("candidate") for h in hits] == ["wires_symbol"]
    assert hits[0].detail.get("oracle_source") == "code_witness"


def test_witness_branch_broad_inbound_is_changes_behavior(tmp_path, monkeypatch):
    hits = _cw_underclaim_branch(tmp_path, monkeypatch, inbound=40)
    assert [h.detail.get("candidate") for h in hits] == ["changes_behavior"]
    assert hits[0].detail.get("oracle_source") == "code_witness"


# ---------------------------------------------------------------- (vi) witness RAISES the oracle
def test_witness_raises_oracle_to_underclaim(tmp_path, monkeypatch):
    # weak declared checks + a broad-fan-in witness -> CHK_CLASS_UNDERCLAIM via code_witness.
    from engines.graph_projection import validate_class_underclaim

    fixture = _cw_fixture(
        symbols_touched=[("m.py", "Core")],
        declared=[{"file": "m.py", "name": "Core", "resolved": True}],
        inbound_counts={"m.py:Core": 65},
    )
    _cw_configure(monkeypatch, tmp_path, fixture)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "code_refs": [{"file": "m.py", "name": "Core"}],
        },
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],  # weak
    )
    hits = [v for v in validate_class_underclaim(ws, "r") if v.code == "CHK_CLASS_UNDERCLAIM"]
    assert [h.detail.get("target") for h in hits] == ["wu-1"]
    assert hits[0].detail.get("candidate") == "changes_behavior"
    assert hits[0].detail.get("oracle_source") == "code_witness"


# ---------------------------------------------------------------- (i) untouched declared ref
def test_untouched_declared_ref_derives_nothing(tmp_path, monkeypatch):
    # The declared ref is NOT in symbols_touched -> CHK_CLASS_REF_UNTOUCHED, and it must NOT be
    # class-derived (an untouched strong symbol cannot manufacture an oracle / false underclaim).
    from engines.graph_projection import validate_class_underclaim

    fixture = _cw_fixture(
        symbols_touched=[("other.py", "Unrelated")],  # the declared ref is absent from the diff
        declared=[{"file": "big.py", "name": "Hub", "resolved": True}],
        inbound_counts={"other.py:Unrelated": 0},
    )
    _cw_configure(monkeypatch, tmp_path, fixture)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "code_refs": [{"file": "big.py", "name": "Hub"}],
        },
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],  # weak
    )
    vs = validate_class_underclaim(ws, "r")
    codes = _cw_codes(vs)
    assert "CHK_CLASS_REF_UNTOUCHED" in codes
    untouched = [v for v in vs if v.code == "CHK_CLASS_REF_UNTOUCHED"]
    assert untouched[0].detail.get("refs") == ["big.py:Hub"]
    assert all(v.severity == "warn" for v in untouched)
    # NOT class-derived: no false underclaim from the untouched ref.
    assert "CHK_CLASS_UNDERCLAIM" not in codes


# ---------------------------------------------------------------- (ii) raise-only, no false block
def test_raise_only_weak_witness_no_false_underclaim(tmp_path, monkeypatch):
    # entailed_class + the checks correctly declare changes_behavior; a weak witness (sets_value)
    # must NOT create a false underclaim (the oracle is a max, never lowered), but the disagreement
    # is surfaced: CHK_ENTAILED_CLASS_SUPERSEDED, with changes_behavior governing (max-rank).
    from engines.graph_projection import validate_class_underclaim

    fixture = _cw_fixture(
        symbols_touched=[("m.py", "Leaf")],
        declared=[{"file": "m.py", "name": "Leaf", "resolved": True}],
        inbound_counts={"m.py:Leaf": 0},  # -> sets_value (weak)
    )
    _cw_configure(monkeypatch, tmp_path, fixture)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "entailed_class": "changes_behavior",
            "code_refs": [{"file": "m.py", "name": "Leaf"}],
        },
        [
            _class_check("chk-1", "wu-1", "changes_behavior", "uacp.check.behavioral")
        ],  # correct/strong
    )
    vs = validate_class_underclaim(ws, "r")
    codes = _cw_codes(vs)
    assert "CHK_CLASS_UNDERCLAIM" not in codes  # correctly declared -> no false block
    superseded = [v for v in vs if v.code == "CHK_ENTAILED_CLASS_SUPERSEDED"]
    assert superseded and superseded[0].detail.get("governs") == "changes_behavior"
    assert all(v.severity == "warn" for v in superseded)


# ---------------------------------------------------------------- (iii) ensures_obligation preserved
def test_ensures_obligation_not_downranked_by_weak_witness(tmp_path, monkeypatch):
    # entailed_class ensures_obligation (rank 2) + weak witness (sets_value, rank 1): the witness
    # cannot express rank 2, and raise-only means the oracle STAYS at ensures_obligation. A weak
    # (sets_value) declared check therefore still underclaims, via entailed_class — not via witness.
    from engines.graph_projection import validate_class_underclaim

    fixture = _cw_fixture(
        symbols_touched=[("m.py", "Guard")],
        declared=[{"file": "m.py", "name": "Guard", "resolved": True}],
        inbound_counts={"m.py:Guard": 0},  # sets_value
    )
    _cw_configure(monkeypatch, tmp_path, fixture)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "entailed_class": "ensures_obligation",
            "code_refs": [{"file": "m.py", "name": "Guard"}],
        },
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],  # weak
    )
    vs = validate_class_underclaim(ws, "r")
    hits = [v for v in vs if v.code == "CHK_CLASS_UNDERCLAIM"]
    assert hits and hits[0].detail.get("candidate") == "ensures_obligation"
    assert hits[0].detail.get("oracle_source") == "entailed_class"  # oracle rank stayed at 2
    # the disagreement is still surfaced.
    assert "CHK_ENTAILED_CLASS_SUPERSEDED" in _cw_codes(vs)


# ---------------------------------------------------------------- (iv) unavailability
def test_witness_unavailable_falls_back_visibly(tmp_path, monkeypatch):
    # code_refs declared but the CLI is UNCONFIGURED -> CHK_CLASS_WITNESS_UNAVAILABLE (once), and
    # the legacy two-source oracle still works (entailed_class fires the underclaim).
    from engines.graph_projection import validate_class_underclaim

    _cw_unconfigure(monkeypatch, tmp_path)
    ws = _cw_ws(
        tmp_path,
        {
            "id": "wu-1",
            "derives_from": ["si-1"],
            "intent": "",
            "entailed_class": "wires_symbol",
            "code_refs": [{"file": "m.py", "name": "Sym"}],
        },
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],  # weak
    )
    vs = validate_class_underclaim(ws, "r")
    unavail = [v for v in vs if v.code == "CHK_CLASS_WITNESS_UNAVAILABLE"]
    assert len(unavail) == 1 and unavail[0].severity == "warn"  # fired ONCE, visible
    # legacy oracle intact: entailed_class still catches the underclaim.
    hits = [v for v in vs if v.code == "CHK_CLASS_UNDERCLAIM"]
    assert hits and hits[0].detail.get("oracle_source") == "entailed_class"


# ---------------------------------------------------------------- (v) no code_refs -> CLI silent
def test_no_code_refs_never_invokes_cli(tmp_path, monkeypatch):
    # No target declares code_refs: the CLI must NEVER be invoked (side-effect calls.log absent),
    # and NO class-witness code appears — byte-identical to the pre-witness gate.
    from engines.graph_projection import validate_class_underclaim

    calls_log = _cw_configure(tmp_path=tmp_path, monkeypatch=monkeypatch, fixture=_cw_fixture())
    ws = _cw_ws(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "entailed_class": "wires_symbol"},
        [_class_check("chk-1", "wu-1", "sets_value", "uacp.check.field_equals")],
    )
    vs = validate_class_underclaim(ws, "r")
    assert not calls_log.exists(), "CLI was invoked despite no code_refs"
    new_codes = {
        "CHK_CLASS_REF_UNTOUCHED",
        "CHK_ENTAILED_CLASS_SUPERSEDED",
        "CHK_CLASS_WITNESS_UNAVAILABLE",
    }
    assert _cw_codes(vs) & new_codes == set()
    # the pre-witness gate still fires on entailed_class alone (byte-identical).
    assert "CHK_CLASS_UNDERCLAIM" in _cw_codes(vs)


def test_malformed_code_refs_never_invokes_cli(tmp_path, monkeypatch):
    # Malformed code_refs (defensive read) carry as None -> treated as no claim -> CLI never runs.
    from engines.graph_projection import validate_class_underclaim

    calls_log = _cw_configure(tmp_path=tmp_path, monkeypatch=monkeypatch, fixture=_cw_fixture())
    ws = _cw_ws(
        tmp_path,
        {"id": "wu-1", "derives_from": ["si-1"], "intent": "", "code_refs": "not-a-list"},
        [_check("chk-1", "wu-1")],
    )
    vs = validate_class_underclaim(ws, "r")
    assert not calls_log.exists()
    assert "CHK_CLASS_WITNESS_UNAVAILABLE" not in _cw_codes(vs)


# ---------------------------------------------------------------- fallback: calls/refs, not defines
def test_fallback_counts_calls_references_not_defines(tmp_path, monkeypatch):
    # inbound_counts OMITTED for the touched symbol -> fallback to neighborhood. A `defines`-only
    # inbound edge counts 0 (-> sets_value); a `calls` inbound edge counts 1 (-> wires_symbol).
    from engines.graph_projection import validate_class_underclaim

    def _run(neighborhood):
        fixture = _cw_fixture(
            symbols_touched=[("m.py", "C.method")],
            declared=[{"file": "m.py", "name": "C.method", "resolved": True}],
            neighborhood=neighborhood,
            inbound_counts={},  # empty -> force the fallback path
        )
        _cw_configure(monkeypatch, tmp_path / neighborhood[0]["reason"], fixture)
        ws = _cw_ws(
            tmp_path / neighborhood[0]["reason"],
            {
                "id": "wu-1",
                "derives_from": ["si-1"],
                "intent": "",
                "code_refs": [{"file": "m.py", "name": "C.method"}],
            },
            [_check("chk-1", "wu-1")],  # no class -> witness is the sole oracle
        )
        return [v for v in validate_class_underclaim(ws, "r") if v.code == "CHK_CLASS_UNDERCLAIM"]

    defines_only = [
        {
            "src": {"file": "m.py", "name": "C"},
            "dst": {"file": "m.py", "name": "C.method"},
            "reason": "defines",
        }
    ]
    assert [h.detail.get("candidate") for h in _run(defines_only)] == ["sets_value"]

    calls_edge = [
        {
            "src": {"file": "x.py", "name": "caller"},
            "dst": {"file": "m.py", "name": "C.method"},
            "reason": "calls",
        }
    ]
    assert [h.detail.get("candidate") for h in _run(calls_edge)] == ["wires_symbol"]

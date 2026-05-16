#!/usr/bin/env python3
"""Phase 1 behavioural verification for the UACP Guardian patch plan.

Exercises:
  - self_attesting_tools loaded from policy (pc_1)
  - uacp_gate_ledger_append append-only and refusal cases (Item 1.1)
  - per-phase Layer B admissibility: forbidden_tools blocks, allowed_tools allowlist misses block (Item 1.3)
  - phase_exit_invariants enforcement: Heartgate blocks transition when required artifact glob is missing (Item 1.2)
  - PIV record requirement and double-failure unconditional block (Item 1.4)
  - quick wins pc_4 (empty tool_name blocks in all modes), pc_5 (state.uacp / general-branch mutual exclusivity), pc_6 (audit-reason consistency)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path


def _import_plugin():
    here = Path(__file__).resolve().parent.parent
    plugins_root = here / "runtime-adapters" / "hermes" / "plugins"
    sys.path.insert(0, str(plugins_root))
    import uacp_guardian as plugin
    from uacp_guardian.kernel import Guardian, GuardianPolicy, Heartgate, make_event
    return plugin, Guardian, GuardianPolicy, Heartgate, make_event


def _prepare_root(tmp: Path) -> None:
    here = Path(__file__).resolve().parent.parent
    for sub in ("config", "docs", "state/runs", "state/gate-ledger",
                "plans", "proposals", "executions", "verification", "outputs", "knowledge"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(here / "config/guardian-policy.yaml", tmp / "config/guardian-policy.yaml")
    shutil.copy2(here / "config/phase-transitions.yaml", tmp / "config/phase-transitions.yaml")
    shutil.copy2(here / "config/state.yaml", tmp / "config/state.yaml")


def _reload(plugin) -> None:
    plugin._POLICY = None
    plugin._POLICY_ERROR = ""
    plugin._PHASE_CONFIG = None


def _common_args(tmp: Path, phase: str = "execute") -> dict:
    return {
        "workspace": str(tmp),
        "uacp_run_id": "phase1-verify",
        "uacp_phase": phase,
        "policy_version": "0.1",
        "declared_side_effects": "phase1 verification writes",
        "authority_artifact": "verification/phase1-verify.yaml",
    }


def main() -> int:
    plugin, Guardian, GuardianPolicy, Heartgate, make_event = _import_plugin()
    report: dict = {"checks": []}
    saved_env = {k: os.environ.get(k) for k in ("UACP_ROOT", "UACP_GUARDIAN_MODE", "UACP_PHASE", "UACP_RUN_ID")}

    try:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            _prepare_root(tmp)
            os.environ["UACP_ROOT"] = str(tmp)
            os.environ.pop("UACP_GUARDIAN_MODE", None)
            os.environ.pop("UACP_PHASE", None)
            os.environ.pop("UACP_RUN_ID", None)
            _reload(plugin)

            policy = plugin._policy()

            # --- Check 1: self_attesting_tools loaded from policy (pc_1) ---
            expected = {"uacp_state_write", "uacp_doc_write", "uacp_config_write",
                        "uacp_artifact_write", "uacp_sandbox_check", "uacp_heartgate_check",
                        "uacp_contained_shell", "uacp_gate_ledger_append"}
            report["checks"].append({
                "name": "self_attesting_tools_loaded_from_policy",
                "status": "pass" if expected.issubset(set(policy.self_attesting_tools)) else "fail",
                "loaded": sorted(policy.self_attesting_tools),
            })

            # --- Check 2: uacp_gate_ledger_append writes append-only ---
            common = _common_args(tmp, phase="execute")
            result = json.loads(plugin._handle_uacp_gate_ledger_append({
                **common,
                "gate": "PHASE1_VERIFY_PROBE",
                "record": {"result": "pass", "phase": "execute"},
            }))
            ledger_path = tmp / "state/gate-ledger/phase1-verify.jsonl"
            report["checks"].append({
                "name": "gate_ledger_append_writes_record",
                "status": "pass" if (result.get("ok") and ledger_path.exists()) else "fail",
                "result": result,
            })
            # Append a second record and confirm both lines present in order.
            plugin._handle_uacp_gate_ledger_append({
                **common,
                "gate": "PHASE1_VERIFY_PROBE_2",
                "record": {"result": "pass"},
            })
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            report["checks"].append({
                "name": "gate_ledger_append_only_two_records",
                "status": "pass" if len(lines) == 2 else "fail",
                "lines_count": len(lines),
            })
            # JSON encoding escapes newlines automatically; verify by writing a
            # value with embedded newlines and confirming the JSONL line count
            # remains 3 (was 2, plus this one).
            plugin._handle_uacp_gate_ledger_append({
                **common,
                "gate": "WITH_NEWLINES_IN_VALUE",
                "record": {"note": "line one\nline two"},
            })
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            report["checks"].append({
                "name": "gate_ledger_json_encoding_preserves_one_record_per_line",
                "status": "pass" if len(lines) == 3 else "fail",
                "lines_count": len(lines),
            })
            # Reject path-traversal run_id.
            bad2 = json.loads(plugin._handle_uacp_gate_ledger_append({
                **common,
                "uacp_run_id": "../escape",
                "gate": "ESCAPE",
                "record": {},
            }))
            report["checks"].append({
                "name": "gate_ledger_rejects_path_traversal_run_id",
                "status": "pass" if bad2.get("error") else "fail",
            })

            # --- Check 3: per-phase Layer B forbids non-listed tool ---
            # In TRIAGE phase, terminal is forbidden. Even with synthetic
            # filesystem_guard_verified=True, Layer B must block.
            event = make_event(
                tool_name="terminal",
                args={**_common_args(tmp, phase="triage"), "command": "echo hi"},
                filesystem_guard_verified=True,
            )
            decision = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
            report["checks"].append({
                "name": "layer_b_forbids_terminal_in_triage",
                "status": "pass" if (decision.blocks_execution and "forbidden in phase" in decision.reason) else "fail",
                "reason": decision.reason,
            })

            # --- Check 4: per-phase Layer B allowlist miss blocks ---
            # uacp_artifact_write is allowed in PLAN; uacp_contained_shell is NOT in PLAN's allowlist.
            event = make_event(
                tool_name="uacp_contained_shell",
                args={**_common_args(tmp, phase="plan"), "command": "x", "workspace": str(tmp.parent)},
                filesystem_guard_verified=True,
            )
            decision = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
            report["checks"].append({
                "name": "layer_b_allowlist_miss_blocks",
                "status": "pass" if (decision.blocks_execution and "not in phase" in decision.reason) else "fail",
                "reason": decision.reason,
            })

            # --- Check 5: per-phase Layer B admits listed tool ---
            event = make_event(
                tool_name="uacp_artifact_write",
                args={**_common_args(tmp, phase="plan"), "target_path": "plans/p.yaml", "content": "a: 1\n"},
                filesystem_guard_verified=True,
            )
            decision = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
            report["checks"].append({
                "name": "layer_b_admits_listed_tool",
                "status": "pass" if not decision.blocks_execution else "fail",
                "decision": decision.decision,
                "category": decision.category,
                "reason": decision.reason,
            })

            # --- Check 6: phase_exit_invariants — missing artifact blocks transition ---
            heartgate = Heartgate.load(tmp)
            def _full_artifact(from_phase: str, to_phase: str) -> dict:
                return {
                    "kind": "uacp.phase_transition",
                    "transition_id": f"phase1-verify-{from_phase}-to-{to_phase}",
                    "run_id": "phase1-verify",
                    "from_phase": from_phase,
                    "to_phase": to_phase,
                    "decision": "pass",
                    "invariant_summary": [],
                    "cluster_summary": [],
                    "blockers": [],
                    "warnings": [],
                    "deferred_items": [],
                    "authority": {"requested_by": "operator", "authorization_source": "test"},
                    "artifact_paths": [],
                    "phase_local_granularity": {"phase": from_phase, "entry_estimate": 5, "exit_actual": 5, "delta_reason": "test", "downstream_projection": {}},
                    "composite_granularity": 5,
                    "human_involvement": {"required": False, "reason": "test", "authority_needed": "none", "decision_owner": "none", "accepted_risk_artifact": ""},
                }
            artifact_missing = _full_artifact("plan", "execute")
            d = heartgate.validate_transition(artifact_missing)
            report["checks"].append({
                "name": "phase_exit_invariants_block_when_artifact_missing",
                "status": "pass" if (d.blocks_transition and any("phase_exit_invariant" in b for b in d.blockers)) else "fail",
                "blockers": d.blockers,
            })

            # --- Check 7: phase_exit_invariants — artifact present + ledger present passes ---
            (tmp / "plans/phase1-verify-plan.yaml").write_text("a: 1\n")
            # Inject the required gate-ledger entry.
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="plan"),
                "gate": "PROPOSE->PLAN",
                "record": {"result": "pass", "phase": "plan"},
            })
            # And a PIV pass for plan phase.
            # Global review R1 (SKEP-G-002): PIV ledger records must carry
            # explicit piv_id coverage with per-check pass evidence.
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="plan"),
                "gate": "PIV",
                "record": {
                    "phase": "plan",
                    "result": "pass",
                    "piv_attempt": 1,
                    "checks": ["piv_1", "piv_2", "piv_3", "piv_4", "piv_5"],
                    "check_results": {"piv_1": "pass", "piv_2": "pass", "piv_3": "pass", "piv_4": "pass", "piv_5": "pass"},
                },
            })
            # Phase 3.1: PLAN_VALIDATION gate (plan->execute transitions now require this).
            # Phase 3 R1: ledger record must carry all six pv_ids in `checks`.
            # Phase 3 R2 (SKEP-R1-003): explicit per-check pass evidence via check_results sibling.
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="plan"),
                "gate": "PLAN_VALIDATION",
                "record": {
                    "phase": "plan",
                    "result": "pass",
                    "checks": ["pv_1", "pv_2", "pv_3", "pv_4", "pv_5", "pv_6"],
                    "check_results": {"pv_1": "pass", "pv_2": "pass", "pv_3": "pass", "pv_4": "pass", "pv_5": "pass", "pv_6": "pass"},
                },
            })
            d = heartgate.validate_transition(artifact_missing)
            report["checks"].append({
                "name": "phase_exit_invariants_pass_when_artifact_and_ledger_present",
                "status": "pass" if not d.blocks_transition else "fail",
                "blockers": d.blockers,
                "decision": d.decision,
            })

            # --- Check 8: PIV double-failure unconditional block ---
            # Append 2 failing PIV attempts for execute phase, then check
            # plan→execute? No — PIV is checked for from_phase. Use execute→verify.
            (tmp / "executions/phase1-verify-exec.yaml").write_text("a: 1\n")
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="execute"),
                "gate": "PLAN->EXECUTE",
                "record": {"result": "pass", "phase": "execute"},
            })
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="execute"),
                "gate": "PIV",
                "record": {"phase": "execute", "result": "fail", "piv_attempt": 1, "checks": ["piv_2 failed"]},
            })
            plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="execute"),
                "gate": "PIV",
                "record": {"phase": "execute", "result": "fail", "piv_attempt": 2, "checks": ["piv_2 failed again"]},
            })
            artifact_e2v = _full_artifact("execute", "verify")
            d = heartgate.validate_transition(artifact_e2v)
            report["checks"].append({
                "name": "piv_double_failure_blocks_unconditionally",
                "status": "pass" if (d.blocks_transition and any("second-failure" in b for b in d.blockers)) else "fail",
                "blockers": d.blockers,
            })

            # --- Check 9: pc_4 empty tool_name blocks in both modes ---
            for mode in ("enforce", "observe"):
                if mode == "observe":
                    import yaml as _yaml
                    pp = tmp / "config/guardian-policy.yaml"
                    data = _yaml.safe_load(pp.read_text())
                    data["mode"] = "observe"
                    pp.write_text(_yaml.safe_dump(data, sort_keys=False))
                    _reload(plugin)
                    policy = plugin._policy()
                event = make_event(tool_name="", args=_common_args(tmp))
                d = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
                report["checks"].append({
                    "name": f"pc_4_empty_tool_name_blocks_in_{mode}",
                    "status": "pass" if d.blocks_execution else "fail",
                    "decision": d.decision,
                    "reason": d.reason,
                })

            # restore enforce
            import yaml as _yaml
            pp = tmp / "config/guardian-policy.yaml"
            data = _yaml.safe_load(pp.read_text())
            data["mode"] = "enforce"
            pp.write_text(_yaml.safe_dump(data, sort_keys=False))
            _reload(plugin)
            policy = plugin._policy()

            # --- Check 10: pc_6 audit-reason consistency for read-only governed categories ---
            event = make_event(
                tool_name="uacp_sandbox_check",
                args={**_common_args(tmp, phase="verify"), "execution_workspace": str(tmp.parent), "tool_surface": "exec.shell"},
                filesystem_guard_verified=True,
            )
            d = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
            report["checks"].append({
                "name": "pc_6_consistent_audit_reason_for_evidence_containment",
                "status": "pass" if ("authorized governed tool" in d.reason and d.category == "evidence.containment") else "fail",
                "reason": d.reason,
                "category": d.category,
            })

            # --- Check 11: pc_5 state.uacp branch is exclusive (no double-fire) ---
            event = make_event(
                tool_name="uacp_state_write",
                args={**_common_args(tmp, phase="execute"), "target_path": "state/runs/probe.yaml", "content": "a: 1\n"},
                filesystem_guard_verified=True,
            )
            d = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
            report["checks"].append({
                "name": "pc_5_state_uacp_takes_state_branch_not_general",
                "status": "pass" if (not d.blocks_execution and d.category == "state.uacp" and "guarded UACP state mutation" in d.reason) else "fail",
                "decision": d.decision,
                "category": d.category,
                "reason": d.reason,
            })

            # --- Remediation R1 (skeptic F1): uacp_state_write refuses state/gate-ledger/ ---
            # pc_p1_t1 (Phase 2 propagated): assert the SPECIFIC gate-ledger
            # refusal branch fires, not just any error.
            forge = json.loads(plugin._handle_uacp_state_write({
                **_common_args(tmp, phase="execute"),
                "reason": "phase1 verify R1 forge attempt",
                "target_path": "state/gate-ledger/forged.jsonl",
                "content": json.dumps({"gate": "PIV", "result": "pass", "phase": "execute", "piv_attempt": 1, "run_id": "phase1-verify"}) + "\n",
            }))
            err = forge.get("error") or ""
            report["checks"].append({
                "name": "remediation_R1_state_write_refuses_gate_ledger",
                "status": "pass" if "may not write under state/gate-ledger/" in err else "fail",
                "error": err,
            })

            # --- Remediation R2 (skeptic F2): policy validator rejects poisoned self_attesting_tools ---
            import yaml as _y
            pp = tmp / "config/guardian-policy.yaml"
            data = _y.safe_load(pp.read_text())
            data["self_attesting_tools"]["names"].append("terminal")
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            _reload(plugin)
            poisoned_rejected = False
            try:
                plugin._policy()
            except Exception:
                poisoned_rejected = True
            report["checks"].append({
                "name": "remediation_R2_policy_validator_rejects_poisoned_self_attesting",
                "status": "pass" if poisoned_rejected else "fail",
            })
            # Restore clean policy.
            data["self_attesting_tools"]["names"].remove("terminal")
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            _reload(plugin)
            policy = plugin._policy()

            # --- Remediation R3 (skeptic F3): _glob_matches_any rejects out-of-root symlinks ---
            outside = tmp.parent / "outside-target.yaml"
            outside.write_text("a: 1\n")
            link = tmp / "plans/symlink-leak.yaml"
            try:
                link.symlink_to(outside)
                heartgate = Heartgate.load(tmp)
                ok = heartgate._glob_matches_any("plans/symlink-leak.yaml")
                report["checks"].append({
                    "name": "remediation_R3_glob_rejects_out_of_root_symlink",
                    "status": "pass" if ok is False else "fail",
                })
            finally:
                if link.exists() or link.is_symlink():
                    link.unlink()
                if outside.exists():
                    outside.unlink()

            # --- Remediation R4 (tech F1): unsafe run_id rejected by PIV reader ---
            heartgate = Heartgate.load(tmp)
            bad_artifact = _full_artifact("execute", "verify")
            bad_artifact["run_id"] = "../escape"
            d = heartgate.validate_transition(bad_artifact)
            report["checks"].append({
                "name": "remediation_R4_unsafe_run_id_rejected_by_heartgate",
                "status": "pass" if (d.blocks_transition and any("unsafe run_id" in b for b in d.blockers)) else "fail",
                "blockers": [b for b in d.blockers if "run_id" in b.lower()],
            })

            # --- Remediation R5 (skeptic F5): malformed piv_rule does not crash ---
            pt_path = tmp / "config/phase-transitions.yaml"
            pt = _y.safe_load(pt_path.read_text())
            saved_piv = pt.get("piv_rule")
            pt["piv_rule"]["max_attempts"] = "bogus"
            pt_path.write_text(_y.safe_dump(pt, sort_keys=False))
            heartgate = Heartgate.load(tmp)
            artifact = _full_artifact("plan", "execute")
            try:
                d = heartgate.validate_transition(artifact)
                crashed = False
                helpful_blocker = any("max_attempts" in b for b in d.blockers)
            except Exception:
                crashed = True
                helpful_blocker = False
            report["checks"].append({
                "name": "remediation_R5_malformed_max_attempts_does_not_crash",
                "status": "pass" if (not crashed and helpful_blocker) else "fail",
            })
            # Restore.
            pt["piv_rule"] = saved_piv
            pt_path.write_text(_y.safe_dump(pt, sort_keys=False))

            # --- Remediation R6 (skeptic F6): max_attempts <= 0 produces a blocker ---
            pt["piv_rule"]["max_attempts"] = 0
            pt_path.write_text(_y.safe_dump(pt, sort_keys=False))
            heartgate = Heartgate.load(tmp)
            d = heartgate.validate_transition(_full_artifact("plan", "execute"))
            report["checks"].append({
                "name": "remediation_R6_max_attempts_zero_produces_blocker",
                "status": "pass" if any("max_attempts must be" in b for b in d.blockers) else "fail",
            })
            pt["piv_rule"] = saved_piv
            pt_path.write_text(_y.safe_dump(pt, sort_keys=False))

            # --- Remediation R7 (skeptic F5b): malformed stages config does not crash ---
            pt["stages"] = ["this", "is", "wrong"]
            pt_path.write_text(_y.safe_dump(pt, sort_keys=False))
            _reload(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="uacp_doc_write",
                args={**_common_args(tmp, phase="execute"), "target_path": "docs/x.md", "content": "# x\n"},
                filesystem_guard_verified=True,
            )
            try:
                d = Guardian(policy, phase_config=plugin._phase_config()).evaluate(event)
                no_crash = True
            except Exception:
                no_crash = False
            report["checks"].append({
                "name": "remediation_R7_malformed_stages_does_not_crash",
                "status": "pass" if no_crash else "fail",
            })
            # Restore good stages.
            pt_path.write_text((Path(__file__).resolve().parent.parent / "config/phase-transitions.yaml").read_text())
            _reload(plugin)
            policy = plugin._policy()

            # --- Check 12: attestation pruning works (pc_3) ---
            plugin._CONTAINED_SHELL_ATTESTATIONS["expired1"] = {
                "expires_at": time.time() - 60,
                "policy_version": str(policy.version),
                "containment_verified": True,
            }
            plugin._CONTAINED_SHELL_ATTESTATIONS["fresh1"] = {
                "expires_at": time.time() + 60,
                "policy_version": str(policy.version),
                "containment_verified": True,
            }
            plugin._validate_contained_shell_attestation("fresh1", str(policy.version))
            report["checks"].append({
                "name": "pc_3_expired_attestations_pruned_on_validate",
                "status": "pass" if ("expired1" not in plugin._CONTAINED_SHELL_ATTESTATIONS and "fresh1" in plugin._CONTAINED_SHELL_ATTESTATIONS) else "fail",
            })

    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    all_pass = all(c.get("status") == "pass" for c in report["checks"])
    report["status"] = "pass" if all_pass else "fail"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

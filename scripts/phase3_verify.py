#!/usr/bin/env python3
"""Phase 3 behavioural verification for the UACP patch plan.

Exercises:
  - Item 3.1 — plan_validation_gate: missing PLAN_VALIDATION ledger entry blocks PLAN->EXECUTE;
    presence with result=pass unblocks (in combination with scope artifact etc.).
  - Item 3.2 — run_registry overlap: state/run-registry.yaml with overlapping write_paths blocks PLAN->EXECUTE.
  - Item 3.4 propagated fixes:
      pc_p2_t3 empty cluster_summary blocks VERIFY->RESOLVE
      pc_p2_t4 assumptions table column-count mismatch produces blocker
      pc_p2_t5 intent doc section regex anchored + fence-aware
      pc_p2_n1 "*" sentinel in tool_path_capabilities dropped
      pc_p2_minor PIV ledger fail-closed on bad JSONL; PIPE_BUF record bound
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
    from uacp_guardian.kernel import Guardian, Heartgate, make_event
    return plugin, Guardian, Heartgate, make_event


def _prepare_root(tmp: Path) -> None:
    here = Path(__file__).resolve().parent.parent
    for sub in ("config", "docs", "state/runs", "state/gate-ledger",
                "plans", "proposals", "executions", "verification", "outputs", "knowledge"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    for fn in ("guardian-policy.yaml", "phase-transitions.yaml", "state.yaml", "artifact-schemas.yaml"):
        shutil.copy2(here / "config" / fn, tmp / "config" / fn)


def _reload(plugin) -> None:
    plugin._POLICY = None
    plugin._POLICY_ERROR = ""
    plugin._PHASE_CONFIG = None


def _common_args(tmp: Path, *, phase: str, run_id: str) -> dict:
    return {
        "workspace": str(tmp),
        "uacp_run_id": run_id,
        "uacp_phase": phase,
        "policy_version": "0.1",
        "declared_side_effects": "phase3 verification writes",
        "authority_artifact": "verification/phase3-verify.yaml",
        "reason": "phase 3 verification",
    }


def _full_artifact(run_id: str, from_phase: str, to_phase: str, *, clusters: list | None = None) -> dict:
    return {
        "kind": "uacp.phase_transition",
        "transition_id": f"{run_id}-{from_phase}-to-{to_phase}",
        "run_id": run_id,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "decision": "pass",
        "invariant_summary": [],
        "cluster_summary": clusters or [],
        "blockers": [],
        "warnings": [],
        "deferred_items": [],
        "authority": {"requested_by": "operator", "authorization_source": "test"},
        "artifact_paths": [],
        "phase_local_granularity": {"phase": from_phase, "entry_estimate": 5, "exit_actual": 5, "delta_reason": "test", "downstream_projection": {}},
        "composite_granularity": 5,
        "human_involvement": {"required": False, "reason": "test", "authority_needed": "none", "decision_owner": "none", "accepted_risk_artifact": ""},
    }


def main() -> int:
    plugin, Guardian, Heartgate, make_event = _import_plugin()
    report: dict = {"checks": []}
    saved_env = {k: os.environ.get(k) for k in ("UACP_ROOT", "UACP_GUARDIAN_MODE")}
    run_id = "phase3-verify"
    import yaml as _y

    try:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            _prepare_root(tmp)
            os.environ["UACP_ROOT"] = str(tmp)
            os.environ.pop("UACP_GUARDIAN_MODE", None)
            _reload(plugin)
            heartgate = Heartgate.load(tmp)

            # Seed ledger helper.
            PV_IDS = ["pv_1", "pv_2", "pv_3", "pv_4", "pv_5", "pv_6"]
            def _append(gate: str, phase: str, result: str = "pass", piv_attempt: int | None = None, run_id_override: str | None = None, checks: list | None = None, check_results: dict | None = None):
                rid = run_id_override or run_id
                record = {"gate": gate, "run_id": rid, "phase": phase, "result": result, "ts": int(time.time())}
                if piv_attempt is not None:
                    record["piv_attempt"] = piv_attempt
                # Phase 3 R1: PLAN_VALIDATION ledger record must carry pv_ids.
                if gate == "PLAN_VALIDATION" and checks is None:
                    checks = list(PV_IDS)
                if checks is not None:
                    record["checks"] = checks
                # Phase 3 R2 (SKEP-R1-003): PLAN_VALIDATION needs per-check
                # pass evidence — sibling check_results mapping when checks
                # is a flat list of strings.
                if gate == "PLAN_VALIDATION" and check_results is None and checks and all(isinstance(c, str) for c in checks):
                    check_results = {c: "pass" for c in checks}
                if check_results is not None:
                    record["check_results"] = check_results
                line = json.dumps(record, sort_keys=True) + "\n"
                (tmp / f"state/gate-ledger/{rid}.jsonl").parent.mkdir(parents=True, exist_ok=True)
                with (tmp / f"state/gate-ledger/{rid}.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write(line)

            # Common seed for transitions used below.
            _append("PROPOSE->PLAN", "plan")
            _append("PIV", "plan", piv_attempt=1)
            (tmp / f"plans/{run_id}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{run_id}-scope.yaml").write_text(_y.safe_dump({
                "run_id": run_id,
                "write_paths": ["plans/", "executions/"],
                "blast_radius": "low",
                "rollback_path": "git revert",
            }))

            # --- Check 1: plan_validation_gate missing blocks PLAN->EXECUTE ---
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            report["checks"].append({
                "name": "plan_validation_gate_missing_blocks",
                "status": "pass" if any("plan_validation_gate" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "plan_validation_gate" in b],
            })

            # --- Check 2: plan_validation_gate present unblocks ---
            _append("PLAN_VALIDATION", "plan")
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            pv_blockers = [b for b in d.blockers if "plan_validation_gate" in b]
            report["checks"].append({
                "name": "plan_validation_gate_present_unblocks",
                "status": "pass" if not pv_blockers else "fail",
                "blockers": pv_blockers,
            })

            # --- Check 3: run_registry overlap blocks ---
            (tmp / "state/run-registry.yaml").write_text(_y.safe_dump({
                "active_runs": [
                    {"run_id": "other-run", "phase": "execute", "write_paths": ["plans/", "executions/"], "started": "2026-05-16"},
                ],
            }))
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            overlap_blockers = [b for b in d.blockers if "run_registry: write_paths overlap" in b]
            report["checks"].append({
                "name": "run_registry_overlap_blocks",
                "status": "pass" if overlap_blockers else "fail",
                "blockers": overlap_blockers,
            })

            # --- Check 4: run_registry no overlap passes ---
            (tmp / "state/run-registry.yaml").write_text(_y.safe_dump({
                "active_runs": [
                    {"run_id": "other-run", "phase": "execute", "write_paths": ["docs/"], "started": "2026-05-16"},
                ],
            }))
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            overlap_blockers = [b for b in d.blockers if "run_registry: write_paths overlap" in b]
            report["checks"].append({
                "name": "run_registry_no_overlap_passes",
                "status": "pass" if not overlap_blockers else "fail",
                "blockers": overlap_blockers,
            })

            # --- Check 5: pc_p2_t3 empty cluster_summary blocks VERIFY->RESOLVE ---
            _append("EXECUTE->VERIFY", "verify")
            _append("PIV", "verify", piv_attempt=1)
            (tmp / f"verification/{run_id}-v.yaml").write_text("a: 1\n")
            (tmp / f"outputs/{run_id}-lessons.yaml").write_text(_y.safe_dump({"run_id": run_id, "lessons": []}))
            d = heartgate.validate_transition(_full_artifact(run_id, "verify", "resolve"))
            empty_cluster_blockers = [b for b in d.blockers if "cluster_summary is empty" in b]
            report["checks"].append({
                "name": "pc_p2_t3_empty_cluster_summary_blocks",
                "status": "pass" if empty_cluster_blockers else "fail",
                "blockers": empty_cluster_blockers,
            })

            # --- Check 6: pc_p2_t4 column-count mismatch produces blocker ---
            (tmp / f"verification/{run_id}-scope-verified-facts.md").write_text(
                "# Verified Facts\n\n| Fact | Source |\n|---|---|\n| ok | tested |\n"
            )
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text(
                "# Assumptions\n\n| A | B | C |\n|---|---|---|\n| x | y | z |\n"  # 3 cols not 4
            )
            d = heartgate.validate_transition(_full_artifact(run_id, "verify", "resolve",
                clusters=[{"cluster_id": "scope", "state": "pass", "artifact_path": ""}]))
            col_blockers = [b for b in d.blockers if "unexpected column count" in b]
            report["checks"].append({
                "name": "pc_p2_t4_column_count_mismatch_blocks",
                "status": "pass" if col_blockers else "fail",
                "blockers": col_blockers,
            })

            # --- Check 7: pc_p2_t5 fenced ## Section does NOT satisfy intent check ---
            triage_run = run_id + "-intent-fence"
            _append("TRIAGE_COMPLETE", "triage", run_id_override=triage_run)
            _append("PIV", "triage", piv_attempt=1, run_id_override=triage_run)
            (tmp / f"proposals/{triage_run}-triage.yaml").write_text("a: 1\n")
            (tmp / f"proposals/{triage_run}-intent.md").write_text(
                "# Intent\n\n```\n## Success Definition\n## Explicit Out-of-Scope\n## Termination Condition\n## Authority Source\n```\n"
            )
            d = heartgate.validate_transition(_full_artifact(triage_run, "triage", "propose"))
            section_blockers = [b for b in d.blockers if "intent doc missing required section" in b]
            report["checks"].append({
                "name": "pc_p2_t5_fenced_sections_dont_satisfy",
                "status": "pass" if len(section_blockers) == 4 else "fail",
                "blockers": section_blockers,
            })

            # --- Check 8: pc_p2_t5 real sections satisfy ---
            (tmp / f"proposals/{triage_run}-intent.md").write_text(
                "# Intent\n\n## Success Definition\nx\n\n## Explicit Out-of-Scope\ny\n\n## Termination Condition\nz\n\n## Authority Source\nop\n"
            )
            d = heartgate.validate_transition(_full_artifact(triage_run, "triage", "propose"))
            section_blockers = [b for b in d.blockers if "intent doc missing required section" in b]
            report["checks"].append({
                "name": "pc_p2_t5_real_sections_satisfy",
                "status": "pass" if not section_blockers else "fail",
                "blockers": section_blockers,
            })

            # --- Check 9: pc_p2_n1 "*" sentinel dropped from capabilities ---
            pp = tmp / "config/artifact-schemas.yaml"
            data = _y.safe_load(pp.read_text())
            data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["evil_tool"] = ["*"]
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            heartgate2 = Heartgate.load(tmp)
            caps = heartgate2._tool_path_capabilities()
            report["checks"].append({
                "name": "pc_p2_n1_wildcard_dropped",
                "status": "pass" if "evil_tool" not in caps else "fail",
                "loaded": sorted(caps.keys()),
            })
            del data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["evil_tool"]
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            heartgate = Heartgate.load(tmp)

            # --- Check 10: pc_p2_minor JSONL fail-closed on bad ledger line ---
            bad_run = run_id + "-badledger"
            badpath = tmp / f"state/gate-ledger/{bad_run}.jsonl"
            badpath.parent.mkdir(parents=True, exist_ok=True)
            badpath.write_text('{"gate": "PROPOSE->PLAN", "run_id": "x", "phase": "plan", "result": "pass", "ts": 0}\n'
                               'this is not json at all\n')
            (tmp / f"plans/{bad_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{bad_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": bad_run,
                "write_paths": ["plans/"],
                "blast_radius": "low",
                "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(bad_run, "plan", "execute"))
            fail_closed = any("unparseable" in b for b in d.blockers)
            report["checks"].append({
                "name": "pc_p2_minor_jsonl_fail_closed",
                "status": "pass" if fail_closed else "fail",
                "blockers": [b for b in d.blockers if "unparseable" in b],
            })

            # --- Check 11: pc_p2_minor PIPE_BUF record-size bound ---
            big = "x" * 5000
            res = json.loads(plugin._handle_uacp_gate_ledger_append({
                **_common_args(tmp, phase="execute", run_id=run_id),
                "gate": "BIG",
                "record": {"payload": big},
            }))
            report["checks"].append({
                "name": "pc_p2_minor_pipe_buf_bound",
                "status": "pass" if (res.get("error") and "PIPE_BUF" in res.get("error", "")) else "fail",
                "error": res.get("error"),
            })

            # --- Check 12 (TECH-006): mixed wildcard list keeps real prefix, drops "*" ---
            pp = tmp / "config/artifact-schemas.yaml"
            data = _y.safe_load(pp.read_text())
            data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["mixed_tool"] = ["state/", "*"]
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            heartgate_mix = Heartgate.load(tmp)
            caps_mix = heartgate_mix._tool_path_capabilities()
            mixed_ok = caps_mix.get("mixed_tool") == ["state/"]
            report["checks"].append({
                "name": "r1_tech006_mixed_wildcard_keeps_real_prefix",
                "status": "pass" if mixed_ok else "fail",
                "loaded": caps_mix.get("mixed_tool"),
            })
            del data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["mixed_tool"]
            pp.write_text(_y.safe_dump(data, sort_keys=False))
            heartgate = Heartgate.load(tmp)

            # --- Check 13 (SKEP-007): description metadata key not loaded as tool ---
            caps_now = heartgate._tool_path_capabilities()
            report["checks"].append({
                "name": "r1_skep007_description_key_not_loaded_as_tool",
                "status": "pass" if "description" not in caps_now else "fail",
                "loaded": sorted(caps_now.keys()),
            })

            # --- Check 14 (SKEP-004): tilde fences do NOT satisfy intent sections ---
            tilde_run = run_id + "-tildefence"
            (tmp / f"proposals/{tilde_run}-triage.yaml").write_text(_y.safe_dump({"run_id": tilde_run}))
            (tmp / f"proposals/{tilde_run}-intent.md").write_text(
                "# Intent\n\n~~~\n## Success Definition\n## Explicit Out-of-Scope\n## Termination Condition\n## Authority Source\n~~~\n"
            )
            d = heartgate.validate_transition(_full_artifact(tilde_run, "triage", "propose"))
            tilde_blockers = [b for b in d.blockers if "intent doc missing required section" in b]
            report["checks"].append({
                "name": "r1_skep004_tilde_fence_does_not_satisfy_sections",
                "status": "pass" if len(tilde_blockers) == 4 else "fail",
                "blockers_count": len(tilde_blockers),
            })

            # --- Check 15 (SKEP-005): substring "disposition" in data row does not skip it ---
            sk5_run = run_id + "-sk5"
            (tmp / f"verification/{sk5_run}-scope-verified-facts.md").write_text("| Fact | Source |\n|---|---|\n| f | s |\n")
            (tmp / f"verification/{sk5_run}-scope-assumptions.md").write_text(
                "| Assumption | Disposition | Owner | Next-phase obligation |\n"
                "|---|---|---|---|\n"
                "| disposition reviewed | pending | | |\n"
            )
            _append("EXECUTE->VERIFY", "verify", run_id_override=sk5_run)
            _append("PIV", "verify", piv_attempt=1, run_id_override=sk5_run)
            artifact_sk5 = {**_full_artifact(sk5_run, "verify", "resolve"), "cluster_summary": [{"cluster_id": "scope", "state": "pass"}]}
            d = heartgate.validate_transition(artifact_sk5)
            unowned = [b for b in d.blockers if "unowned 'pending'" in b]
            report["checks"].append({
                "name": "r1_skep005_substring_disposition_row_still_flagged",
                "status": "pass" if unowned else "fail",
                "blockers": unowned,
            })

            # --- Check 16 (SKEP-006): all clusters not_applicable bypass is blocked ---
            sk6_run = run_id + "-sk6"
            _append("EXECUTE->VERIFY", "verify", run_id_override=sk6_run)
            _append("PIV", "verify", piv_attempt=1, run_id_override=sk6_run)
            (tmp / f"outputs/{sk6_run}-lessons.yaml").write_text(_y.safe_dump({"run_id": sk6_run, "lessons": []}))
            artifact_sk6 = {
                **_full_artifact(sk6_run, "verify", "resolve"),
                "cluster_summary": [
                    {"cluster_id": "a", "state": "not_applicable"},
                    {"cluster_id": "b", "state": "deferred"},
                ],
            }
            d = heartgate.validate_transition(artifact_sk6)
            na_block = [b for b in d.blockers if "not_applicable/deferred" in b]
            report["checks"].append({
                "name": "r1_skep006_all_na_clusters_blocked",
                "status": "pass" if na_block else "fail",
                "blockers": na_block,
            })

            # --- Check 17 (SKEP-001): PLAN_VALIDATION with no checks list is rejected ---
            bare_run = run_id + "-bare"
            bare_ledger = tmp / f"state/gate-ledger/{bare_run}.jsonl"
            bare_ledger.parent.mkdir(parents=True, exist_ok=True)
            bare_ledger.write_text(
                json.dumps({"gate": "PROPOSE->PLAN", "run_id": bare_run, "phase": "plan", "result": "pass", "ts": 0}) + "\n"
                + json.dumps({"gate": "PIV", "run_id": bare_run, "phase": "plan", "result": "pass", "piv_attempt": 1, "ts": 0}) + "\n"
                + json.dumps({"gate": "PLAN_VALIDATION", "run_id": bare_run, "phase": "plan", "result": "pass", "ts": 0}) + "\n"
            )
            (tmp / f"plans/{bare_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{bare_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": bare_run, "write_paths": ["plans/"], "blast_radius": "low", "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(bare_run, "plan", "execute"))
            bare_block = [b for b in d.blockers if "plan_validation_gate" in b and ("checks" in b or "missing required" in b)]
            report["checks"].append({
                "name": "r1_skep001_plan_validation_without_checks_blocked",
                "status": "pass" if bare_block else "fail",
                "blockers": bare_block,
            })

            # --- Check 18 (SKEP-002): uacp_state_write refuses state/run-registry.yaml ---
            regw = json.loads(plugin._handle_uacp_state_write({
                **_common_args(tmp, phase="execute", run_id=run_id),
                "target_path": "state/run-registry.yaml",
                "content": "active_runs: []\n",
            }))
            report["checks"].append({
                "name": "r1_skep002_state_write_refuses_run_registry",
                "status": "pass" if (regw.get("error") and "run-registry.yaml directly" in regw.get("error", "")) else "fail",
                "error": regw.get("error"),
            })

            # --- Check 19 (SKEP-003): path normalization — './plans/' overlaps 'plans/' ---
            sk3_run = run_id + "-sk3"
            (tmp / f"plans/{sk3_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{sk3_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": sk3_run, "write_paths": ["plans/"], "blast_radius": "low", "rollback_path": "none",
            }))
            _append("PROPOSE->PLAN", "plan", run_id_override=sk3_run)
            _append("PIV", "plan", piv_attempt=1, run_id_override=sk3_run)
            _append("PLAN_VALIDATION", "plan", run_id_override=sk3_run)
            (tmp / "state/run-registry.yaml").write_text(_y.safe_dump({
                "schema_version": "0.1",
                "active_runs": [
                    {"run_id": "other-sneaky-run", "phase": "execute", "write_paths": ["./plans/"], "started_at": 0, "scope_artifact_path": ""},
                ],
            }))
            d = heartgate.validate_transition(_full_artifact(sk3_run, "plan", "execute"))
            overlap = [b for b in d.blockers if "run_registry" in b and "overlap" in b]
            report["checks"].append({
                "name": "r1_skep003_dot_slash_normalized_to_overlap",
                "status": "pass" if overlap else "fail",
                "blockers": overlap,
            })

            # --- Check 20 (SKEP-003 inverse): "plans" vs "plans-other/" must NOT overlap ---
            (tmp / "state/run-registry.yaml").write_text(_y.safe_dump({
                "schema_version": "0.1",
                "active_runs": [
                    {"run_id": "lookalike-other", "phase": "execute", "write_paths": ["plans-other/"], "started_at": 0, "scope_artifact_path": ""},
                ],
            }))
            d = heartgate.validate_transition(_full_artifact(sk3_run, "plan", "execute"))
            false_overlap = [b for b in d.blockers if "run_registry" in b and "overlap" in b]
            report["checks"].append({
                "name": "r1_skep003_lookalike_prefix_no_false_overlap",
                "status": "pass" if not false_overlap else "fail",
                "blockers": false_overlap,
            })

            # --- Check 21 (SKEP-010): malformed active_runs (non-list) blocks ---
            (tmp / "state/run-registry.yaml").write_text("active_runs: hello\n")
            d = heartgate.validate_transition(_full_artifact(sk3_run, "plan", "execute"))
            malformed = [b for b in d.blockers if "active_runs" in b and "must be a list" in b]
            report["checks"].append({
                "name": "r1_skep010_malformed_active_runs_blocks",
                "status": "pass" if malformed else "fail",
                "blockers": malformed,
            })
            # cleanup registry
            (tmp / "state/run-registry.yaml").unlink()

            # --- Check 22 (SKEP-008): scope.write_paths cannot launder state/gate-ledger/ ---
            sk8_run = run_id + "-sk8"
            (tmp / f"plans/{sk8_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{sk8_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": sk8_run, "write_paths": ["state/gate-ledger/forged.jsonl"], "blast_radius": "low", "rollback_path": "none",
            }))
            _append("PROPOSE->PLAN", "plan", run_id_override=sk8_run)
            _append("PIV", "plan", piv_attempt=1, run_id_override=sk8_run)
            _append("PLAN_VALIDATION", "plan", run_id_override=sk8_run)
            d = heartgate.validate_transition(_full_artifact(sk8_run, "plan", "execute"))
            launder = [b for b in d.blockers if "scope.write_paths cross-check" in b and "state/gate-ledger" in b]
            report["checks"].append({
                "name": "r1_skep008_gate_ledger_launder_blocked",
                "status": "pass" if launder else "fail",
                "blockers": launder,
            })

            # --- Check 23 (R1 GOV-002): uacp_run_registry_update register works (own run only) ---
            # Phase 3 R2 (SKEP-R1-001): caller must register its own run_id.
            reg_ok = json.loads(plugin._handle_uacp_run_registry_update({
                **_common_args(tmp, phase="execute", run_id=run_id),
                "op": "register",
                "entry": {"run_id": run_id, "phase": "execute", "write_paths": ["zzz/"], "scope_artifact_path": f"plans/{run_id}-scope.yaml", "started_at": 1},
            }))
            report["checks"].append({
                "name": "r1_gov002_run_registry_update_register_ok",
                "status": "pass" if reg_ok.get("ok") and reg_ok.get("active_count") == 1 else "fail",
                "result": reg_ok,
            })

            # --- Check 24 (SKEP-R1-001): uacp_run_registry_update rejects foreign run_id ---
            reg_foreign = json.loads(plugin._handle_uacp_run_registry_update({
                **_common_args(tmp, phase="execute", run_id=run_id),
                "op": "register",
                "entry": {"run_id": "foreign-run", "phase": "execute", "write_paths": ["plans/"]},
            }))
            report["checks"].append({
                "name": "r2_skep001_caller_binding_blocks_foreign_run",
                "status": "pass" if (reg_foreign.get("error") and "does not match caller" in reg_foreign.get("error", "")) else "fail",
                "result": reg_foreign,
            })

            # --- Check 25 (SKEP-R1-002): bogus handled_findings_chain doesn't bypass all-NA block ---
            sk2_run = run_id + "-sk2"
            _append("EXECUTE->VERIFY", "verify", run_id_override=sk2_run)
            _append("PIV", "verify", piv_attempt=1, run_id_override=sk2_run)
            (tmp / f"outputs/{sk2_run}-lessons.yaml").write_text(_y.safe_dump({"run_id": sk2_run, "lessons": []}))
            artifact_sk2 = {
                **_full_artifact(sk2_run, "verify", "resolve"),
                "cluster_summary": [{"cluster_id": "a", "state": "not_applicable"}],
                "handled_findings_chain": [None, {}, ""],  # bogus
                "accepted_exceptions": [{}, ""],            # bogus
            }
            d = heartgate.validate_transition(artifact_sk2)
            still_blocked = [b for b in d.blockers if "not_applicable/deferred" in b]
            report["checks"].append({
                "name": "r2_skep002_bogus_escape_hatch_does_not_bypass",
                "status": "pass" if still_blocked else "fail",
                "blockers": still_blocked,
            })

            # --- Check 26 (SKEP-R1-003): flat-string checks list without check_results is rejected ---
            flat_run = run_id + "-flat"
            flat_ledger = tmp / f"state/gate-ledger/{flat_run}.jsonl"
            flat_ledger.parent.mkdir(parents=True, exist_ok=True)
            flat_ledger.write_text(
                json.dumps({"gate": "PROPOSE->PLAN", "run_id": flat_run, "phase": "plan", "result": "pass", "ts": 0}) + "\n"
                + json.dumps({"gate": "PIV", "run_id": flat_run, "phase": "plan", "result": "pass", "piv_attempt": 1, "ts": 0}) + "\n"
                # NOTE: flat list of pv_ids WITHOUT check_results sibling → must be rejected.
                + json.dumps({"gate": "PLAN_VALIDATION", "run_id": flat_run, "phase": "plan", "result": "pass", "checks": ["pv_1","pv_2","pv_3","pv_4","pv_5","pv_6"], "ts": 0}) + "\n"
            )
            (tmp / f"plans/{flat_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{flat_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": flat_run, "write_paths": ["plans/"], "blast_radius": "low", "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(flat_run, "plan", "execute"))
            flat_block = [b for b in d.blockers if "per-check pass evidence" in b or "no '" in b]
            report["checks"].append({
                "name": "r2_skep003_flat_string_checks_without_results_blocked",
                "status": "pass" if flat_block else "fail",
                "blockers": flat_block,
            })

            # --- Check 27 (SKEP-R1-004): empty scope.write_paths is a blocker ---
            empty_run = run_id + "-empty"
            (tmp / f"plans/{empty_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{empty_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": empty_run, "write_paths": [], "blast_radius": "low", "rollback_path": "none",
            }))
            _append("PROPOSE->PLAN", "plan", run_id_override=empty_run)
            _append("PIV", "plan", piv_attempt=1, run_id_override=empty_run)
            _append("PLAN_VALIDATION", "plan", run_id_override=empty_run)
            d = heartgate.validate_transition(_full_artifact(empty_run, "plan", "execute"))
            empty_block = [b for b in d.blockers if "scope.write_paths is empty" in b]
            report["checks"].append({
                "name": "r2_skep004_empty_write_paths_blocked",
                "status": "pass" if empty_block else "fail",
                "blockers": empty_block,
            })

            # --- Check 28 (SKEP-R1-007): DoS via bad PLAN_VALIDATION followed by good one — good wins ---
            dos_run = run_id + "-dos"
            dos_ledger = tmp / f"state/gate-ledger/{dos_run}.jsonl"
            dos_ledger.parent.mkdir(parents=True, exist_ok=True)
            dos_ledger.write_text(
                json.dumps({"gate": "PROPOSE->PLAN", "run_id": dos_run, "phase": "plan", "result": "pass", "ts": 0}) + "\n"
                + json.dumps({"gate": "PIV", "run_id": dos_run, "phase": "plan", "result": "pass", "piv_attempt": 1, "ts": 0}) + "\n"
                # Bad: missing checks
                + json.dumps({"gate": "PLAN_VALIDATION", "run_id": dos_run, "phase": "plan", "result": "pass", "ts": 0}) + "\n"
                # Good: full contract
                + json.dumps({"gate": "PLAN_VALIDATION", "run_id": dos_run, "phase": "plan", "result": "pass",
                              "checks": ["pv_1","pv_2","pv_3","pv_4","pv_5","pv_6"],
                              "check_results": {"pv_1":"pass","pv_2":"pass","pv_3":"pass","pv_4":"pass","pv_5":"pass","pv_6":"pass"},
                              "ts": 1}) + "\n"
            )
            (tmp / f"plans/{dos_run}-plan.yaml").write_text("a: 1\n")
            (tmp / f"plans/{dos_run}-scope.yaml").write_text(_y.safe_dump({
                "run_id": dos_run, "write_paths": ["plans/"], "blast_radius": "low", "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(dos_run, "plan", "execute"))
            pv_blockers = [b for b in d.blockers if "plan_validation_gate" in b]
            report["checks"].append({
                "name": "r2_skep007_dos_resistance_good_record_wins",
                "status": "pass" if not pv_blockers else "fail",
                "blockers": pv_blockers,
            })

            # --- Check 29 (TECH-R1-001): uacp_run_registry_update enforces UACP context fields ---
            no_ctx = json.loads(plugin._handle_uacp_run_registry_update({
                "op": "register",
                "entry": {"run_id": "anything", "phase": "execute", "write_paths": ["plans/"]},
                "reason": "test",
                "authority_artifact": "test",
            }))
            report["checks"].append({
                "name": "r2_tech001_uacp_context_required",
                "status": "pass" if (no_ctx.get("error") and "missing UACP context" in no_ctx.get("error", "")) else "fail",
                "result": no_ctx,
            })

            # --- Check 30 (TECH-R1-002): write_paths with '..' rejected at register ---
            bad_wp = json.loads(plugin._handle_uacp_run_registry_update({
                **_common_args(tmp, phase="execute", run_id=run_id),
                "op": "register",
                "entry": {"run_id": run_id, "phase": "execute", "write_paths": ["plans/../plans/"]},
            }))
            report["checks"].append({
                "name": "r2_tech002_dotdot_write_path_rejected_at_register",
                "status": "pass" if (bad_wp.get("error") and "not canonicalizable" in bad_wp.get("error", "")) else "fail",
                "result": bad_wp,
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

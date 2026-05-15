#!/usr/bin/env python3
"""Phase 2 behavioural verification for the UACP patch plan.

Exercises Heartgate enforcement of Phase 2 structured artifacts:
  - Item 2.1 — scope artifact: required fields + write_paths Layer B cross-check (pc_p1_gov_2)
  - Item 2.2 — evidence disposition pairs: pair-file existence + unowned-pending block
  - Item 2.3 — intent doc: presence + required sections
  - Item 2.4 — lessons artifact: schema with ledger_citations (pc_p1_gov_3)
  - Item 2.5 — pc_p1_t2 (_is_safe_run_id rejects literal "." and "..")
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def _import_plugin():
    here = Path(__file__).resolve().parent.parent
    plugins_root = here / "runtime-adapters" / "hermes" / "plugins"
    sys.path.insert(0, str(plugins_root))
    import uacp_guardian as plugin
    from uacp_guardian.kernel import Heartgate, _is_safe_run_id, make_event
    return plugin, Heartgate, _is_safe_run_id, make_event


def _prepare_root(tmp: Path) -> None:
    here = Path(__file__).resolve().parent.parent
    for sub in ("config", "docs", "state/runs", "state/gate-ledger",
                "plans", "proposals", "executions", "verification", "outputs", "knowledge"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(here / "config/guardian-policy.yaml", tmp / "config/guardian-policy.yaml")
    shutil.copy2(here / "config/phase-transitions.yaml", tmp / "config/phase-transitions.yaml")
    shutil.copy2(here / "config/state.yaml", tmp / "config/state.yaml")
    shutil.copy2(here / "config/artifact-schemas.yaml", tmp / "config/artifact-schemas.yaml")


def _reload(plugin) -> None:
    plugin._POLICY = None
    plugin._POLICY_ERROR = ""
    plugin._PHASE_CONFIG = None


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
    plugin, Heartgate, _is_safe_run_id, make_event = _import_plugin()
    report: dict = {"checks": []}
    saved_env = {k: os.environ.get(k) for k in ("UACP_ROOT", "UACP_GUARDIAN_MODE")}
    run_id = "phase2-verify"

    try:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            _prepare_root(tmp)
            os.environ["UACP_ROOT"] = str(tmp)
            os.environ.pop("UACP_GUARDIAN_MODE", None)
            _reload(plugin)

            heartgate = Heartgate.load(tmp)
            import yaml as _yaml

            # Seed the gate ledger so phase_exit_invariants do not fire spurious blockers.
            def _seed_ledger(phase: str, gate: str, piv_pass: bool = True):
                ledger_dir = tmp / "state/gate-ledger"
                ledger_dir.mkdir(parents=True, exist_ok=True)
                path = ledger_dir / f"{run_id}.jsonl"
                import time as _t
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"gate": gate, "run_id": run_id, "phase": phase, "result": "pass", "ts": int(_t.time())}, sort_keys=True) + "\n")
                    if piv_pass:
                        fh.write(json.dumps({"gate": "PIV", "run_id": run_id, "phase": phase, "result": "pass", "piv_attempt": 1, "ts": int(_t.time())}, sort_keys=True) + "\n")

            # --- Check 1: scope artifact missing blocks PLAN->EXECUTE ---
            _seed_ledger("plan", "PROPOSE->PLAN")
            (tmp / "plans/phase2-verify-plan.yaml").write_text("a: 1\n")
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            report["checks"].append({
                "name": "scope_missing_blocks_plan_to_execute",
                "status": "pass" if (d.blocks_transition and any("scope artifact missing" in b for b in d.blockers)) else "fail",
                "blockers": [b for b in d.blockers if "scope" in b.lower()],
            })

            # --- Check 2: scope artifact present with correct fields + reachable write_paths passes ---
            (tmp / f"plans/{run_id}-scope.yaml").write_text(_yaml.safe_dump({
                "run_id": run_id,
                "write_paths": ["plans/", "executions/", "outputs/"],
                "blast_radius": "low",
                "rollback_path": "git revert",
            }))
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            scope_blockers = [b for b in d.blockers if "scope" in b.lower()]
            report["checks"].append({
                "name": "scope_present_and_reachable_passes",
                "status": "pass" if not scope_blockers else "fail",
                "blockers": scope_blockers,
            })

            # --- Check 3: scope.write_paths cross-check rejects unreachable path ---
            (tmp / f"plans/{run_id}-scope.yaml").write_text(_yaml.safe_dump({
                "run_id": run_id,
                "write_paths": ["nonexistent-top-dir/anything"],
                "blast_radius": "low",
                "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            report["checks"].append({
                "name": "scope_write_paths_unreachable_blocks",
                "status": "pass" if any("not reachable by any execute-phase allowed_tool" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "reachable" in b],
            })

            # --- Check 4: scope missing required field blocks ---
            (tmp / f"plans/{run_id}-scope.yaml").write_text(_yaml.safe_dump({
                "run_id": run_id,
                # missing write_paths
                "blast_radius": "low",
                "rollback_path": "none",
            }))
            d = heartgate.validate_transition(_full_artifact(run_id, "plan", "execute"))
            report["checks"].append({
                "name": "scope_missing_required_field_blocks",
                "status": "pass" if any("missing required field: write_paths" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "write_paths" in b],
            })

            # --- Check 5: intent doc missing blocks TRIAGE->PROPOSE ---
            _seed_ledger("triage", "TRIAGE_COMPLETE")
            (tmp / f"proposals/{run_id}-triage.yaml").write_text("a: 1\n")
            d = heartgate.validate_transition(_full_artifact(run_id, "triage", "propose"))
            report["checks"].append({
                "name": "intent_missing_blocks_triage_to_propose",
                "status": "pass" if any("intent doc missing" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "intent" in b.lower()],
            })

            # --- Check 6: intent doc present + all required sections passes ---
            (tmp / f"proposals/{run_id}-intent.md").write_text(
                "# Intent\n\n## Success Definition\nx\n\n## Explicit Out-of-Scope\ny\n\n## Termination Condition\nz\n\n## Authority Source\nop\n"
            )
            d = heartgate.validate_transition(_full_artifact(run_id, "triage", "propose"))
            intent_blockers = [b for b in d.blockers if "intent" in b.lower()]
            report["checks"].append({
                "name": "intent_complete_passes",
                "status": "pass" if not intent_blockers else "fail",
                "blockers": intent_blockers,
            })

            # --- Check 7: intent doc missing a required section blocks ---
            (tmp / f"proposals/{run_id}-intent.md").write_text(
                "# Intent\n\n## Success Definition\nx\n\n## Termination Condition\nz\n"
            )
            d = heartgate.validate_transition(_full_artifact(run_id, "triage", "propose"))
            report["checks"].append({
                "name": "intent_missing_section_blocks",
                "status": "pass" if any("Explicit Out-of-Scope" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "intent" in b.lower()],
            })

            # --- Check 8: evidence disposition pair missing blocks VERIFY->RESOLVE ---
            _seed_ledger("verify", "EXECUTE->VERIFY")
            (tmp / f"verification/{run_id}-v.yaml").write_text("a: 1\n")
            # Lessons file pre-create for this check (so we isolate disposition blocker).
            (tmp / f"outputs/{run_id}-lessons.yaml").write_text(_yaml.safe_dump({"run_id": run_id, "lessons": []}))
            artifact = _full_artifact(run_id, "verify", "resolve",
                clusters=[{"cluster_id": "scope", "state": "pass", "artifact_path": ""}])
            d = heartgate.validate_transition(artifact)
            disp_blockers = [b for b in d.blockers if "evidence_disposition" in b]
            report["checks"].append({
                "name": "disposition_pair_missing_blocks",
                "status": "pass" if disp_blockers else "fail",
                "blockers": disp_blockers,
            })

            # --- Check 9: disposition pair present + no pending assumption passes ---
            (tmp / f"verification/{run_id}-scope-verified-facts.md").write_text(
                "# Verified Facts\n\n| Fact | Source |\n|---|---|\n| ok | tested |\n"
            )
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text(
                "# Assumptions\n\n| Assumption | Disposition | Owner | Next-phase obligation |\n|---|---|---|---|\n| x | accepted_risk | mike | none |\n"
            )
            d = heartgate.validate_transition(artifact)
            disp_blockers = [b for b in d.blockers if "evidence_disposition" in b]
            report["checks"].append({
                "name": "disposition_pair_complete_passes",
                "status": "pass" if not disp_blockers else "fail",
                "blockers": disp_blockers,
            })

            # --- Check 10: unowned pending assumption blocks ---
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text(
                "# Assumptions\n\n| Assumption | Disposition | Owner | Next-phase obligation |\n|---|---|---|---|\n| missing-owner | pending |  |  |\n"
            )
            d = heartgate.validate_transition(artifact)
            report["checks"].append({
                "name": "unowned_pending_assumption_blocks",
                "status": "pass" if any("unowned 'pending'" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "pending" in b],
            })

            # --- Check 11: lessons artifact missing blocks VERIFY->RESOLVE ---
            (tmp / f"outputs/{run_id}-lessons.yaml").unlink()
            # Restore valid disposition for isolation.
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text(
                "# Assumptions\n\n| Assumption | Disposition | Owner | Next-phase obligation |\n|---|---|---|---|\n| x | accepted_risk | mike | none |\n"
            )
            d = heartgate.validate_transition(artifact)
            report["checks"].append({
                "name": "lessons_missing_blocks",
                "status": "pass" if any("lessons artifact missing" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "lessons" in b.lower()],
            })

            # --- Check 12: lessons artifact malformed (lessons key not a list) blocks ---
            (tmp / f"outputs/{run_id}-lessons.yaml").write_text(_yaml.safe_dump({"run_id": run_id, "lessons": "not-a-list"}))
            d = heartgate.validate_transition(artifact)
            report["checks"].append({
                "name": "lessons_malformed_blocks",
                "status": "pass" if any("lessons.lessons must be a list" in b for b in d.blockers) else "fail",
                "blockers": [b for b in d.blockers if "lessons" in b],
            })

            # --- Check 13: well-formed lessons with ledger_citations passes ---
            (tmp / f"outputs/{run_id}-lessons.yaml").write_text(_yaml.safe_dump({
                "run_id": run_id,
                "lessons": [
                    {
                        "id": "L1", "category": "governance",
                        "finding": "x", "recommendation": "y",
                        "gate_affected": "VERIFY->RESOLVE",
                        "applies_to_future_runs": True,
                        "knowledge_path": "knowledge/lessons/universal-governance-lessons.yaml",
                        "ledger_citations": [
                            {"run_id": run_id, "gate": "PIV", "ts": 0, "byte_offset": 0, "reviewer": "codex"},
                        ],
                    }
                ],
            }))
            d = heartgate.validate_transition(artifact)
            lesson_blockers = [b for b in d.blockers if "lessons" in b.lower()]
            report["checks"].append({
                "name": "lessons_with_ledger_citations_passes",
                "status": "pass" if not lesson_blockers else "fail",
                "blockers": lesson_blockers,
            })

            # --- Check 14: pc_p1_t2 — _is_safe_run_id rejects "." and ".." ---
            report["checks"].append({
                "name": "pc_p1_t2_is_safe_run_id_rejects_dots",
                "status": "pass" if (not _is_safe_run_id(".") and not _is_safe_run_id("..") and _is_safe_run_id("ok-1")) else "fail",
            })

            # --- Remediation R-F1 (F1): terminal/execute_code/uacp_contained_shell NOT in capabilities ---
            caps = heartgate._tool_path_capabilities()
            report["checks"].append({
                "name": "R_F1_shell_exec_tools_excluded_from_capabilities",
                "status": "pass" if all(t not in caps for t in ("terminal", "execute_code", "uacp_contained_shell")) else "fail",
                "loaded_tools": sorted(caps.keys()),
            })

            # --- Remediation R-F2 (F2): tool_path_capabilities loaded from config ---
            # Mutate config to add a sentinel; reload Heartgate; confirm propagation.
            pp = tmp / "config/artifact-schemas.yaml"
            data = _yaml.safe_load(pp.read_text())
            data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["sentinel_tool"] = ["sentinel-prefix/"]
            pp.write_text(_yaml.safe_dump(data, sort_keys=False))
            heartgate2 = Heartgate.load(tmp)
            caps2 = heartgate2._tool_path_capabilities()
            report["checks"].append({
                "name": "R_F2_capabilities_loaded_from_config",
                "status": "pass" if caps2.get("sentinel_tool") == ["sentinel-prefix/"] else "fail",
                "sentinel": caps2.get("sentinel_tool"),
            })
            # Restore.
            del data["cross_checks"]["scope_write_paths_vs_layer_b"]["tool_path_capabilities"]["sentinel_tool"]
            pp.write_text(_yaml.safe_dump(data, sort_keys=False))
            heartgate = Heartgate.load(tmp)

            # --- Remediation R-F3 (F3): empty disposition files block ---
            (tmp / f"verification/{run_id}-scope-verified-facts.md").write_text("")  # empty file
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text("")
            d = heartgate.validate_transition(artifact)
            empty_disp_blockers = [b for b in d.blockers if "is empty or missing required header" in b]
            report["checks"].append({
                "name": "R_F3_empty_disposition_files_block",
                "status": "pass" if len(empty_disp_blockers) >= 2 else "fail",
                "blockers": empty_disp_blockers,
            })
            # Restore valid disposition files for later checks.
            (tmp / f"verification/{run_id}-scope-verified-facts.md").write_text(
                "# Verified Facts\n\n| Fact | Source |\n|---|---|\n| ok | tested |\n"
            )
            (tmp / f"verification/{run_id}-scope-assumptions.md").write_text(
                "# Assumptions\n\n| Assumption | Disposition | Owner | Next-phase obligation |\n|---|---|---|---|\n| x | accepted_risk | mike | none |\n"
            )

            # --- Check 15: scope schema not triggered for non-PLAN->EXECUTE transitions ---
            d = heartgate.validate_transition(_full_artifact(run_id, "propose", "plan"))
            scope_unrelated = [b for b in d.blockers if "scope artifact" in b.lower()]
            report["checks"].append({
                "name": "scope_not_required_outside_plan_to_execute",
                "status": "pass" if not scope_unrelated else "fail",
                "blockers": scope_unrelated,
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

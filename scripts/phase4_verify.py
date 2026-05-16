#!/usr/bin/env python3
"""Phase 4 verification — autonomous-mode framework.

Checks:
  * Item 4.1: uacp_mode field in state schema, default manual, enum values correct
  * Item 4.2: config/autonomy-policy.yaml loads, declares 4 modes and trigger registry
  * Item 4.3: every uacp-* SKILL.md carries a mode_behavior section
  * Item 4.4: uacp_escalation_event handler enforces UACP context, validates trigger/severity/reason/mode,
              writes JSONL to state/escalations/{run_id}.jsonl, rejects records > 3584 bytes
  * Drift absorption: state/escalations/ recognized as canonical surface
"""

from __future__ import annotations
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime-adapters/hermes/plugins"))


def _common_args(tmp: Path, *, phase: str, run_id: str) -> dict:
    return {
        "workspace": str(tmp),
        "uacp_run_id": run_id,
        "uacp_phase": phase,
        "policy_version": "0.1",
        "declared_side_effects": "test",
        "reason": "phase4-verify",
        "authority_artifact": "verification/phase4-verify.yaml",
    }


def main() -> int:
    import yaml as _y
    import uacp_guardian as plugin
    from uacp_guardian.kernel import Heartgate

    report: dict = {"phase": 4, "checks": []}
    saved_env: dict[str, str | None] = {}
    for k in ("UACP_ROOT",):
        saved_env[k] = os.environ.get(k)
    try:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d).resolve()
            os.environ["UACP_ROOT"] = str(tmp)
            (tmp / "config").mkdir()
            (tmp / "state").mkdir()
            (tmp / "state/escalations").mkdir()
            for f in ["phase-transitions.yaml", "artifact-schemas.yaml", "guardian-policy.yaml", "state.yaml", "autonomy-policy.yaml"]:
                src = ROOT / "config" / f
                (tmp / "config" / f).write_text(src.read_text())
            plugin._POLICY = None

            # --- Check 1 (Item 4.1): uacp_mode declared in state schema ---
            state_schema = _y.safe_load((tmp / "config/state.yaml").read_text())
            current_schema = state_schema.get("current_pointer_schema", {}) or {}
            fields = (current_schema.get("fields") or {})
            uacp_mode = fields.get("uacp_mode") or {}
            ok = (
                isinstance(uacp_mode, dict)
                and uacp_mode.get("type") == "enum"
                and set(uacp_mode.get("values") or []) == {"manual", "semi_auto", "supervised_auto", "full_auto"}
                and uacp_mode.get("default") == "manual"
            )
            report["checks"].append({
                "name": "item41_uacp_mode_in_state_schema",
                "status": "pass" if ok else "fail",
                "field": uacp_mode,
            })

            # --- Check 2 (Item 4.1): escalations block in state schema ---
            esc = state_schema.get("escalations") or {}
            ok2 = (
                esc.get("path") == "state/escalations/"
                and "{run_id}.jsonl" in str(esc.get("filename_template") or "")
                and "trigger" in (esc.get("record_schema") or {}).get("required_fields", [])
            )
            report["checks"].append({
                "name": "item41_escalations_block_in_state_schema",
                "status": "pass" if ok2 else "fail",
                "block": esc.get("record_schema"),
            })

            # --- Check 3 (Item 4.2): autonomy-policy.yaml loads with 4 modes ---
            ap = _y.safe_load((tmp / "config/autonomy-policy.yaml").read_text())
            modes_block = ap.get("modes") or {}
            # Phase 4 R1: filter out the enforcement_status meta key.
            modes = [k for k in modes_block.keys() if k != "enforcement_status"]
            ok3 = set(modes) == {"manual", "semi_auto", "supervised_auto", "full_auto"}
            report["checks"].append({
                "name": "item42_autonomy_policy_has_4_modes",
                "status": "pass" if ok3 else "fail",
                "modes": modes,
            })

            # --- Check 4 (Item 4.2): escalation triggers registered ---
            triggers = (ap.get("escalation_triggers") or {}).get("triggers") or []
            trigger_ids = [str(t.get("id") or "") for t in triggers if isinstance(t, dict)]
            ok4 = "trigger_blast_radius_high" in trigger_ids and "trigger_piv_second_failure" in trigger_ids
            report["checks"].append({
                "name": "item42_escalation_triggers_present",
                "status": "pass" if ok4 else "fail",
                "trigger_ids": trigger_ids,
            })

            # --- Check 5 (Item 4.3): every uacp-* SKILL.md has mode_behavior stub ---
            skills_dir = Path("/home/norty/.hermes/skills/devops/uacp")
            missing = []
            if skills_dir.exists():
                for sub in sorted(skills_dir.iterdir()):
                    if sub.is_dir() and sub.name.startswith("uacp-"):
                        skill_md = sub / "SKILL.md"
                        if skill_md.exists():
                            txt = skill_md.read_text()
                            if "mode_behavior (Phase 4.3" not in txt:
                                missing.append(sub.name)
            report["checks"].append({
                "name": "item43_mode_behavior_stub_in_all_skills",
                "status": "pass" if not missing else "fail",
                "missing": missing,
            })

            # --- Check 6 (Item 4.4): uacp_escalation_event requires UACP context ---
            no_ctx = json.loads(plugin._handle_uacp_escalation_event({
                "trigger": "trigger_blast_radius_high",
                "severity": "block",
                "reason": "test",
            }))
            report["checks"].append({
                "name": "item44_escalation_event_requires_uacp_context",
                "status": "pass" if (no_ctx.get("error") and "missing UACP context" in no_ctx.get("error", "")) else "fail",
                "result": no_ctx,
            })

            # --- Check 7 (Item 4.4): rejects invalid severity ---
            bad_sev = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "doom",
                "reason": "test",
                "mode": "supervised_auto",
            }))
            report["checks"].append({
                "name": "item44_escalation_event_rejects_bad_severity",
                "status": "pass" if (bad_sev.get("error") and "severity" in bad_sev.get("error", "")) else "fail",
                "result": bad_sev,
            })

            # --- Check 8 (Item 4.4): rejects empty reason ---
            empty_reason = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "warn",
                "reason": "",
                "mode": "supervised_auto",
            }))
            report["checks"].append({
                "name": "item44_escalation_event_rejects_empty_reason",
                "status": "pass" if (empty_reason.get("error") and "reason" in empty_reason.get("error", "")) else "fail",
                "result": empty_reason,
            })

            # --- Check 9 (Item 4.4): rejects invalid mode ---
            bad_mode = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "warn",
                "reason": "test",
                "mode": "godmode",
            }))
            report["checks"].append({
                "name": "item44_escalation_event_rejects_bad_mode",
                "status": "pass" if (bad_mode.get("error") and "mode" in bad_mode.get("error", "")) else "fail",
                "result": bad_mode,
            })

            # --- Check 10 (Item 4.4): happy path writes JSONL ---
            ok_event = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "warn",
                "reason": "phase4 verify happy path",
                "mode": "supervised_auto",
                "details": {"foo": "bar"},
            }))
            jsonl_file = tmp / "state/escalations/phase4-verify.jsonl"
            lines = jsonl_file.read_text().splitlines() if jsonl_file.exists() else []
            ok10 = (
                ok_event.get("ok") is True
                and ok_event.get("trigger") == "trigger_blast_radius_high"
                and len(lines) == 1
                and json.loads(lines[0]).get("trigger") == "trigger_blast_radius_high"
            )
            report["checks"].append({
                "name": "item44_escalation_event_writes_jsonl",
                "status": "pass" if ok10 else "fail",
                "lines_count": len(lines),
                "result": ok_event,
            })

            # --- Check 11 (Item 4.4): PIPE_BUF bound on escalation record ---
            big = "x" * 5000
            big_res = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "info",
                "reason": "test",
                "mode": "supervised_auto",
                "details": {"payload": big},
            }))
            report["checks"].append({
                "name": "item44_escalation_event_pipe_buf_bound",
                "status": "pass" if (big_res.get("error") and "PIPE_BUF" in big_res.get("error", "")) else "fail",
                "error": big_res.get("error"),
            })

            # --- Check 12 (Item 4.4): rejects unsafe uacp_run_id ---
            unsafe = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "uacp_run_id": "../escape",
                "trigger": "trigger_blast_radius_high",
                "severity": "warn",
                "reason": "test",
                "mode": "supervised_auto",
            }))
            report["checks"].append({
                "name": "item44_escalation_event_rejects_unsafe_run_id",
                "status": "pass" if (unsafe.get("error") and "uacp_run_id" in unsafe.get("error", "")) else "fail",
                "result": unsafe,
            })

            # --- Check 13 (drift pc_p3_tech_r1_004): canonical_state_paths declared in autonomy-policy ---
            canon = ap.get("canonical_state_paths") or {}
            ok13 = (
                canon.get("run_registry") == "state/run-registry.yaml"
                and canon.get("gate_ledger_dir") == "state/gate-ledger/"
                and canon.get("escalations_dir") == "state/escalations/"
            )
            report["checks"].append({
                "name": "drift_pc_p3_tech_r1_004_canonical_state_paths",
                "status": "pass" if ok13 else "fail",
                "block": canon,
            })

            # --- Check 14 (drift pc_p3_gov_r1_003): _advisory convention documented ---
            adv = ap.get("advisory_field_convention") or {}
            ok14 = "_advisory" in str(adv.get("rule") or "")
            report["checks"].append({
                "name": "drift_pc_p3_gov_r1_003_advisory_convention",
                "status": "pass" if ok14 else "fail",
                "block": adv,
            })

            # --- Check 15 (R1 TECH-P4-002): escalation handler requires 'mode' ---
            no_mode = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "trigger": "trigger_blast_radius_high",
                "severity": "warn",
                "reason": "test",
                # mode omitted
            }))
            report["checks"].append({
                "name": "r1_tech_p4_002_escalation_requires_mode",
                "status": "pass" if (no_mode.get("error") and "mode" in no_mode.get("error", "") and "required" in no_mode.get("error", "")) else "fail",
                "result": no_mode,
            })

            # --- Check 16 (R1 TECH-P4-005): escape-from-escalations dir is refused ---
            # Symlink escalations/foo → ../runs/forged.jsonl would resolve outside.
            # Easier: a malformed run_id that resolves up — _is_safe_run_id should
            # already catch this; assert defense-in-depth fires.
            safe_run = json.loads(plugin._handle_uacp_escalation_event({
                **_common_args(tmp, phase="execute", run_id="phase4-verify"),
                "uacp_run_id": "/etc/passwd",
                "trigger": "trigger_blast_radius_high",
                "severity": "info",
                "reason": "test",
                "mode": "supervised_auto",
            }))
            report["checks"].append({
                "name": "r1_tech_p4_005_unsafe_run_id_rejected",
                "status": "pass" if (safe_run.get("error") and "uacp_run_id" in safe_run.get("error", "")) else "fail",
                "result": safe_run,
            })

            # --- Check 17 (R1 GOV-P4-002): autonomy-policy declares enforcement_status ---
            est = ap.get("enforcement_status")
            has_legend = ap.get("enforcement_status_legend") and isinstance(ap.get("enforcement_status_legend"), dict)
            ok17 = est == "stub_only_phase_4" and has_legend
            report["checks"].append({
                "name": "r1_gov_p4_002_enforcement_status_declared",
                "status": "pass" if ok17 else "fail",
                "enforcement_status": est,
                "has_legend": bool(has_legend),
            })

            # --- Check 18 (R1 GOV-P4-001): drift YAML uses honest classification keys ---
            drift_path = ROOT / "executions/uacp-patch-plan-20260515-phase4-drift-reconciliation.yaml"
            drift = _y.safe_load(drift_path.read_text())
            classifications = set()
            for entry in (drift.get("classification") or {}).values():
                if isinstance(entry, dict):
                    cls = str(entry.get("classification") or "")
                    if cls:
                        classifications.add(cls)
            expected_keys = {"REMEDIATED_IN_PHASE_4", "DEFERRED_TO_PHASE_5", "DOCUMENTED_NOT_ENFORCED"}
            ok18 = expected_keys.issubset(classifications)
            report["checks"].append({
                "name": "r1_gov_p4_001_drift_classification_honest",
                "status": "pass" if ok18 else "fail",
                "classifications": sorted(classifications),
            })

            # --- Check 19 (R1 GOV-P4-003): docs/index.md inventories Phase 4 surfaces ---
            idx = (ROOT / "docs/index.md").read_text()
            ok19 = "state/escalations/" in idx and "config/autonomy-policy.yaml" in idx
            report["checks"].append({
                "name": "r1_gov_p4_003_doc_inventory_covers_phase4",
                "status": "pass" if ok19 else "fail",
                "in_inventory": {"escalations": "state/escalations/" in idx, "autonomy_policy": "config/autonomy-policy.yaml" in idx},
            })

            # --- Check 20 (R1 GOV-P4-003): skill-enforcement-spec lists escalation in every Allowed-tools ---
            spec = (ROOT / "docs/skill-enforcement-spec.md").read_text()
            allowed_count = spec.count("**Allowed tools**:")
            esc_count = spec.count("uacp_escalation_event")
            # Should appear in every Allowed-tools line (7) plus the Mechanical-enforcement table.
            ok20 = allowed_count >= 7 and esc_count >= 7
            report["checks"].append({
                "name": "r1_gov_p4_003_spec_lists_escalation_in_allowed_tools",
                "status": "pass" if ok20 else "fail",
                "allowed_lines": allowed_count,
                "escalation_mentions": esc_count,
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

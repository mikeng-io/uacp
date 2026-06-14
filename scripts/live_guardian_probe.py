#!/usr/bin/env python3
"""Safe live proof harness for UACP Hermes runtime adapter bindings.

This script performs non-destructive checks only:
- UACP-owned adapter source exists
- HERMES_ROOT/plugins symlinks point to UACP source
- Hermes config enables the expected plugins
- `hermes plugins list` reports expected plugins as enabled user plugins
- key UACP YAML artifacts parse
- known removed probe/duplicate plugin paths remain absent

It does not mutate runtime config, state, external systems, or protected paths.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import shutil
import time
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(json.dumps({"status": "error", "error": f"PyYAML unavailable: {exc}"}))
    raise SystemExit(2)

HOME = Path(os.environ.get("HERMES_HOME", "/home/norty/.hermes")).expanduser()
UACP_ROOT = Path(os.environ.get("UACP_ROOT", str(HOME / "uacp"))).expanduser()
HERMES_AGENT = Path(os.environ.get("HERMES_AGENT_ROOT", str(HOME / "hermes-agent"))).expanduser()
EXPECTED = ["thread_title_sync", "uacp_guardian"]
EXPECTED_GUARDIAN_TOOLS = ["uacp_state_write", "uacp_artifact_write", "uacp_doc_write", "uacp_config_write", "uacp_heartgate_check", "uacp_sandbox_check", "uacp_contained_shell"]


def check(condition: bool, name: str, evidence=None):
    return {"name": name, "status": "pass" if condition else "fail", "evidence": evidence}


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=60)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def _exercise_guardian_writers(checks):
    adapter_plugins_root = UACP_ROOT / "runtime-adapters/hermes/plugins"
    sys.path.insert(0, str(adapter_plugins_root))
    import uacp_guardian as guardian_plugin
    from uacp_guardian.kernel import Guardian, GuardianPolicy, make_event

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        (tmp_root / "config").mkdir(parents=True)
        (tmp_root / "docs").mkdir(parents=True)
        (tmp_root / "state/runs").mkdir(parents=True)
        shutil.copy2(UACP_ROOT / "config/guardian-policy.yaml", tmp_root / "config/guardian-policy.yaml")
        shutil.copy2(UACP_ROOT / "config/phase-transitions.yaml", tmp_root / "config/phase-transitions.yaml")
        old_env = {key: os.environ.get(key) for key in ["UACP_ROOT", "UACP_GUARDIAN_MODE"]}
        try:
            os.environ["UACP_ROOT"] = str(tmp_root)
            os.environ.pop("UACP_GUARDIAN_MODE", None)
            guardian_plugin._POLICY = None
            common = {
                "reason": "safe live probe temporary root",
                "authority_artifact": "verification/live-guardian-proof-20260514.yaml",
                "workspace": str(tmp_root),
                "uacp_run_id": "live-guardian-proof-20260514",
                "uacp_phase": "verify",
                "policy_version": "0.1",
                "declared_side_effects": "temporary proof write under isolated temp UACP root",
            }
            doc_result = json.loads(guardian_plugin._handle_uacp_doc_write({
                **common,
                "target_path": "docs/probe.md",
                "content": "# Probe\n",
            }))
            checks.append(check(doc_result.get("ok") is True and (tmp_root / "docs/probe.md").read_text() == "# Probe\n", "uacp_doc_write_positive_temp_root", doc_result))

            config_result = json.loads(guardian_plugin._handle_uacp_config_write({
                **common,
                "target_path": "config/probe.yaml",
                "content": "ok: true\n",
            }))
            checks.append(check(config_result.get("ok") is True and (tmp_root / "config/probe.yaml").exists(), "uacp_config_write_positive_temp_root", config_result))

            bad_yaml = json.loads(guardian_plugin._handle_uacp_config_write({
                **common,
                "target_path": "config/bad.yaml",
                "content": "ok: [unterminated\n",
            }))
            checks.append(check("error" in bad_yaml, "uacp_config_write_blocks_invalid_yaml", bad_yaml))

            bad_path = json.loads(guardian_plugin._handle_uacp_doc_write({
                **common,
                "target_path": "../escape.md",
                "content": "escape",
            }))
            checks.append(check("error" in bad_path, "uacp_doc_write_blocks_path_escape", bad_path))

            absolute_path = json.loads(guardian_plugin._handle_uacp_doc_write({
                **common,
                "target_path": str(tmp_root.parent / "absolute-escape.md"),
                "content": "escape",
            }))
            checks.append(check("error" in absolute_path, "uacp_doc_write_blocks_absolute_path", absolute_path))

            root_target = json.loads(guardian_plugin._handle_uacp_doc_write({
                **common,
                "target_path": ".",
                "content": "escape",
            }))
            checks.append(check("error" in root_target, "uacp_doc_write_blocks_root_target", root_target))

            directory_target = json.loads(guardian_plugin._handle_uacp_config_write({
                **common,
                "target_path": "config",
                "content": "ok: true\n",
            }))
            checks.append(check("error" in directory_target, "uacp_config_write_blocks_directory_target", directory_target))

            outside_dir = tmp_root.parent / "outside-uacp-writer-proof"
            outside_dir.mkdir(exist_ok=True)
            symlink_path = tmp_root / "docs" / "leak.md"
            symlink_path.symlink_to(outside_dir / "leak.md")
            symlink_result = json.loads(guardian_plugin._handle_uacp_doc_write({
                **common,
                "target_path": "docs/leak.md",
                "content": "escape",
            }))
            checks.append(check("error" in symlink_result and not (outside_dir / "leak.md").exists(), "uacp_doc_write_blocks_symlink_escape", symlink_result))

            symlink_parent = tmp_root / "config" / "outside"
            symlink_parent.symlink_to(outside_dir, target_is_directory=True)
            symlink_parent_result = json.loads(guardian_plugin._handle_uacp_config_write({
                **common,
                "target_path": "config/outside/leak.yaml",
                "content": "ok: true\n",
            }))
            checks.append(check("error" in symlink_parent_result and not (outside_dir / "leak.yaml").exists(), "uacp_config_write_blocks_symlink_parent_escape", symlink_parent_result))

            guardian = Guardian(GuardianPolicy.load(tmp_root))
            known_doc = guardian.evaluate(make_event(tool_name="uacp_doc_write", tool_provider="plugin", args={**common, "target_path": "docs/probe.md"}))
            checks.append(check(known_doc.decision == "allow_with_audit" and known_doc.category == "docs.uacp", "guardian_classifies_known_doc_writer", {"decision": known_doc.decision, "category": known_doc.category, "reason": known_doc.reason}))
            known_config = guardian.evaluate(make_event(tool_name="uacp_config_write", tool_provider="plugin", args={**common, "target_path": "config/probe.yaml"}))
            checks.append(check(known_config.decision == "allow_with_audit" and known_config.category == "config.uacp", "guardian_classifies_known_config_writer", {"decision": known_config.decision, "category": known_config.category, "reason": known_config.reason}))
            transition_ok = tmp_root / "state/runs/probe-verify-to-resolve.yaml"
            transition_ok.write_text("""kind: uacp.phase_transition
transition_id: probe-verify-to-resolve
run_id: live-guardian-proof-20260514
from_phase: verify
to_phase: resolve
decision: pass
invariant_summary:
  - id: authority.explicit
    status: pass
    evidence: safe probe
cluster_summary:
  - cluster_id: writer_hardening
    state: pass
    artifact_path: verification/live-guardian-proof-20260514-phase2-hardening.yaml
blockers: []
warnings: []
deferred_items: []
authority:
  requested_by: operator
  authorization_source: safe live proof harness
artifact_paths:
  - verification/live-guardian-proof-20260514-phase2-hardening.yaml
phase_local_granularity:
  phase: verify
  entry_estimate: 5
  exit_actual: 5
  delta_reason: safe probe
  downstream_projection:
    resolve: 5
composite_granularity: 5
human_involvement:
  required: false
  reason: safe probe only
  authority_needed: none
  decision_owner: none
  accepted_risk_artifact: ''
""", encoding="utf-8")
            heartgate_ok = json.loads(guardian_plugin._handle_uacp_heartgate_check({
                **common,
                "transition_path": "state/runs/probe-verify-to-resolve.yaml",
            }))
            checks.append(check(heartgate_ok.get("ok") is True and heartgate_ok.get("decision") == "pass", "uacp_heartgate_check_passes_valid_transition", heartgate_ok))

            transition_bad = tmp_root / "state/runs/probe-invalid-transition.yaml"
            transition_bad.write_text("""kind: uacp.phase_transition
transition_id: probe-invalid
run_id: live-guardian-proof-20260514
from_phase: execute
to_phase: resolve
decision: pass
invariant_summary: []
cluster_summary: []
blockers: []
warnings: []
deferred_items: []
authority: {}
artifact_paths: []
phase_local_granularity: {}
composite_granularity: 5
human_involvement: {}
""", encoding="utf-8")
            heartgate_bad = json.loads(guardian_plugin._handle_uacp_heartgate_check({
                **common,
                "transition_path": "state/runs/probe-invalid-transition.yaml",
            }))
            checks.append(check(heartgate_bad.get("ok") is False and heartgate_bad.get("decision") == "block", "uacp_heartgate_check_blocks_invalid_transition", heartgate_bad))

            heartgate_missing_context = json.loads(guardian_plugin._handle_uacp_heartgate_check({
                "transition_path": "state/runs/probe-verify-to-resolve.yaml",
                "authority_artifact": "verification/live-guardian-proof-20260514.yaml",
            }))
            checks.append(check("error" in heartgate_missing_context, "uacp_heartgate_check_blocks_missing_context", heartgate_missing_context))

            known_heartgate = guardian.evaluate(make_event(tool_name="uacp_heartgate_check", tool_provider="plugin", args={**common, "transition_path": "state/runs/probe-verify-to-resolve.yaml"}))
            checks.append(check(known_heartgate.decision == "allow_with_audit" and known_heartgate.category == "lifecycle.transition", "guardian_classifies_heartgate_check", {"decision": known_heartgate.decision, "category": known_heartgate.category, "reason": known_heartgate.reason}))
            sandbox_workspace = tmp_root.parent / "uacp-sandbox-workspace"
            sandbox_workspace.mkdir(exist_ok=True)
            sandbox_ok = json.loads(guardian_plugin._handle_uacp_sandbox_check({
                **common,
                "execution_workspace": str(sandbox_workspace),
                "tool_surface": "exec.shell",
                "backend": "local",
                "mechanism": "bwrap_readonly_root",
            }))
            checks.append(check(sandbox_ok.get("ok") is True and sandbox_ok.get("containment_verified") is True and sandbox_ok.get("allow_standard_tool_path") is False, "uacp_sandbox_check_proves_bwrap_but_not_standard_tool_path", sandbox_ok))

            sandbox_under_root = json.loads(guardian_plugin._handle_uacp_sandbox_check({
                **common,
                "execution_workspace": str(tmp_root / "docs"),
                "tool_surface": "exec.shell",
                "backend": "local",
                "mechanism": "bwrap_readonly_root",
            }))
            checks.append(check(sandbox_under_root.get("ok") is True and sandbox_under_root.get("containment_verified") is False, "uacp_sandbox_check_blocks_workspace_under_uacp_root", sandbox_under_root))

            sandbox_code = json.loads(guardian_plugin._handle_uacp_sandbox_check({
                **common,
                "execution_workspace": str(sandbox_workspace),
                "tool_surface": "exec.code_with_tool_proxy",
                "backend": "local-python",
                "mechanism": "bwrap_readonly_root",
            }))
            checks.append(check(sandbox_code.get("ok") is True and sandbox_code.get("containment_verified") is False, "uacp_sandbox_check_blocks_unproven_execute_code_backend", sandbox_code))

            known_sandbox = guardian.evaluate(make_event(tool_name="uacp_sandbox_check", tool_provider="plugin", args={**common, "execution_workspace": str(sandbox_workspace)}))
            checks.append(check(known_sandbox.decision == "allow_with_audit" and known_sandbox.category == "evidence.containment", "guardian_classifies_sandbox_check", {"decision": known_sandbox.decision, "category": known_sandbox.category, "reason": known_sandbox.reason}))
            contained_shell = guardian.evaluate(make_event(tool_name="uacp_contained_shell", tool_provider="plugin", args={**common, "workspace": str(sandbox_workspace), "command": "echo probe"}))
            checks.append(check(contained_shell.decision == "allow_with_audit" and contained_shell.category == "exec.shell.contained", "guardian_classifies_contained_shell", {"decision": contained_shell.decision, "category": contained_shell.category, "reason": contained_shell.reason}))
            shell_ok = json.loads(guardian_plugin._handle_uacp_contained_shell({
                **common,
                "workspace": str(sandbox_workspace),
                "command": "echo contained-ok",
                "timeout": 20,
            }))
            checks.append(check(shell_ok.get("ok") is True and shell_ok.get("containment_verified") is True and shell_ok.get("allow_standard_tool_path") is False and shell_ok.get("exit_code") == 0, "uacp_contained_shell_executes_inside_containment", shell_ok))
            attestation_id = shell_ok.get("attestation_id")
            if attestation_id:
                guardian_plugin._CONTAINED_SHELL_ATTESTATIONS[attestation_id]["expires_at"] = time.time() - 1
            shell_stale = json.loads(guardian_plugin._handle_uacp_contained_shell({
                **common,
                "workspace": str(sandbox_workspace),
                "command": "echo stale",
                "attestation_id": attestation_id or "stale",
            }))
            checks.append(check(shell_stale.get("ok") is True and shell_stale.get("containment_verified") is False and "expired" in shell_stale.get("verdict_reason", ""), "uacp_contained_shell_blocks_stale_attestation", shell_stale))
            shell_write_attempt = json.loads(guardian_plugin._handle_uacp_contained_shell({
                **common,
                "workspace": str(sandbox_workspace),
                "command": """python3 - <<'PY'
from pathlib import Path
probe = Path('/home/norty/.hermes/uacp/.contained_shell_probe')
try:
    probe.write_text('x', encoding='utf-8')
    print('unexpected-write')
except Exception as exc:
    print(f'blocked:{type(exc).__name__}')
PY""",
                "timeout": 20,
            }))
            checks.append(check(shell_write_attempt.get("ok") is True and shell_write_attempt.get("containment_verified") is True and shell_write_attempt.get("write_probe_blocked") is True and shell_write_attempt.get("exit_code") == 0 and "blocked:" in shell_write_attempt.get("stdout_tail", ""), "uacp_contained_shell_blocks_write_attempt_to_uacp_root", shell_write_attempt))
            shell_guard_block = guardian.evaluate(make_event(tool_name="terminal", tool_provider="core", args={**common, "command": "echo probe", "workspace": str(tmp_root), "filesystem_guard_verified": False}))
            checks.append(check(shell_guard_block.decision == "block" and shell_guard_block.category == "exec.shell" and "containment" in shell_guard_block.reason, "guardian_blocks_uacp_shell_without_containment", {"decision": shell_guard_block.decision, "category": shell_guard_block.category, "reason": shell_guard_block.reason}))
            code_guard_block = guardian.evaluate(make_event(tool_name="execute_code", tool_provider="core", args={**common, "code": "print('probe')", "workspace": str(tmp_root), "filesystem_guard_verified": False}))
            checks.append(check(code_guard_block.decision == "block" and code_guard_block.category == "exec.code_with_tool_proxy" and "containment" in code_guard_block.reason, "guardian_blocks_uacp_code_without_containment", {"decision": code_guard_block.decision, "category": code_guard_block.category, "reason": code_guard_block.reason}))
            unknown = guardian.evaluate(make_event(tool_name="unknown_plugin_mutator", tool_provider="plugin", args=common))
            checks.append(check(unknown.decision == "block" and unknown.category == "runtime.extension", "guardian_blocks_unknown_plugin_mutator", {"decision": unknown.decision, "category": unknown.category, "reason": unknown.reason}))
        finally:
            guardian_plugin._POLICY = None
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def main():
    checks = []
    # Source and symlink checks
    for plugin in EXPECTED:
        source = UACP_ROOT / "runtime-adapters/hermes/plugins" / plugin
        binding = HOME / "plugins" / plugin
        checks.append(check(source.exists(), f"source_exists:{plugin}", str(source)))
        checks.append(check(binding.is_symlink(), f"binding_is_symlink:{plugin}", str(binding)))
        target = binding.resolve() if binding.is_symlink() else None
        checks.append(check(target == source.resolve() if target else False, f"binding_targets_source:{plugin}", {"target": str(target) if target else "", "source": str(source.resolve()) if source.exists() else str(source)}))
        manifest_path = source / "plugin.yaml"
        checks.append(check(manifest_path.exists(), f"manifest_exists:{plugin}", str(manifest_path)))
        if plugin == "uacp_guardian" and manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            tools = manifest.get("tools") or []
            for tool in EXPECTED_GUARDIAN_TOOLS:
                checks.append(check(tool in tools, f"manifest_tool_registered:{tool}", tools))

    # Config checks
    config_path = HOME / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    enabled = (config.get("plugins") or {}).get("enabled") or []
    for plugin in EXPECTED:
        checks.append(check(plugin in enabled, f"config_enabled:{plugin}", enabled))

    # Hermes loader report
    loader = run(["hermes", "plugins", "list"], cwd=str(HERMES_AGENT))
    checks.append(check(loader["returncode"] == 0, "hermes_plugins_list_runs", {"stderr": loader["stderr"][-500:]}))
    out = loader["stdout"]
    for plugin in EXPECTED:
        checks.append(check(plugin in out and "enabled" in out and "user" in out, f"loader_reports_enabled_user:{plugin}", plugin))

    # YAML parse checks
    yaml_paths = [
        "config/runtime-bindings.yaml",
        "config/state.yaml",
        ".outputs/uacp-current-status.yaml",
        "verification/runtime-porting-20260514-cleanup-doc-sync.yaml",
    ]
    for rel in yaml_paths:
        path = UACP_ROOT / rel
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
            checks.append(check(True, f"yaml_parse:{rel}", rel))
        except Exception as exc:
            checks.append(check(False, f"yaml_parse:{rel}", str(exc)))

    # Safe temporary-root writer/Guardian checks
    try:
        _exercise_guardian_writers(checks)
    except Exception as exc:
        checks.append(check(False, "guardian_writer_exercise_unhandled_exception", f"{type(exc).__name__}: {exc}"))

    # Cleanup invariants
    absent_paths = [
        UACP_ROOT / "runtime-adapters/hermes/plugins/uacp_symlink_probe",
        HERMES_AGENT / "plugins/thread_title_sync",
        HERMES_AGENT / "plugins/uacp_guardian",
    ]
    for p in absent_paths:
        checks.append(check(not p.exists(), f"absent:{p}", str(p)))

    status = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    result = {
        "schema_version": "0.1",
        "kind": "uacp.live_guardian_probe_result",
        "status": status,
        "uacp_root": str(UACP_ROOT),
        "hermes_home": str(HOME),
        "hermes_agent_root": str(HERMES_AGENT),
        "checks": checks,
    }
    print(yaml.safe_dump(result, sort_keys=False, allow_unicode=True, width=1000))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

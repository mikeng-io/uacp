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
EXPECTED_GUARDIAN_TOOLS = ["uacp_state_write", "uacp_artifact_write", "uacp_doc_write", "uacp_config_write"]


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
        shutil.copy2(UACP_ROOT / "config/guardian-policy.yaml", tmp_root / "config/guardian-policy.yaml")
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
        "outputs/uacp-current-status.yaml",
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

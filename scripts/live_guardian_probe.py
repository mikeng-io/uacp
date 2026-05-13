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


def check(condition: bool, name: str, evidence=None):
    return {"name": name, "status": "pass" if condition else "fail", "evidence": evidence}


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=60)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


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
        checks.append(check((source / "plugin.yaml").exists(), f"manifest_exists:{plugin}", str(source / "plugin.yaml")))

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

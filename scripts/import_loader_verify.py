#!/usr/bin/env python3
"""Verify UACP Guardian works when loaded under a plugin-host alias.

The Hermes plugin host may load package directories by file path instead of by
their top-level package name. In that loader shape, package-relative imports
work, but hard-coded imports of ``uacp_guardian.kernel`` do not.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "runtime-adapters" / "hermes" / "plugins"
PKG_DIR = PLUGIN_ROOT / "uacp_guardian"


def _load_plugin_under_alias():
    plugins_root = str(PLUGIN_ROOT.resolve())
    sys.path = [p for p in sys.path if str(Path(p or ".").resolve()) != plugins_root]
    for key in list(sys.modules):
        if (
            key == "uacp_guardian"
            or key.startswith("uacp_guardian.")
            or key == "alias_uacp_guardian"
            or key.startswith("alias_uacp_guardian.")
        ):
            sys.modules.pop(key, None)

    spec = importlib.util.spec_from_file_location(
        "alias_uacp_guardian",
        PKG_DIR / "__init__.py",
        submodule_search_locations=[str(PKG_DIR)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to create alias import spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _prepare_root(tmp: Path) -> None:
    for sub in ("config", ".uacp/state", ".uacp/state/escalations"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    # guardian policy is now sourced from config/uacp.toml [guardian] via
    # config.py — guardian-policy.yaml has been deleted (config-collapse Slice 3).
    # artifact-schemas.yaml deleted in Slice 5 W3; schemas codified to
    # engines/domain/artifact_schema.py; knobs in uacp.toml [scope].
    for name in (
        "uacp.toml",
        "phase-transitions.yaml",
        "state.yaml",
    ):
        shutil.copy2(ROOT / "config" / name, tmp / "config" / name)


def _common_args(tmp: Path, run_id: str) -> dict:
    return {
        "workspace": str(tmp),
        "uacp_run_id": run_id,
        "uacp_phase": "execute",
        "policy_version": "0.1",
        "declared_side_effects": "import loader verification",
        "reason": "import loader verification",
        "authority_artifact": "verification/import-loader-verify.yaml",
    }


def main() -> int:
    saved_env = {k: os.environ.get(k) for k in ("UACP_ROOT",)}
    report: dict = {"checks": []}
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            _prepare_root(tmp)
            os.environ["UACP_ROOT"] = str(tmp)
            plugin = _load_plugin_under_alias()
            plugin._POLICY = None
            plugin._POLICY_ERROR = ""
            plugin._PHASE_CONFIG = None

            report["checks"].append(
                {
                    "name": "alias_package_relative_kernel_loaded",
                    "status": "pass"
                    if "alias_uacp_guardian.kernel" in sys.modules
                    else "fail",
                }
            )

            run_id = "import-loader-verify"
            registry_args = {
                **_common_args(tmp, run_id),
                "op": "deregister",
                "entry": {"run_id": run_id},
            }
            registry = json.loads(plugin._handle_uacp_run_registry_update(registry_args))
            report["checks"].append(
                {
                    "name": "run_registry_update_alias_loaded",
                    "status": "pass" if registry.get("ok") is True else "fail",
                    "result": registry,
                }
            )

            escalation_args = {
                **_common_args(tmp, run_id),
                "trigger": "trigger_blast_radius_high",
                "severity": "info",
                "mode": "manual",
            }
            escalation = json.loads(plugin._handle_uacp_escalation_event(escalation_args))
            report["checks"].append(
                {
                    "name": "escalation_event_alias_loaded",
                    "status": "pass" if escalation.get("ok") is True else "fail",
                    "result": escalation,
                }
            )
    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    failed = [c for c in report["checks"] if c.get("status") != "pass"]
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

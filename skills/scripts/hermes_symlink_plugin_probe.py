#!/usr/bin/env python3
"""Non-destructive Hermes user-plugin symlink discovery probe for UACP runtime-adapter work.

Creates a temporary probe plugin under a supplied UACP worktree/runtime-adapter root,
binds it into HERMES_HOME/plugins by symlink, verifies Hermes plugin discovery sees it
as a user plugin, then removes the symlink. It does not bind real production plugins.

Usage:
  python scripts/hermes_symlink_plugin_probe.py \
    --hermes-agent-root /path/to/hermes-agent \
    --hermes-home /path/to/.hermes \
    --adapter-root /path/to/uacp-worktree/runtime-adapters/hermes/plugins
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROBE_NAME = "uacp_symlink_probe"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hermes-agent-root", required=True)
    parser.add_argument("--hermes-home", required=True)
    parser.add_argument("--adapter-root", required=True)
    args = parser.parse_args()

    hermes_agent_root = Path(args.hermes_agent_root).resolve()
    hermes_home = Path(args.hermes_home).resolve()
    adapter_root = Path(args.adapter_root).resolve()
    probe_src = adapter_root / PROBE_NAME
    probe_link = hermes_home / "plugins" / PROBE_NAME

    if probe_src.exists():
        shutil.rmtree(probe_src)
    probe_src.mkdir(parents=True)
    write(
        probe_src / "plugin.yaml",
        "name: uacp_symlink_probe\n"
        "version: \"0.1.0\"\n"
        "description: \"Temporary UACP runtime-adapter symlink discovery probe.\"\n"
        "kind: standalone\n"
        "provides_hooks:\n"
        "  - on_session_start\n",
    )
    write(
        probe_src / "__init__.py",
        '"""UACP runtime-adapter symlink discovery probe."""\n'
        "LOADED_FROM_UACP_SYMLINK_PROBE = True\n\n"
        "def register(ctx):\n"
        "    def _noop_on_session_start(**kwargs):\n"
        "        return None\n"
        "    ctx.register_hook(\"on_session_start\", _noop_on_session_start)\n",
    )

    (hermes_home / "plugins").mkdir(parents=True, exist_ok=True)
    if probe_link.exists() or probe_link.is_symlink():
        if not probe_link.is_symlink() or probe_link.resolve() != probe_src:
            raise RuntimeError(f"Refusing to overwrite pre-existing path: {probe_link}")
        probe_link.unlink()
    probe_link.symlink_to(probe_src, target_is_directory=True)

    probe_py = f'''
import json, os, sys
from pathlib import Path
sys.path.insert(0, {str(hermes_agent_root)!r})
os.environ["HERMES_HOME"] = {str(hermes_home)!r}
import hermes_cli.plugins as plugins
plugins._get_enabled_plugins = lambda: {{{PROBE_NAME!r}}}
plugins._get_disabled_plugins = lambda: set()
pm = plugins.get_plugin_manager()
pm.discover_and_load(force=True)
loaded = pm._plugins.get({PROBE_NAME!r})
res = {{
    "loaded_present": loaded is not None,
    "enabled": bool(getattr(loaded, "enabled", False)) if loaded else False,
    "error": getattr(loaded, "error", None) if loaded else "missing",
    "manifest_source": getattr(getattr(loaded, "manifest", None), "source", None) if loaded else None,
    "manifest_path": getattr(getattr(loaded, "manifest", None), "path", None) if loaded else None,
    "hooks_registered": getattr(loaded, "hooks_registered", []) if loaded else [],
    "link_is_symlink": Path({str(probe_link)!r}).is_symlink(),
    "link_realpath": str(Path({str(probe_link)!r}).resolve()),
}}
print(json.dumps(res, sort_keys=True))
raise SystemExit(0 if res["loaded_present"] and res["enabled"] and res["manifest_source"] == "user" and "on_session_start" in res["hooks_registered"] else 2)
'''
    try:
        proc = subprocess.run(
            [sys.executable, "-c", probe_py],
            cwd=str(hermes_agent_root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "HERMES_HOME": str(hermes_home), "PYTHONPATH": str(hermes_agent_root)},
        )
        print(proc.stdout.strip())
        return proc.returncode
    finally:
        if probe_link.is_symlink() and probe_link.resolve() == probe_src:
            probe_link.unlink()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Codeflair bootstrap — install the per-language SCIP indexers REPO-LOCALLY (no global).

    python3 scripts/bootstrap.py

- Python + TypeScript indexers (scip-python, scip-typescript) are npm packages: installed
  into codeflair/vendor/node_modules via `npm install` (uses the user's npm — a given for
  anyone doing TS/JS work — but writes nothing to the global scope).
- Go indexer (scip-go) + the scip CLI are Go tools, installed with `go install` to the
  user's Go bin. We don't auto-install those (Go toolchain is the user's call, CF-D12); we
  check and print the command if missing.

The engine itself is a Python package; set it up with uv:
    uv venv .venv && uv pip install -e '.[treesitter]' --python .venv/bin/python
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"

_GO_TOOLS = {
    "scip-go": "go install github.com/sourcegraph/scip-go/cmd/scip-go@latest",
    "scip": "(prebuilt) github.com/sourcegraph/scip/releases  — or go install ...@latest",
}


def _has(tool: str) -> bool:
    return shutil.which(tool) is not None


def main() -> int:
    print("Codeflair bootstrap — repo-local SCIP indexers\n")

    # 1. npm indexers (Python + TypeScript), installed into vendor/node_modules
    if not _has("npm"):
        print("✗ npm not found — needed for the Python/TypeScript SCIP indexers.")
        print("  Install Node (which ships npm); then re-run. (A given if you do TS/JS work.)")
        return 1
    print(f"• npm install (repo-local) in {VENDOR} …")
    rc = subprocess.run(["npm", "install", "--silent"], cwd=VENDOR).returncode
    if rc != 0:
        print("✗ npm install failed")
        return rc
    bins = VENDOR / "node_modules" / ".bin"
    for tool in ("scip-python", "scip-typescript"):
        ok = (bins / tool).exists()
        print(f"  {'✓' if ok else '✗'} {tool}  ({bins / tool})")

    # 2. Go tools — checked, not auto-installed (toolchain is the user's call)
    print("\n• Go indexer + scip CLI (install yourself if missing):")
    for tool, how in _GO_TOOLS.items():
        if _has(tool):
            print(f"  ✓ {tool}")
        else:
            print(f"  ✗ {tool} — {how}")

    print("\nEngine: uv venv .venv && uv pip install -e '.[treesitter]' --python .venv/bin/python")
    print("Done. SCIP indexers are repo-local; nothing was installed globally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prove the shipped tree really loads on the DECLARED ``requires-python`` floor.

Run this **with a floor interpreter** (CI's `test-floor` job provisions one from
``requires-python``); it is not useful on a newer Python, and says so rather than
passing vacuously.

Why this exists
---------------
CI otherwise runs 3.13/3.14 only, while ``pyproject.toml`` advertises
``>=3.10`` and real host runtimes ship older interpreters (Hermes' venv is
3.11). A single newer-than-floor construct is then a SyntaxError at *import*
time on a supported configuration — and because host plugin loaders wrap each
plugin in its own ``except``, the user sees "plugin disabled / error", not a
crash. That is how ``class Loaded[T]`` (PEP 695, 3.12+) shipped green.

Two layers, deliberately split
------------------------------
* ``tests/unit/test_python_version_floor.py`` re-parses the tree with the
  floor's *grammar* via ``ast.parse(feature_version=…)``. It runs on every
  interpreter, so a developer on 3.13 sees the break immediately — but it can
  only see syntax.
* **This script** runs on a real floor interpreter, so it additionally catches
  what grammar cannot: a stdlib symbol that does not exist yet at the floor
  (``itertools.batched``, ``typing.override``, ``asyncio.TaskGroup``, …), which
  fails at import, not at parse.

Exit code 0 = every shipped module compiled and every entrypoint imported.
"""

from __future__ import annotations

import compileall
import importlib
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Source roots that ship to users or are imported by a host-runtime adapter.
_SHIPPED_ROOTS = ("skills", "runtime-adapters", "scripts", "tools/proving-ground")

_SKIP_DIR_PARTS = frozenset({"__pycache__", "vendor", "node_modules", ".venv", ".worktrees"})

# Entrypoints that MUST import cleanly: the modules a host runtime or the MCP
# launcher actually loads. Compiling proves syntax; importing these proves the
# stdlib surface they touch exists at the floor. Each entry is
# ``(sys.path additions, module name)`` mirroring how the runtime bootstraps it.
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"
_HERMES_PLUGINS = _REPO_ROOT / "runtime-adapters" / "hermes" / "plugins"

# Import names of DECLARED optional extras (pyproject `[project.optional-dependencies]`).
# Only these may be absent without failing — see the ImportError branch below for
# why this must be an allowlist rather than a `sys.stdlib_module_names` test.
_OPTIONAL_DISTRIBUTIONS = frozenset(
    {
        "mcp",
        "anyio",  # [mcp]
        "lancedb",
        "sentence_transformers",  # [oracle-e2e]
        "pytest",
        "ruff",
        "pyright",  # [dev]
    }
)

_ENTRYPOINTS: tuple[tuple[tuple[Path, ...], str], ...] = (
    ((_CORE_SCRIPTS,), "tool_specs"),
    ((_CORE_SCRIPTS,), "governed_handlers"),
    ((_CORE_SCRIPTS,), "engines.io"),
    ((_CORE_SCRIPTS,), "engines.oracle"),
    ((_CORE_SCRIPTS, _HERMES_PLUGINS), "uacp_guardian"),
)


def _declared_floor() -> tuple[int, int]:
    text = (_REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r'^requires-python\s*=\s*"[><=~^]*\s*(\d+)\.(\d+)', text, re.MULTILINE)
    if not m:
        sys.exit("FAIL: could not read `requires-python` from pyproject.toml")
    return int(m.group(1)), int(m.group(2))


def _check_running_on_floor(floor: tuple[int, int]) -> None:
    running = sys.version_info[:2]
    if running != floor:
        sys.exit(
            f"FAIL: this check is only meaningful on the declared floor.\n"
            f"  requires-python floor : {floor[0]}.{floor[1]}\n"
            f"  running interpreter   : {running[0]}.{running[1]}\n"
            "Run it under the floor interpreter (CI's `test-floor` job does this),\n"
            "e.g. `uv run --python "
            f"{floor[0]}.{floor[1]} python scripts/check_python_floor.py`.\n"
            "Refusing to report a pass that proves nothing."
        )


def _compile_shipped_sources(floor: tuple[int, int]) -> int:
    """Byte-compile every shipped source on THIS (floor) interpreter."""
    failed = 0
    checked = 0
    for root in _SHIPPED_ROOTS:
        base = _REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if _SKIP_DIR_PARTS.intersection(path.relative_to(_REPO_ROOT).parts):
                continue
            checked += 1
            # quiet=1 still prints the error body, which is what we want to read.
            if not compileall.compile_file(path, quiet=1, force=True):
                failed += 1
    if not checked:
        sys.exit(f"FAIL: found no sources under {_SHIPPED_ROOTS!r} — this check would be vacuous")
    print(f"compiled {checked} shipped source file(s) on Python {floor[0]}.{floor[1]}")
    return failed


def _import_entrypoints() -> int:
    failed = 0
    for extra_paths, module in _ENTRYPOINTS:
        for p in extra_paths:
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
        try:
            importlib.import_module(module)
        except SyntaxError as exc:  # the defect class this whole job exists for
            print(f"FAIL import {module}: SyntaxError {exc.filename}:{exc.lineno}: {exc.msg}")
            failed += 1
        except ImportError as exc:
            # Classify against an ALLOWLIST of declared optional extras, never
            # against `sys.stdlib_module_names`. The obvious-looking check —
            # "is it stdlib?" — is exactly backwards here: a module that is
            # stdlib on a NEWER Python (tomllib, added in 3.11) is absent from
            # the FLOOR interpreter's own `stdlib_module_names`, so it would be
            # waved through as "optional dependency" — silently skipping the
            # one defect class this layer exists to catch. Anything not
            # explicitly declared optional in pyproject.toml is a failure.
            name = (getattr(exc, "name", "") or "").split(".")[0]
            if name in _OPTIONAL_DISTRIBUTIONS:
                print(f"skip  {module}: declared-optional dependency absent ({name})")
            else:
                print(
                    f"FAIL import {module}: module {name!r} unavailable at the floor "
                    f"and not a declared optional extra — likely a newer-than-floor "
                    f"stdlib module: {exc}"
                )
                failed += 1
        except AttributeError as exc:
            print(f"FAIL import {module}: likely newer-than-floor stdlib attribute: {exc}")
            failed += 1
        else:
            print(f"ok    import {module}")
    return failed


def main() -> int:
    floor = _declared_floor()
    _check_running_on_floor(floor)

    failed = _compile_shipped_sources(floor)
    failed += _import_entrypoints()

    if failed:
        print(
            f"\nFAIL: {failed} floor violation(s) on Python {floor[0]}.{floor[1]}.\n"
            "On a host runtime at the floor these break at import time, and a\n"
            "per-plugin exception handler turns that into a silently disabled plugin.\n"
            "Either rewrite to floor-compatible code, or raise `requires-python`\n"
            "AND ruff's `target-version` together, deliberately."
        )
        return 1
    print(f"\nPASS: the shipped tree loads on Python {floor[0]}.{floor[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

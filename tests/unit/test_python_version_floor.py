"""Guard: every shipped Python source file MUST parse under the declared floor.

``pyproject.toml`` declares ``requires-python = ">=3.10"`` and the Claude Code
plugin manifest ships an even looser ``mcp`` launcher — so a normal user, or a
host runtime such as Hermes (whose venv is 3.11), can legitimately import this
code on an interpreter older than CI's. A single 3.12-only construct anywhere in
the tree is then a **SyntaxError at import time**, and because host plugin
loaders catch per-plugin exceptions, the failure surfaces as "plugin marked
error" rather than a crash — silent, and invisible to every test that runs on a
modern interpreter.

That is exactly how ``class Loaded[T]`` (PEP 695, 3.12+) reached ``main`` while
CI was green: CI runs 3.13 and 3.14 only, and ruff's ``target-version`` was
pinned to the CI interpreter rather than to the declared floor, so neither the
test suite nor the linter ever exercised the contract the package advertises.

This test closes that gap on **any** interpreter by re-parsing the tree with the
floor's grammar via ``ast.parse(..., feature_version=...)``, so it fails on the
3.13 developer laptop and in 3.13 CI, not only on a machine that happens to run
the oldest supported Python.

Scope note: ``feature_version`` constrains the *grammar*, not the standard
library. It catches syntax-level floor violations (PEP 695 generics, ``match``,
walrus, ``except*``); it does not catch a newer-than-floor stdlib API. Those need
the real-interpreter job in CI. This guard is the cheap, always-on half.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Source roots that ship to users or get imported by a host runtime adapter.
_SHIPPED_ROOTS = ("skills", "runtime-adapters", "scripts", "tools/proving-ground")

_SKIP_DIR_PARTS = frozenset({"__pycache__", ".worktrees", "vendor", "node_modules", ".venv"})


def _declared_floor() -> tuple[int, int]:
    """Read ``requires-python`` from pyproject.toml as a ``(major, minor)`` pair."""
    text = (_REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r'^requires-python\s*=\s*"[><=~^]*\s*(\d+)\.(\d+)', text, re.MULTILINE)
    assert m, "could not find `requires-python` in pyproject.toml"
    return int(m.group(1)), int(m.group(2))


def _shipped_sources() -> list[Path]:
    out: list[Path] = []
    for root in _SHIPPED_ROOTS:
        base = _REPO_ROOT / root
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            # Match against the REPO-RELATIVE parts: the absolute path may itself
            # sit under a checkout directory whose name collides with this skip
            # set (e.g. a `.worktrees/<name>/` worktree), which would silently
            # skip every file and make the sweep vacuous.
            if _SKIP_DIR_PARTS.intersection(path.relative_to(_REPO_ROOT).parts):
                continue
            out.append(path)
    return sorted(out)


def test_floor_is_reachable_by_this_interpreter() -> None:
    """Precondition: ``feature_version`` can only constrain the grammar DOWN to an
    older Python, never up to a newer one. If the declared floor were somehow above
    the running interpreter, every parse below would be checked against the wrong
    (older) grammar and the sweep would not mean what it claims."""
    floor = _declared_floor()
    assert floor <= sys.version_info[:2], (
        f"declared floor {floor} is newer than the running interpreter "
        f"{sys.version_info[:2]}; `ast.parse(feature_version=…)` cannot check a "
        "grammar newer than the one it is running, so this guard would be unsound"
    )


def test_pep695_is_actually_rejected_at_the_floor() -> None:
    """Non-vacuity proof: the mechanism this guard relies on must really reject
    the construct that caused the original defect. Without this, a future change
    to ``feature_version`` semantics would turn the sweep below into a no-op that
    passes on an empty check."""
    floor = _declared_floor()
    if floor >= (3, 12):
        pytest.skip("floor has moved to 3.12+; PEP 695 is legal there")
    with pytest.raises(SyntaxError):
        ast.parse("class Loaded[T]:\n    pass\n", feature_version=floor)


def test_shipped_sources_parse_at_declared_floor() -> None:
    floor = _declared_floor()
    sources = _shipped_sources()
    assert sources, f"found no Python sources under {_SHIPPED_ROOTS!r} — the sweep would be vacuous"

    failures: list[str] = []
    for path in sources:
        try:
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
                feature_version=floor,
            )
        except SyntaxError as exc:
            rel = path.relative_to(_REPO_ROOT)
            failures.append(f"  {rel}:{exc.lineno}: {exc.msg}")

    assert not failures, (
        f"{len(failures)} shipped source file(s) use syntax newer than the declared "
        f"floor Python {floor[0]}.{floor[1]} (`requires-python` in pyproject.toml).\n"
        + "\n".join(failures)
        + "\n\nOn a host runtime at the floor these raise SyntaxError at import time, "
        "and a per-plugin exception handler turns that into a silently disabled "
        "plugin. Either rewrite to floor-compatible syntax, or raise "
        "`requires-python` (and ruff's `target-version`) deliberately."
    )

"""Guard: the Ruff pin in pyproject.toml and the ruff-pre-commit rev in
.pre-commit-config.yaml MUST stay identical.

The pre-commit hook formats with the SAME Ruff version CI uses; if the two pins
drift, local `pre-commit` and CI format/lint with different Ruff versions and
silently disagree. Dependabot tracks these in two separate ecosystems (pip +
pre-commit), so it can open independent PRs that bump one but not the other —
this test fail-closes that drift at the required `pytest` gate, regardless of how
the bump arrived (split Dependabot PRs, a partial merge, or a manual edit).
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _pyproject_ruff_version() -> str:
    text = (_REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r"ruff==([0-9][0-9.]*)", text)
    assert m, "could not find a pinned `ruff==<version>` in pyproject.toml"
    return m.group(1)


def _precommit_ruff_version() -> str:
    text = (_REPO_ROOT / ".pre-commit-config.yaml").read_text()
    # The ruff-pre-commit repo line, then its `rev: vX.Y.Z` (optionally commented).
    m = re.search(r"ruff-pre-commit.*?rev:\s*v?([0-9][0-9.]*)", text, re.DOTALL)
    assert m, "could not find ruff-pre-commit `rev:` in .pre-commit-config.yaml"
    return m.group(1)


def test_ruff_pin_matches_precommit_rev() -> None:
    pyproject = _pyproject_ruff_version()
    precommit = _precommit_ruff_version()
    assert pyproject == precommit, (
        f"Ruff version drift: pyproject.toml pins ruff=={pyproject} but "
        f".pre-commit-config.yaml ruff-pre-commit rev is v{precommit}. "
        "These MUST match so local pre-commit and CI use the same Ruff. "
        "Bump both pins together (they are tracked in separate Dependabot "
        "ecosystems and can drift if updated independently)."
    )

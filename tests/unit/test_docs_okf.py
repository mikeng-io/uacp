"""OKF frontmatter regression guard for docs/.

Every *.md file under docs/ (recursively) — except files named INDEX.md
(the per-directory index convention) — must carry valid OKF frontmatter.

Required fields
---------------
- type        : one of {adr, policy, spec, reference, guide, plan, design, decision}
- title       : non-empty string
- description : non-empty string

Parse strategy: split on the leading ``---`` delimiter (``text.split("---", 2)[1]``)
then ``yaml.safe_load`` — identical approach to
``tests/unit/skills/test_okf_frontmatter.py`` (the corpus-scoped twin of this file).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

VALID_TYPES = {"adr", "policy", "spec", "reference", "guide", "plan", "design", "decision"}

# Minimum expected doc count — guards against an empty glob silently vacuousing the suite.
# There are 69 docs in docs/ as of the doc-architecture-refresh branch.
MIN_DOC_COUNT = 60


def _docs_okf_files() -> list[Path]:
    """Return all *.md files under docs/, recursively, excluding INDEX.md."""
    return sorted(
        p
        for p in DOCS_DIR.rglob("*.md")
        if p.name != "INDEX.md"
    )


# ---------------------------------------------------------------------------
# Guard: ensure the collector is non-vacuous
# ---------------------------------------------------------------------------


def test_docs_okf_collector_non_vacuous() -> None:
    """The collector must find at least MIN_DOC_COUNT docs.

    If this fails, the glob is broken or docs/ was moved — do not let the
    parametrized suite pass vacuously on an empty list.
    """
    docs = _docs_okf_files()
    assert len(docs) >= MIN_DOC_COUNT, (
        f"docs/ OKF collector found only {len(docs)} docs "
        f"(expected ≥ {MIN_DOC_COUNT}). "
        f"Check DOCS_DIR={DOCS_DIR}."
    )


# ---------------------------------------------------------------------------
# Parametrized: OKF frontmatter enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doc",
    _docs_okf_files(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_docs_okf_frontmatter_present_and_valid(doc: Path) -> None:
    """Every docs/ OKF file must carry valid frontmatter with required fields."""
    rel = str(doc.relative_to(REPO_ROOT))
    text = doc.read_text(encoding="utf-8")

    # --- presence check ---
    assert text.startswith("---"), (
        f"{rel}: missing OKF frontmatter — file must start with '---\\n'"
    )
    parts = text.split("---", 2)  # ['', '<yaml>', '<body>']
    assert len(parts) >= 3, (
        f"{rel}: malformed OKF frontmatter — could not find closing '---'"
    )

    # --- parse check ---
    fm = yaml.safe_load(parts[1])
    assert isinstance(fm, dict), (
        f"{rel}: OKF frontmatter did not parse as a YAML mapping"
    )

    # --- type field ---
    assert "type" in fm, f"{rel}: OKF frontmatter missing required field 'type'"
    assert fm["type"] in VALID_TYPES, (
        f"{rel}: 'type' value {fm['type']!r} is not one of {sorted(VALID_TYPES)}"
    )

    # --- title field ---
    assert "title" in fm, f"{rel}: OKF frontmatter missing required field 'title'"
    assert isinstance(fm["title"], str) and fm["title"].strip(), (
        f"{rel}: 'title' must be a non-empty string"
    )

    # --- description field ---
    assert "description" in fm, (
        f"{rel}: OKF frontmatter missing required field 'description'"
    )
    assert isinstance(fm["description"], str) and fm["description"].strip(), (
        f"{rel}: 'description' must be a non-empty string"
    )

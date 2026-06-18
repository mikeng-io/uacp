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

# The allowed top-level governance taxonomy under docs/. A new top-level category
# must be a deliberate change (update this set AND the policy in CONTRIBUTING.md
# "Documentation — what belongs in docs/"), never an ad-hoc drop.
ALLOWED_SUBDIRS = {
    "policy",
    "lifecycle",
    "runtime",
    "reference",
    "architecture",
    "decisions",
    "guides",
    "plans",
    "archived",
}

# Per-subdir type constraints (only where the policy makes it unambiguous).
# docs/runtime/ holds runtime-NEUTRAL normative contracts (type: spec). A runtime
# how-to (type: guide — install/wire a specific runtime) belongs with the adapter
# (runtime-adapters/<x>/README.md), NOT in docs/. See CONTRIBUTING.md.
SUBDIR_ALLOWED_TYPES = {
    "runtime": {"spec"},
}

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


def _all_docs_markdown() -> list[Path]:
    """Every *.md under docs/ (including INDEX.md) — for location/placement checks."""
    return sorted(DOCS_DIR.rglob("*.md"))


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


# ---------------------------------------------------------------------------
# Placement policy: allowed subdirs + per-subdir type constraints
# (mechanical enforcement of CONTRIBUTING.md "what belongs in docs/")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doc",
    _all_docs_markdown(),
    ids=lambda p: str(p.relative_to(DOCS_DIR)),
)
def test_docs_file_in_allowed_subdir(doc: Path) -> None:
    """Every docs/*.md is a top-level file (e.g. INDEX.md, arc42-index.md) or lives
    under an allowed governance subdir. Blocks ad-hoc new categories and
    runtime/skill/corpus material being dropped into docs/."""
    rel = doc.relative_to(DOCS_DIR)
    if len(rel.parts) == 1:
        return  # top-level docs/ file — allowed
    top = rel.parts[0]
    assert top in ALLOWED_SUBDIRS, (
        f"docs/{rel}: '{top}/' is not an allowed docs/ subdirectory "
        f"{sorted(ALLOWED_SUBDIRS)}. Runtime/skill/corpus material does not belong "
        f"in docs/ — see CONTRIBUTING.md 'what belongs in docs/'."
    )


@pytest.mark.parametrize(
    "doc",
    _docs_okf_files(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_docs_subdir_type_constraint(doc: Path) -> None:
    """Subdirs with a pinned type set only accept those types. docs/runtime/ holds
    runtime-NEUTRAL specs; a runtime how-to (type: guide) belongs with the adapter,
    not in docs/runtime/."""
    rel = doc.relative_to(DOCS_DIR)
    if len(rel.parts) < 2:
        return
    top = rel.parts[0]
    allowed = SUBDIR_ALLOWED_TYPES.get(top)
    if allowed is None:
        return
    fm = yaml.safe_load(doc.read_text(encoding="utf-8").split("---", 2)[1])
    assert fm.get("type") in allowed, (
        f"docs/{rel}: type {fm.get('type')!r} not allowed in docs/{top}/ "
        f"(allowed: {sorted(allowed)}). A runtime-specific how-to belongs in "
        f"runtime-adapters/, not docs/runtime/ — see CONTRIBUTING.md."
    )

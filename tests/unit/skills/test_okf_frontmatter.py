"""OKF frontmatter tripwire for UACP knowledge and reference docs.

Open Knowledge Format (OKF) frontmatter is required on every *.md file in:
  - skills/uacp-core/references/
  - .uacp/knowledge/

with the sole exemption of per-directory index.md files.

Required fields:
  - type: one of {contract, pattern, digest, lessons, analysis}
  - title: non-empty string
  - description: non-empty string

Optional (required for digest-typed docs):
  - resource: path string

Parse strategy: split on the leading ``---`` delimiter to avoid accidental
matches in the body; use yaml.safe_load for correctness.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCES_DIR = REPO_ROOT / "skills" / "uacp-core" / "references"
KNOWLEDGE_DIR = REPO_ROOT / ".uacp" / "knowledge"

VALID_TYPES = {"contract", "pattern", "digest", "lessons", "analysis"}

# Minimum expected doc count — guards against an empty glob silently vacuousing the suite.
MIN_DOC_COUNT = 30


def _okf_docs() -> list[Path]:
    """Return all *.md files in the two OKF directories, excluding index.md."""
    refs = sorted(p for p in REFERENCES_DIR.glob("*.md") if p.name != "index.md")
    knowledge = sorted(p for p in KNOWLEDGE_DIR.glob("*.md") if p.name != "index.md")
    return refs + knowledge


# ---------------------------------------------------------------------------
# Guard: ensure the collector is non-vacuous
# ---------------------------------------------------------------------------


def test_okf_doc_collector_non_vacuous() -> None:
    """The collector must find at least MIN_DOC_COUNT docs.

    If this fails, the glob is broken or the directories were moved — do not
    let the parametrized suite pass vacuously on an empty list.
    """
    docs = _okf_docs()
    assert len(docs) >= MIN_DOC_COUNT, (
        f"OKF doc collector found only {len(docs)} docs "
        f"(expected ≥ {MIN_DOC_COUNT}). "
        f"Check REFERENCES_DIR={REFERENCES_DIR} and KNOWLEDGE_DIR={KNOWLEDGE_DIR}."
    )


# ---------------------------------------------------------------------------
# Parametrized: OKF frontmatter enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doc",
    _okf_docs(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_okf_frontmatter_present_and_valid(doc: Path) -> None:
    """Every OKF doc must carry valid frontmatter with required fields."""
    rel = str(doc.relative_to(REPO_ROOT))
    text = doc.read_text(encoding="utf-8")

    # --- presence check ---
    assert text.startswith("---"), f"{rel}: missing OKF frontmatter — file must start with '---\\n'"
    parts = text.split("---", 2)  # ['', '<yaml>', '<body>']
    assert len(parts) >= 3, f"{rel}: malformed OKF frontmatter — could not find closing '---'"

    # --- parse check ---
    fm = yaml.safe_load(parts[1])
    assert isinstance(fm, dict), f"{rel}: OKF frontmatter did not parse as a YAML mapping"

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
    assert "description" in fm, f"{rel}: OKF frontmatter missing required field 'description'"
    assert isinstance(fm["description"], str) and fm["description"].strip(), (
        f"{rel}: 'description' must be a non-empty string"
    )


@pytest.mark.parametrize(
    "doc",
    [
        p
        for p in _okf_docs()
        if yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1]).get("type") == "digest"
    ],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_digest_docs_carry_resource_field(doc: Path) -> None:
    """Docs with type=digest must carry a 'resource' field."""
    rel = str(doc.relative_to(REPO_ROOT))
    text = doc.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    assert "resource" in fm, f"{rel}: digest-typed doc is missing the required 'resource' field"
    assert isinstance(fm["resource"], str) and fm["resource"].strip(), (
        f"{rel}: 'resource' must be a non-empty string path"
    )

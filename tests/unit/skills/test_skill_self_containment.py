"""Reference-boundary tripwire for UACP skill instruction bodies.

Convention (skills/uacp-skills, "reference boundary — one-directional"): references
flow one way. A skill cites only the SKILL TREE (uacp-core/references + its own
references/); ``docs/`` is the authority/rationale/history layer that governs skills
but is never cited by them. (Not about dangling — a CC plugin install copies the
whole repo, docs/ included; the rule is boundary cleanliness / no divergence.)

This test enforces:
  1. No citation of the abolished top-level shared references dump (gone; shared refs
     live in ``uacp-core/references/``).
  2. No ``ADR-<number>`` citation in SKILL.md bodies — cite the concise
     ``uacp-core/references/`` digest, not a sprawling ADR. (*.py files may cite ADRs
     as provenance and are NOT scanned.)
  3. Anti-proliferation: every skills/uacp-core/references/*.md (except README.md) must
     be cited by ≥1 skills/*/SKILL.md.  An uncited reference doesn't belong in the
     skill tree; move to docs/ or delete.
  4. Index completeness: every skills/uacp-core/references/*.md (except README.md) must
     appear in the README.md index; the README must not list a file that doesn't exist.
  5. docs/ citation ban (rooted form): no skills/*/SKILL.md body may contain
     ``UACP_ROOT/docs/``.  Bare ``docs/`` prose mentions are still allowed (the
     convention/router skills legitimately describe docs/).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
REFERENCES_DIR = SKILLS_DIR / "uacp-core" / "references"
ADR_CITATION = re.compile(r"ADR-\d")
ROOTED_DOCS_CITATION = re.compile(r"UACP_ROOT/docs/")


def _skill_md_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("**/SKILL.md"))


def test_skills_dir_resolved() -> None:
    # Guard the path math: if this fails, REPO_ROOT/parents is wrong.
    assert SKILLS_DIR.is_dir(), f"skills dir not found at {SKILLS_DIR}"
    assert _skill_md_files(), "no SKILL.md files discovered"


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_md_body_cites_no_adr(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    offenders = [
        f"{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if ADR_CITATION.search(line)
    ]
    assert not offenders, (
        f"{skill_md.relative_to(REPO_ROOT)} cites an ADR in its instruction body "
        f"(cite skills/uacp-core/references/goal-driven-track.md instead). "
        f"Offending lines:\n" + "\n".join(offenders)
    )


# Slice 3: the top-level skills/references/ shared dump is ABOLISHED. Shared
# references live in uacp-core/references/; single-skill refs in that skill's own
# references/. No skill may cite the dead dump path again.
DUMP_LITERAL = "skills/references/"
DUMP_RELATIVE = re.compile(r"\.\./references/")


def _all_skill_md_text() -> list[Path]:
    return sorted(SKILLS_DIR.glob("**/*.md"))


@pytest.mark.parametrize("md", _all_skill_md_text(), ids=lambda p: str(p.relative_to(SKILLS_DIR)))
def test_no_citation_of_abolished_references_dump(md: Path) -> None:
    text = md.read_text(encoding="utf-8")
    offenders = [
        f"{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if DUMP_LITERAL in line
    ]
    assert not offenders, (
        f"{md.relative_to(REPO_ROOT)} cites the abolished skills/references/ dump "
        f"(shared refs live in uacp-core/references/; single-skill refs in the skill's "
        f"own references/). Offending lines:\n" + "\n".join(offenders)
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_md_no_dump_relative_pointer(skill_md: Path) -> None:
    # `../references/X` from a skills/<name>/SKILL.md resolves to the abolished
    # skills/references/ dump. The shared home is `../uacp-core/references/X`.
    text = skill_md.read_text(encoding="utf-8")
    offenders = [
        f"{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if DUMP_RELATIVE.search(line)
    ]
    assert not offenders, (
        f"{skill_md.relative_to(REPO_ROOT)} uses a `../references/` pointer to the "
        f"abolished dump; use `../uacp-core/references/` or this skill's own "
        f"`references/`. Offending lines:\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Reference-document policy (Slice-5)
# ---------------------------------------------------------------------------


def _reference_docs() -> list[Path]:
    """Return all *.md files in skills/uacp-core/references/ except README.md."""
    return sorted(
        p for p in REFERENCES_DIR.glob("*.md") if p.name != "README.md"
    )


@pytest.mark.parametrize("ref_doc", _reference_docs(), ids=lambda p: p.name)
def test_reference_doc_cited_by_at_least_one_skill(ref_doc: Path) -> None:
    """Every skills/uacp-core/references/*.md must be cited by ≥1 skills/*/SKILL.md.

    An uncited reference doesn't belong in the skill tree — move to docs/ or delete.
    """
    basename = ref_doc.name
    skill_mds = list(SKILLS_DIR.glob("*/SKILL.md"))
    cited = any(basename in skill_md.read_text(encoding="utf-8") for skill_md in skill_mds)
    assert cited, (
        f"skills/uacp-core/references/{basename} is not cited by any skill — "
        f"an uncited reference doesn't belong in the skill tree; move to docs/ or delete."
    )


def test_reference_index_complete() -> None:
    """Every skills/uacp-core/references/*.md (except README.md) must appear in README.md;
    README.md must not list a file that doesn't exist on disk.
    """
    readme_text = (REFERENCES_DIR / "README.md").read_text(encoding="utf-8")
    ref_files = {p.name for p in REFERENCES_DIR.glob("*.md") if p.name != "README.md"}

    missing_from_readme = sorted(f for f in ref_files if f not in readme_text)
    assert not missing_from_readme, (
        f"The following reference docs exist on disk but are missing from "
        f"skills/uacp-core/references/README.md index: {missing_from_readme}. "
        f"Add an entry for each."
    )

    # Find .md filenames referenced in README that do not exist on disk
    mentioned = set(re.findall(r"\b([\w-]+\.md)\b", readme_text))
    mentioned.discard("README.md")
    extra_in_readme = sorted(f for f in mentioned if f not in ref_files)
    assert not extra_in_readme, (
        f"The following filenames appear in skills/uacp-core/references/README.md "
        f"but do not exist on disk: {extra_in_readme}. Remove the stale entries."
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_md_no_rooted_docs_citation(skill_md: Path) -> None:
    """No skills/*/SKILL.md body may cite the rooted form UACP_ROOT/docs/.

    Bare 'docs/' prose mentions are still allowed (convention/router skills legitimately
    describe the docs layer).  Only the rooted path form that would be used as a
    navigable reference is banned.
    """
    text = skill_md.read_text(encoding="utf-8")
    offenders = [
        f"{i}: {line.strip()}"
        for i, line in enumerate(text.splitlines(), start=1)
        if ROOTED_DOCS_CITATION.search(line)
    ]
    assert not offenders, (
        f"{skill_md.relative_to(REPO_ROOT)} contains a rooted docs/ citation "
        f"(UACP_ROOT/docs/); cite a skills/uacp-core/references/ digest instead. "
        f"Offending lines:\n" + "\n".join(offenders)
    )

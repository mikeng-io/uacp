"""Self-containment tripwire for UACP skill instruction bodies (Step 1).

Convention (skills/uacp-skills): a SKILL.md body must reference only files that
ship with some skill. An installed coding agent receives the skill directory,
NOT the repo's docs/ tree, so an ADR citation in instruction prose dangles.

Scope (Step 1): forbid ``ADR-<number>`` citations in SKILL.md bodies. Source
files (*.py) may cite ADRs as origin-of-record provenance and are NOT scanned.
The broader docs/ self-containment sweep is Step 2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
ADR_CITATION = re.compile(r"ADR-\d")


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

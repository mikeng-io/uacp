"""Plugin-readiness lint: skills must be in the shape the Claude Code plugin
loader discovers and reads (ADR-0017 'Plugin packaging').

Step-1 scope: enforce the two things that affect LOADING — every skill is at
skills/<dir>/SKILL.md (no bare skills/SKILL.md; the loader skips it), and each
SKILL.md has a usable description.

Step-2 / Slice-4 scope: frontmatter conformance for one-level-deep skills —
valid kind classifier, no authority mirrors on lifecycle skills, no reserved-key
context misuse.

Step-2 / Slice-5 scope: reference-doc naming — filenames in
skills/uacp-core/references/ must be kebab-case with no date suffix.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
REFERENCES_DIR = SKILLS_DIR / "uacp-core" / "references"
DESCRIPTION_BUDGET = 1536

_KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
_DATE_SUFFIX_RE = re.compile(r"-\d{8}\.")

_VALID_KINDS = {"kernel", "lifecycle", "reference", "orchestration"}
_LIFECYCLE_AUTHORITY_KEYS = {"allowed_tools", "forbidden_tools", "phase_exit_invariants"}


def _skill_md_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("**/SKILL.md"))


def _one_level_skill_md_files() -> list[Path]:
    """Return SKILL.md files that are exactly skills/<dir>/SKILL.md (one level deep)."""
    return sorted(
        p for p in SKILLS_DIR.glob("*/SKILL.md") if len(p.relative_to(SKILLS_DIR).parts) == 2
    )


def _parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file (block between first two --- fences)."""
    text = skill_md.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def test_plugin_manifest_present() -> None:
    assert (REPO_ROOT / ".claude-plugin" / "plugin.json").is_file(), (
        "Claude Code plugin manifest missing (.claude-plugin/plugin.json)"
    )


def test_no_bare_skills_root_skill() -> None:
    # A SKILL.md directly under skills/ (not in a named subdir) is NOT discovered
    # by the CC plugin loader. Every skill must live in skills/<dir>/SKILL.md.
    assert not (SKILLS_DIR / "SKILL.md").exists(), (
        "skills/SKILL.md is not plugin-discoverable; move it into a named subdir "
        "(e.g. skills/uacp/SKILL.md)"
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_in_named_subdir(skill_md: Path) -> None:
    # SKILL.md must be exactly skills/<dir>/SKILL.md (one level under skills/).
    rel = skill_md.relative_to(SKILLS_DIR)
    assert len(rel.parts) == 2 and rel.parts[1] == "SKILL.md", (
        f"{skill_md.relative_to(REPO_ROOT)} is not at skills/<dir>/SKILL.md"
    )


@pytest.mark.parametrize("skill_md", _skill_md_files(), ids=lambda p: p.parent.name)
def test_description_present_and_within_budget(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{skill_md} missing YAML frontmatter"
    fm = text.split("---", 2)[1]
    assert "description:" in fm, f"{skill_md.relative_to(REPO_ROOT)} has no description"
    # crude length guard on the description block (multi-line allowed)
    for line in fm.splitlines():
        if line.strip().startswith("description:"):
            inline = line.split("description:", 1)[1].strip()
            if inline and len(inline) > DESCRIPTION_BUDGET:
                pytest.fail(
                    f"{skill_md.relative_to(REPO_ROOT)} description exceeds "
                    f"{DESCRIPTION_BUDGET} chars"
                )


# ---------------------------------------------------------------------------
# Frontmatter conformance checks (Slice-4 / Step-2)
# Applies to one-level-deep skills only: skills/<dir>/SKILL.md
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_md", _one_level_skill_md_files(), ids=lambda p: p.parent.name)
def test_skill_declares_valid_kind(skill_md: Path) -> None:
    """Every skill must declare a 'kind:' whose value is in the allowed set."""
    fm = _parse_frontmatter(skill_md)
    skill_name = skill_md.relative_to(REPO_ROOT)
    assert "kind" in fm, f"{skill_name}: frontmatter missing required 'kind' key"
    kind = fm["kind"]
    assert kind in _VALID_KINDS, (
        f"{skill_name}: 'kind: {kind}' is not a recognised classifier; "
        f"expected one of {sorted(_VALID_KINDS)}"
    )


@pytest.mark.parametrize("skill_md", _one_level_skill_md_files(), ids=lambda p: p.parent.name)
def test_lifecycle_skill_has_no_authority_mirrors(skill_md: Path) -> None:
    """Lifecycle skills must not carry allowed_tools, forbidden_tools, or
    phase_exit_invariants in their frontmatter — authority lives in codified grammar."""
    fm = _parse_frontmatter(skill_md)
    if fm.get("kind") != "lifecycle":
        return
    skill_name = skill_md.relative_to(REPO_ROOT)
    offending = sorted(_LIFECYCLE_AUTHORITY_KEYS & fm.keys())
    assert not offending, (
        f"{skill_name} (kind: lifecycle) must not carry authority-mirror keys "
        f"in frontmatter: {offending}. Move them to the codified grammar."
    )


@pytest.mark.parametrize("skill_md", _one_level_skill_md_files(), ids=lambda p: p.parent.name)
def test_no_reserved_key_context_misuse(skill_md: Path) -> None:
    """If 'context:' appears in frontmatter, its value must be 'fork'
    (the only meaning Claude Code recognises for this reserved key)."""
    fm = _parse_frontmatter(skill_md)
    if "context" not in fm:
        return
    skill_name = skill_md.relative_to(REPO_ROOT)
    value = fm["context"]
    assert value == "fork", (
        f"{skill_name}: reserved frontmatter key 'context' has disallowed value "
        f"'{value}'; only 'fork' is valid (Claude Code's fork-context semantic)."
    )


# ---------------------------------------------------------------------------
# Reference-doc naming (Slice-5)
# ---------------------------------------------------------------------------


def _reference_docs() -> list[Path]:
    """Return all *.md files in skills/uacp-core/references/ except README.md."""
    return sorted(
        p for p in REFERENCES_DIR.glob("*.md") if p.name != "README.md"
    )


@pytest.mark.parametrize("ref_doc", _reference_docs(), ids=lambda p: p.name)
def test_reference_doc_kebab_case_no_date_suffix(ref_doc: Path) -> None:
    """Reference doc filenames must be kebab-case with no -YYYYMMDD date suffix.

    Allowed:  agent-council-followthrough.md
    Rejected: Agent_Council.md, goal-driven-track-20240115.md
    README.md is excluded from this check.
    """
    name = ref_doc.name
    assert _KEBAB_CASE_RE.match(name), (
        f"skills/uacp-core/references/{name} has a non-kebab-case filename; "
        f"rename to lowercase-hyphenated form (e.g. my-reference.md)."
    )
    assert not _DATE_SUFFIX_RE.search(name), (
        f"skills/uacp-core/references/{name} has a -YYYYMMDD date suffix in the "
        f"filename; remove it (dates belong in the doc body, not the filename)."
    )

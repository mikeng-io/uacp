"""Plugin-readiness lint: skills must be in the shape the Claude Code plugin
loader discovers and reads (ADR-0017 'Plugin packaging').

Step-1 scope: enforce the two things that affect LOADING — every skill is at
skills/<dir>/SKILL.md (no bare skills/SKILL.md; the loader skips it), and each
SKILL.md has a usable description. Frontmatter reserved-key normalization is
enforced once the kind rollout lands (later frontmatter slice).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
DESCRIPTION_BUDGET = 1536


def _skill_md_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("**/SKILL.md"))


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

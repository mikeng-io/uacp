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

Slice-phase-hygiene scope: regression guards added after the phase-skill
hygiene pass —
  (a) lifecycle skills must carry 'phase' AND 'authority_source' in frontmatter;
  (b) no SKILL.md or references/*.md may reference the dead 'check-preflight'
      CLI sub-command (it does not exist in core.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"
# Vendored third-party skills are marked by a NOTICE file in their skill dir (a
# direct child of skills/, e.g. skills/code-review/NOTICE). They follow their own
# UPSTREAM convention (their LICENSE/NOTICE), NOT UACP's authored-skill convention
# (ADR-0017), so the authored-skill lints exempt them. They still install with the
# plugin (depth-2, auto-discovered) — exemption is from the *quality* lints only.
_VENDORED_SKILL_DIRS = [d for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "NOTICE").is_file()]


def _is_vendored(p: Path) -> bool:
    return any(d == p or d in p.parents for d in _VENDORED_SKILL_DIRS)


REFERENCES_DIR = SKILLS_DIR / "uacp-core" / "references"
DESCRIPTION_BUDGET = 1536

_KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
_DATE_SUFFIX_RE = re.compile(r"-\d{8}\.")

_VALID_KINDS = {"kernel", "lifecycle", "reference", "orchestration"}
_LIFECYCLE_AUTHORITY_KEYS = {"allowed_tools", "forbidden_tools", "phase_exit_invariants"}


def _skill_md_files() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.glob("**/SKILL.md") if not _is_vendored(p))


def _one_level_skill_md_files() -> list[Path]:
    """Return SKILL.md files that are exactly skills/<dir>/SKILL.md (one level deep),
    excluding vendored third-party skills (those whose dir carries a NOTICE — they
    follow their own upstream frontmatter convention, not UACP's kind/authority one)."""
    return sorted(
        p
        for p in SKILLS_DIR.glob("*/SKILL.md")
        if len(p.relative_to(SKILLS_DIR).parts) == 2 and not _is_vendored(p)
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
    return sorted(p for p in REFERENCES_DIR.glob("*.md") if p.name != "README.md")


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


# ---------------------------------------------------------------------------
# Phase-skill hygiene regression guards (Slice-phase-hygiene)
# ---------------------------------------------------------------------------


def _lifecycle_skill_md_files() -> list[Path]:
    """Return SKILL.md files whose frontmatter declares kind: lifecycle."""
    return sorted(
        p for p in SKILLS_DIR.glob("*/SKILL.md") if _parse_frontmatter(p).get("kind") == "lifecycle"
    )


@pytest.mark.parametrize("skill_md", _lifecycle_skill_md_files(), ids=lambda p: p.parent.name)
def test_lifecycle_skill_declares_phase(skill_md: Path) -> None:
    """Every lifecycle skill MUST declare a non-empty 'phase' key.

    The value may be a concrete phase name (e.g. 'triage') or '*' (the
    cross-phase state-mutator convention). The check guards against skills that
    drift from lifecycle kind without updating their frontmatter.
    """
    fm = _parse_frontmatter(skill_md)
    skill_name = skill_md.relative_to(REPO_ROOT)
    assert "phase" in fm, (
        f"{skill_name} (kind: lifecycle) is missing the required 'phase' key in "
        f"frontmatter. Add 'phase: <phase-name>' (or 'phase: \"*\"' for cross-phase)."
    )
    phase_val = fm["phase"]
    assert phase_val not in (None, ""), (
        f"{skill_name} (kind: lifecycle) has an empty 'phase' value; "
        f"set it to a concrete phase name or '*'."
    )


@pytest.mark.parametrize("skill_md", _lifecycle_skill_md_files(), ids=lambda p: p.parent.name)
def test_lifecycle_skill_declares_authority_source(skill_md: Path) -> None:
    """Every lifecycle skill MUST declare a non-empty 'authority_source' key.

    This guards against skills that name concrete phases but omit the pointer to
    the codified grammar that actually enforces them — the drift pattern seen in
    uacp-brainstorm before the hygiene pass.
    """
    fm = _parse_frontmatter(skill_md)
    skill_name = skill_md.relative_to(REPO_ROOT)
    assert "authority_source" in fm, (
        f"{skill_name} (kind: lifecycle) is missing the required 'authority_source' "
        f"key in frontmatter. Add a pointer to the codified grammar "
        f"(e.g. engines/domain/phase_graph.py)."
    )
    src_val = fm["authority_source"]
    assert src_val not in (None, ""), (
        f"{skill_name} (kind: lifecycle) has an empty 'authority_source' value; "
        f"point it at the codified grammar files."
    )


# ---------------------------------------------------------------------------
# Dead CLI guard: 'check-preflight' does not exist in core.py
# ---------------------------------------------------------------------------


def _all_skill_markdown_files() -> list[Path]:
    """Return every *.md under skills/ (SKILL.md files and references), EXCLUDING
    vendored third-party skills (those whose skill dir carries a NOTICE)."""
    return sorted(p for p in SKILLS_DIR.rglob("*.md") if not _is_vendored(p))


@pytest.mark.parametrize(
    "md_file", _all_skill_markdown_files(), ids=lambda p: str(p.relative_to(SKILLS_DIR))
)
def test_no_dead_check_preflight_cli(md_file: Path) -> None:
    """No skills markdown file may reference the dead 'check-preflight' CLI.

    The sub-command 'check-preflight' does not exist in
    skills/uacp-core/scripts/core.py. Any reference to it is stale and must be
    removed to prevent agents from invoking a non-existent tool.
    """
    text = md_file.read_text(encoding="utf-8")
    assert "check-preflight" not in text, (
        f"{md_file.relative_to(REPO_ROOT)} contains a reference to the dead "
        f"'check-preflight' CLI sub-command, which does not exist in core.py. "
        f"Remove or replace the reference."
    )

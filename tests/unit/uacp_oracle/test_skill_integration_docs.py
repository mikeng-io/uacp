"""Tests for Oracle integration hooks in lifecycle skill SKILL.md files."""
from __future__ import annotations

from pathlib import Path


UACP_ROOT = Path(__file__).resolve().parents[3]


def _read_skill(name: str) -> str:
    path = UACP_ROOT / "skills" / name / "SKILL.md"
    return path.read_text(encoding="utf-8")


def test_brainstorm_skill_has_oracle_advisory_section():
    content = _read_skill("uacp-brainstorm")
    assert "uacp_oracle_query" in content
    assert "advisory" in content.lower()
    assert "phase=brainstorm" in content


def test_triage_skill_has_oracle_advisory_section():
    content = _read_skill("uacp-triage")
    assert "uacp_oracle_query" in content
    assert "phase=triage" in content


def test_propose_skill_has_oracle_retrieval_section():
    content = _read_skill("uacp-propose")
    assert "uacp_oracle_query" in content
    assert "phase=propose" in content


def test_plan_skill_has_oracle_retrieval_section():
    content = _read_skill("uacp-plan")
    assert "uacp_oracle_query" in content
    assert "phase=plan" in content


def test_verify_skill_has_oracle_retrieval_section():
    content = _read_skill("uacp-verify")
    assert "uacp_oracle_query" in content
    assert "phase=verify" in content

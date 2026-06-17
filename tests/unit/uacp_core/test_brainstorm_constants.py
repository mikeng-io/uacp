"""Unit tests for brainstorm phase_transitions constants (T2)."""
from __future__ import annotations

import pytest
from engines.domain.phase_transitions import (
    STAGE_ALLOWED_TOOLS,
    STAGE_ENTERS_FROM,
    STAGE_FORBIDDEN_TOOLS,
    STAGE_PURPOSE,
    _PHASE_ORDER,
)


def test_brainstorm_first_in_phase_order() -> None:
    assert _PHASE_ORDER[0] == "brainstorm"


def test_brainstorm_allowed_tools_present() -> None:
    assert "brainstorm" in STAGE_ALLOWED_TOOLS
    tools = STAGE_ALLOWED_TOOLS["brainstorm"]
    # Must have the governed writers declared in the design doc.
    for required in ("uacp_state_write", "uacp_artifact_write", "uacp_heartgate_check"):
        assert required in tools, f"expected {required!r} in brainstorm allowed_tools"


def test_brainstorm_forbidden_tools_present() -> None:
    assert "brainstorm" in STAGE_FORBIDDEN_TOOLS
    # Exploratory phase; must forbid shell execution.
    assert "terminal" in STAGE_FORBIDDEN_TOOLS["brainstorm"]
    assert "execute_code" in STAGE_FORBIDDEN_TOOLS["brainstorm"]


def test_brainstorm_purpose_present() -> None:
    assert "brainstorm" in STAGE_PURPOSE
    assert STAGE_PURPOSE["brainstorm"]  # non-empty string


def test_brainstorm_enters_from_none() -> None:
    assert STAGE_ENTERS_FROM["brainstorm"] == ["none"]


def test_triage_enters_from_includes_brainstorm() -> None:
    assert set(STAGE_ENTERS_FROM["triage"]) == {"none", "brainstorm"}

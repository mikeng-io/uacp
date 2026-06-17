"""Tests for the uacp_oracle_query governed tool classification."""
from __future__ import annotations



def test_oracle_tool_is_classified_read_local():
    """uacp_oracle_query must be classified as read.local in uacp.toml."""
    from config import load_config
    cfg = load_config()
    guardian = cfg.model_extra.get("guardian", {})
    tool_classification = guardian.get("tool_classification", {})
    assert tool_classification.get("uacp_oracle_query") == "read.local"


def test_oracle_tool_not_in_self_attesting():
    """uacp_oracle_query must NOT be in self_attesting_tools (it is read-only)."""
    from config import load_config
    cfg = load_config()
    guardian = cfg.model_extra.get("guardian", {})
    sat = guardian.get("self_attesting_tools", {})
    names = sat.get("names", [])
    assert "uacp_oracle_query" not in names

"""Tests for the uacp_oracle_query governed tool classification."""
from __future__ import annotations



def test_oracle_tool_is_classified_external_network_read():
    """uacp_oracle_query must be classified as external.network_read in uacp.toml.

    The tool performs a NETWORK read via Honcho when enabled (MED-4), so it is
    classified external.network_read rather than read.local. Both categories are
    UNPROTECTED in core._is_protected, so the tool is still never blocked.
    """
    from config import load_config
    cfg = load_config()
    guardian = cfg.model_extra.get("guardian", {})
    tool_classification = guardian.get("tool_classification", {})
    assert tool_classification.get("uacp_oracle_query") == "external.network_read"


def test_oracle_tool_not_in_self_attesting():
    """uacp_oracle_query must NOT be in self_attesting_tools (it is read-only)."""
    from config import load_config
    cfg = load_config()
    guardian = cfg.model_extra.get("guardian", {})
    sat = guardian.get("self_attesting_tools", {})
    names = sat.get("names", [])
    assert "uacp_oracle_query" not in names

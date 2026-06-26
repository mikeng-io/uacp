"""Acceptance harness, Increment 0: the plugin-conformance prober (design node 13).

Runs the REAL conformance prober against this repo's plugin — it launches the MCP server exactly as
`plugin.json` configures it (`uv run … uacp_mcp_server.py`) and asserts the listed tool set equals
`tool_specs()`, plus the hooks/skills it ships are loadable. This is the deterministic core of the
E2E acceptance harness (no model, no container needed); the container wrapper drives the same prober
against a real `claude plugin install`.

Gated: needs the optional `mcp` SDK AND `uv` on PATH (the MCP launch prereq) — skips
otherwise so the core suite stays installable.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")
if shutil.which("uv") is None:
    pytest.skip("uv not on PATH (the plugin's MCP launch prereq)", allow_module_level=True)

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "acceptance"))
import conformance  # noqa: E402


def test_real_plugin_install_is_conformant():
    # the shipped plugin exposes every expected capability, actionable, through the real launch.
    res = conformance.run(REPO)
    failed = [c for c in res["capabilities"] if c["status"] != "pass"]
    assert res["pass"] is True, failed
    mcp = next(c for c in res["capabilities"] if c["kind"] == "mcp_tools")
    assert mcp["status"] == "pass" and mcp["evidence"]["tools"], "MCP probe listed no tools"
    # the MCP server really started and listed the 12 governed writers (not a vacuous pass).
    assert "uacp_entity_write" in mcp["evidence"]["tools"]


def test_probe_catches_a_missing_tool(monkeypatch):
    # NON-VACUITY: a governed tool EXPECTED but not listed by the server -> the MCP probe FAILs
    # (this is the council's #1 regression — "the plugin shipped zero MCP servers" — being caught).
    real = conformance._expected_tool_names
    monkeypatch.setattr(
        conformance, "_expected_tool_names", lambda root: real(root) | {"uacp_phantom_tool"}
    )
    res = conformance.probe_mcp(REPO)
    assert res.status == "fail" and "uacp_phantom_tool" in res.detail


def test_probe_catches_a_broken_skill(tmp_path):
    # NON-VACUITY for skills: a SKILL.md with no `name` is a packaging regression -> FAIL.
    fake = tmp_path / "skills" / "broken"
    fake.mkdir(parents=True)
    (fake / "SKILL.md").write_text("---\ndescription: no name here\n---\nbody\n")
    results = conformance.probe_skills(tmp_path)
    assert any(c.status == "fail" and c.name == "skill:broken" for c in results)

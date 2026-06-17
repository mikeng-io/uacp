"""Unit tests for uacp-core policy loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from core import GuardianPolicy, GuardianPolicyError


class TestGuardianPolicyLoad:
    """Tests for GuardianPolicy.load()"""

    def test_loads_valid_policy(self, temp_uacp_root: Path):
        policy = GuardianPolicy.load(temp_uacp_root)
        assert policy.version == "0.1"
        assert "state.uacp" in policy.protected_categories

    def test_load_reads_guardian_from_uacp_toml(self, tmp_path: Path):
        # With no per-project override, GuardianPolicy.load uses the repo-default
        # config/uacp.toml [guardian], which carries all 10 self-attesting tools.
        # This proves load sources from config.py (uacp.toml [guardian]) rather
        # than from the old 3/4-tool guardian-policy.yaml stub.
        policy = GuardianPolicy.load(tmp_path)
        assert len(policy.self_attesting_tools) == 10, policy.self_attesting_tools
        assert "uacp_doc_write" in policy.self_attesting_tools
        assert "uacp_contained_shell" in policy.self_attesting_tools
        # tool_classification-backed: the full policy classifies all 24 tools.
        assert len(policy.tool_classification) == 24, policy.tool_classification

    def test_override_mode_is_honored(self, tmp_path: Path):
        # Proves the live reader actually flows through config.py's deep-merge:
        # a `<root>/.uacp/config.toml` [guardian] override (mode = "observe")
        # wins over the repo-default `mode = "enforce"`, while the rest of the
        # full default policy (schema_version, the 10 self-attesting tools) is
        # preserved by the merge.
        (tmp_path / ".uacp").mkdir()
        (tmp_path / ".uacp" / "config.toml").write_text('[guardian]\nmode = "observe"\n')
        policy = GuardianPolicy.load(tmp_path)
        assert policy.mode == "observe"
        assert policy.version == "0.1"
        assert len(policy.self_attesting_tools) == 10

    def test_raises_when_guardian_table_missing(self, tmp_path: Path, monkeypatch):
        # The source is now config/uacp.toml [guardian] via config.py. If the
        # resolved config carries no (or a non-mapping) [guardian] table, load
        # MUST fail closed rather than construct an empty, no-op policy.
        import core

        class _NoGuardian:
            def model_dump(self):
                return {"paths": {}}  # no "guardian" key at all

        monkeypatch.setattr(core, "get_config", lambda _root: _NoGuardian())
        with pytest.raises(GuardianPolicyError, match="missing or invalid"):
            GuardianPolicy.load(tmp_path)

    def test_raises_on_malformed_guardian_table(self, tmp_path: Path, monkeypatch):
        # A non-mapping [guardian] value (e.g. a list) must fail closed.
        import core

        class _BadGuardian:
            def model_dump(self):
                return {"guardian": [1, 2, 3]}

        monkeypatch.setattr(core, "get_config", lambda _root: _BadGuardian())
        with pytest.raises(GuardianPolicyError, match="missing or invalid"):
            GuardianPolicy.load(tmp_path)


class TestGuardianPolicyValidate:
    """Tests for GuardianPolicy.validate()

    These exercise the anti-bypass invariants in ``validate()`` directly against
    crafted policy dicts. ``validate()`` is the same method that now guards the
    TOML-sourced ``[guardian]`` policy produced by ``GuardianPolicy.load``, so
    these checks remain the authoritative rejection contract for that policy.
    """

    def test_valid_policy_passes(self, temp_uacp_root: Path):
        policy = GuardianPolicy.load(temp_uacp_root)
        policy.validate()  # should not raise

    def test_rejects_missing_schema_version(self, tmp_path: Path):
        policy = GuardianPolicy(
            {
                "protected_categories": {"state.uacp": {}},
                "tool_classification": {"uacp_state_write": "state.uacp"},
            },
            uacp_root=tmp_path,
        )
        with pytest.raises(GuardianPolicyError, match="schema_version"):
            policy.validate()

    def test_rejects_missing_protected_categories(self, tmp_path: Path):
        policy = GuardianPolicy(
            {
                "schema_version": "0.1",
                "tool_classification": {"uacp_state_write": "state.uacp"},
            },
            uacp_root=tmp_path,
        )
        with pytest.raises(GuardianPolicyError, match="protected_categories"):
            policy.validate()

    def test_rejects_self_attesting_tool_not_in_classification(self, tmp_path: Path):
        # Anti-bypass invariant (skeptic F2): a self-attesting tool MUST appear
        # in tool_classification. A policy that lists one that does not is
        # rejected — this is the containment-bypass guard.
        policy = GuardianPolicy(
            {
                "schema_version": "0.1",
                "protected_categories": {"state.uacp": {}},
                "tool_classification": {"uacp_state_write": "state.uacp"},
                "self_attesting_tools": {"names": ["terminal"]},
            },
            uacp_root=tmp_path,
        )
        with pytest.raises(GuardianPolicyError, match="not in tool_classification"):
            policy.validate()

    def test_rejects_self_attesting_tool_targeting_nongoverned_category(self, tmp_path: Path):
        # Anti-bypass invariant: a self-attesting tool classified into a
        # non-governed category is rejected.
        policy = GuardianPolicy(
            {
                "schema_version": "0.1",
                "protected_categories": {"file.write": {}},
                "tool_classification": {"sneaky": "file.write"},
                "self_attesting_tools": {"names": ["sneaky"]},
            },
            uacp_root=tmp_path,
        )
        with pytest.raises(GuardianPolicyError, match="non-governed category"):
            policy.validate()

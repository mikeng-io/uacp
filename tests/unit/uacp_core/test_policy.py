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

    def test_raises_on_missing_policy(self, temp_uacp_root: Path):
        (temp_uacp_root / "config" / "guardian-policy.yaml").unlink()
        with pytest.raises(GuardianPolicyError, match="not found"):
            GuardianPolicy.load(temp_uacp_root)

    def test_raises_on_malformed_policy(self, temp_uacp_root: Path):
        policy_path = temp_uacp_root / "config" / "guardian-policy.yaml"
        policy_path.write_text("not_a_dict: [1, 2, 3\n")  # malformed YAML
        with pytest.raises(GuardianPolicyError):
            GuardianPolicy.load(temp_uacp_root)


class TestGuardianPolicyValidate:
    """Tests for GuardianPolicy.validate()"""

    def test_valid_policy_passes(self, temp_uacp_root: Path):
        policy = GuardianPolicy.load(temp_uacp_root)
        policy.validate()  # should not raise

    def test_rejects_missing_schema_version(self, temp_uacp_root: Path):
        policy_path = temp_uacp_root / "config" / "guardian-policy.yaml"
        policy_path.write_text("""
protected_categories:
  state.uacp: {}
tool_classification:
  uacp_state_write: state.uacp
""")
        with pytest.raises(GuardianPolicyError, match="schema_version"):
            GuardianPolicy.load(temp_uacp_root)

    def test_rejects_missing_protected_categories(self, temp_uacp_root: Path):
        policy_path = temp_uacp_root / "config" / "guardian-policy.yaml"
        policy_path.write_text("""
schema_version: "0.1"
tool_classification:
  uacp_state_write: state.uacp
""")
        with pytest.raises(GuardianPolicyError, match="protected_categories"):
            GuardianPolicy.load(temp_uacp_root)

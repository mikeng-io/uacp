"""Defensive-robustness regression tests for the Guardian (adversarial-review
findings on the Phase-A1 type-safety hardening).

The Guardian's config table is `cast` to a TypedDict, not validated, so the
runtime value may not match the declared shape. The pre-typing code coerced
malformed values defensively; the typed rewrite must preserve that. Each test
below FAILS (crash or flipped decision) if the corresponding defensive coercion
is dropped — i.e. they are non-vacuous guards for a specific regression.
"""

from __future__ import annotations

from pathlib import Path

from core import DECISION_BLOCK, Guardian, GuardianEvent, GuardianPolicy, make_event


def _policy(data: dict[str, object], tmp_path: Path) -> GuardianPolicy:
    # Construct directly (bypassing load()) to inject a malformed table.
    return GuardianPolicy(data, uacp_root=tmp_path)


def test_category_defaults_normalizes_a_non_dict_value(tmp_path: Path):
    # A category whose value is a list (malformed — should be a table) must
    # normalize to {}, not be returned as-is (which crashed is_allowed_* with
    # AttributeError before the isinstance(dict) fallback was restored).
    pol = _policy(
        {"schema_version": "1", "protected_categories": {"state.uacp": ["uacp_state_write"]}},
        tmp_path,
    )
    assert pol.category_defaults("state.uacp") == {}
    assert pol.is_allowed_tool_for_category("state.uacp", "uacp_state_write") is False


def test_phase_layer_scalar_allowed_tools_is_not_substring_matched(tmp_path: Path):
    # A stage whose allowed_tools is a malformed SCALAR string must be coerced
    # to a list (of chars) so a tool name that is a *substring* of it is NOT
    # admitted. Without the list() coercion, `"state" in "uacp_state_write"` is
    # a substring hit that silently passes the allowlist — a block->allow flip.
    pol = _policy({"schema_version": "1", "protected_categories": {"file.write": {}}}, tmp_path)
    guardian = Guardian(pol, phase_config={"stages": {"execute": {"allowed_tools": "uacp_state_write"}}})
    event = make_event(tool_name="state", args={"uacp_phase": "execute"})
    decision = guardian._phase_layer_check(event, "file.write", [])
    assert decision is not None
    assert decision.decision == DECISION_BLOCK
    assert "allowed_tools" in decision.reason


def test_extract_paths_tolerates_explicit_none_tool_args(tmp_path: Path):
    # tool_args is typed non-None but an explicit GuardianEvent(tool_args=None)
    # bypasses the dataclass default_factory; _extract_paths must not crash.
    pol = _policy({"schema_version": "1", "protected_categories": {}}, tmp_path)
    guardian = Guardian(pol)
    event = GuardianEvent(
        runtime="",
        adapter="",
        event_type="",
        tool_provider="core",
        tool_name="x",
        tool_args=None,  # type: ignore[arg-type]
    )
    assert guardian._extract_paths(event) == []


def test_is_allowed_tool_for_category_tolerates_falsy_non_list(tmp_path: Path):
    # A malformed falsy non-list allowed_tools (e.g. 0) must degrade to "not
    # allowed", not crash `in` with TypeError (the `or []` defensive coercion).
    pol = _policy(
        {"schema_version": "1", "protected_categories": {"state.uacp": {"allowed_tools": 0}}},
        tmp_path,
    )
    assert pol.is_allowed_tool_for_category("state.uacp", "uacp_state_write") is False

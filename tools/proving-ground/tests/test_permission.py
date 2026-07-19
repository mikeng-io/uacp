"""Permission auto-reply shape -- mirrors OpenAB's connection.rs unit tests (the mined source)."""

from __future__ import annotations

from acp_client import build_permission_response, pick_best_option


def test_picks_allow_always_over_other_options():
    options = [
        {"kind": "allow_once", "optionId": "once"},
        {"kind": "allow_always", "optionId": "always"},
        {"kind": "reject_once", "optionId": "reject"},
    ]
    assert pick_best_option(options) == "always"


def test_falls_back_to_first_unknown_non_reject_kind():
    options = [
        {"kind": "reject_once", "optionId": "reject"},
        {"kind": "workspace_write", "optionId": "workspace-write"},
    ]
    assert pick_best_option(options) == "workspace-write"


def test_returns_none_when_only_reject_options_exist():
    options = [
        {"kind": "reject_once", "optionId": "reject-once"},
        {"kind": "reject_always", "optionId": "reject-always"},
    ]
    assert pick_best_option(options) is None


def test_builds_cancelled_outcome_when_no_selectable_option_exists():
    response = build_permission_response({"options": [{"kind": "reject_once", "optionId": "r"}]})
    assert response == {"outcome": {"outcome": "cancelled"}}


def test_default_allow_always_when_no_options_present():
    response = build_permission_response(None)
    assert response == {"outcome": {"outcome": "selected", "optionId": "allow_always"}}
    response2 = build_permission_response({})
    assert response2 == {"outcome": {"outcome": "selected", "optionId": "allow_always"}}


def test_selects_allow_option_id():
    response = build_permission_response(
        {
            "options": [
                {"kind": "reject_once", "optionId": "no"},
                {"kind": "allow_always", "optionId": "yes"},
            ]
        }
    )
    assert response == {"outcome": {"outcome": "selected", "optionId": "yes"}}

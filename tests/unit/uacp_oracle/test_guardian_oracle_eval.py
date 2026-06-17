"""Kernel-level Guardian evaluation regression for uacp_oracle_query.

Behavioral guard: constructs the real Guardian from the production policy
(config/uacp.toml [guardian]) and the production phase-config
(config/phase-transitions.yaml with codified stages injected by the loader),
then asserts that a uacp_oracle_query tool-call event is NOT BLOCKED (verdict
allow / allow_with_audit) for each of the three read-heavy phases: propose, plan,
verify.  The tool is classified external.network_read (MED-4: it performs a
network read via Honcho when enabled); like read.local it is unprotected, so the
verdict is non-blocking (allow_with_audit, since a network read is audited).

The mutation assertion (documented below) confirmed that removing
uacp_oracle_query from [guardian.tool_classification] in uacp.toml causes
these tests to FAIL: the tool falls through to external.unknown_mutator
(a protected, block-by-default category), and the decision becomes BLOCK.
Restoring the entry restores ALLOW.  This file IS the regression guard.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core import (
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    DECISION_BLOCK,
    Guardian,
    GuardianEvent,
    GuardianPolicy,
)
from engines.io import load_phase_transitions

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_oracle_event(phase: str) -> GuardianEvent:
    """Build a minimal but realistic uacp_oracle_query event for a given phase."""
    return GuardianEvent(
        runtime="test",
        adapter="unit",
        event_type="pre_tool_call",
        tool_provider="core",
        tool_name="uacp_oracle_query",
        tool_args={},
        uacp_run_id="uacp-oracle-reg-001",
        uacp_phase=phase,
        workspace=str(REPO_ROOT),
        policy_version="0.1",
        declared_authority="plans/oracle-reg.yaml",
        declared_side_effects=[],
        filesystem_guard_verified=True,
    )


def _build_guardian() -> Guardian:
    """Construct a Guardian from real production policy + real phase config."""
    policy = GuardianPolicy.load(str(REPO_ROOT))
    phase_config = load_phase_transitions(REPO_ROOT).value
    return Guardian(policy, phase_config=phase_config)


@pytest.mark.parametrize("phase", ["propose", "plan", "verify"])
def test_oracle_query_allowed_in_read_phases(phase: str) -> None:
    """Guardian Layer-B must NOT block uacp_oracle_query in propose/plan/verify.

    uacp_oracle_query is classified as external.network_read (MED-4: it performs a
    network read via Honcho when enabled) — a non-protected category, exactly like
    read.local (core._is_protected treats both as unprotected).  Layer-B's
    allowlist guard only restricts protected categories, so this tool must always
    pass regardless of the phase allowlist.  This test locks that invariant
    against config regressions.
    """
    guardian = _build_guardian()
    decision = guardian.evaluate(_make_oracle_event(phase))
    assert not decision.blocks_execution, (
        f"Guardian unexpectedly blocked uacp_oracle_query in phase '{phase}': "
        f"decision={decision.decision!r}, reason={decision.reason!r}, "
        f"category={decision.category!r}, evidence={decision.evidence}"
    )
    # external.network_read is unprotected, so the verdict is non-blocking; the
    # category's default_decision is allow_with_audit (a network read is audited),
    # which is still a "may proceed" verdict (MED-4).
    assert decision.decision in {DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT}, (
        f"Expected a non-blocking verdict for uacp_oracle_query in '{phase}', "
        f"got {decision.decision!r}"
    )


def test_oracle_query_allowed_decision_depends_on_classification(monkeypatch) -> None:
    """Mutation guard: removing uacp_oracle_query from tool_classification causes BLOCK.

    This confirms the test above is a genuine regression guard, not a vacuous
    pass.  When the classification is absent, the tool falls through to
    external.unknown_mutator — a protected, block-by-default category.

    core.py does ``from config import get_config``, creating a module-level
    binding.  We must patch BOTH ``config.get_config`` AND ``core.get_config``
    to ensure GuardianPolicy.load (which calls the name bound in core) sees the
    mutated version.
    """
    import config as config_module
    import core as core_module

    original_get_config = config_module.get_config

    def _patched_get_config(root=None):
        cfg = original_get_config(root)
        raw = cfg.model_dump()
        guardian_raw = dict(raw.get("guardian", {}))
        tool_cls = dict(guardian_raw.get("tool_classification", {}))
        # Remove the oracle classification — this is the mutation.
        tool_cls.pop("uacp_oracle_query", None)
        guardian_raw["tool_classification"] = tool_cls
        raw["guardian"] = guardian_raw
        return _MutatedConfig(raw)

    monkeypatch.setattr(config_module, "get_config", _patched_get_config)
    monkeypatch.setattr(core_module, "get_config", _patched_get_config)

    # GuardianPolicy.load calls core.get_config; with both patches active the
    # oracle classification is absent and load() sees the mutated policy.
    policy = GuardianPolicy.load(str(REPO_ROOT))
    phase_config = load_phase_transitions(REPO_ROOT).value
    guardian = Guardian(policy, phase_config=phase_config)

    decision = guardian.evaluate(_make_oracle_event("propose"))
    # Without the classification the tool lands in external.unknown_mutator
    # which has default_decision=block — this must be a blocking decision.
    assert decision.blocks_execution, (
        "Expected BLOCK when uacp_oracle_query is absent from tool_classification, "
        f"but got {decision.decision!r} (category={decision.category!r})"
    )
    assert decision.decision == DECISION_BLOCK, decision


class _MutatedConfig:
    """Minimal stand-in for the config object that exposes model_dump()."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    def model_dump(self) -> dict:
        return dict(self._raw)

    @property
    def model_extra(self) -> dict:
        return dict(self._raw)

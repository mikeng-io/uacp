"""Fake-agent driver: issues governed tool calls through the real Guardian + handlers.

Every tool call is evaluated by the REAL Guardian before its handler runs. A
non-allow decision raises AssertionError — that assertion IS the false-block
detector (failure-mode F1): if Guardian ever blocks a legitimate governed call,
the E2E lifecycle test fails loudly rather than silently degrading.

`handler` is any callable taking the args dict and returning a JSON string
(e.g. ``state._handle_uacp_gate_ledger_append``, ``state_machine.handle_init``).
"""

from __future__ import annotations

import json
from pathlib import Path

from core import (
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    Guardian,
    GuardianEvent,
    GuardianPolicy,
)

# Guardian decisions that mean "the call may proceed". Anything else is a block
# (or an approval gate) and must fail the harness when issued for a legit call.
_ALLOW = {DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT}


def make_event(
    tool_name: str,
    tool_args: dict,
    *,
    run_id: str,
    phase: str,
    root: Path,
) -> GuardianEvent:
    """Build a GuardianEvent for a governed tool call from the fake agent."""
    return GuardianEvent(
        runtime="test",
        adapter="e2e",
        event_type="tool_call",
        tool_provider="core",
        tool_name=tool_name,
        tool_args=tool_args,
        uacp_run_id=run_id,
        uacp_phase=phase,
        workspace=str(root),
        policy_version="0.1",
        declared_authority="plans/test.yaml",
        declared_side_effects=[],
    )


class Driver:
    """Drives governed tool calls; asserts Guardian never false-blocks a legit call."""

    def __init__(self, root: Path, run_id: str):
        self.root = root
        self.run_id = run_id
        self.guardian = Guardian(GuardianPolicy.load(str(root)))

    def call(self, tool_name: str, handler, args: dict, *, phase: str) -> dict:
        """Evaluate ``tool_name`` via the real Guardian, then run ``handler(args)``.

        Raises AssertionError if Guardian returns a non-allow decision (F1
        false-block detector). Returns the handler's JSON output parsed to a dict.
        """
        event = make_event(tool_name, args, run_id=self.run_id, phase=phase, root=self.root)
        decision = self.guardian.evaluate(event)
        assert decision.decision in _ALLOW, (
            f"Guardian FALSE-BLOCKED legit call {tool_name} in {phase}: "
            f"{decision.decision} / {getattr(decision, 'blockers', None)}"
        )
        return json.loads(handler(args))

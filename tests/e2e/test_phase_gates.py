"""E2E: per-phase Guardian Layer-B tool-allowlist matrix.

GOAL
----
Prove that Guardian's per-phase "Layer-B" tool admissibility actually
ENFORCES the per-phase tool envelope (``allowed_tools`` / ``forbidden_tools``)
declared in the PRODUCTION ``config/phase-transitions.yaml`` — not a synthetic
fixture. For each (phase, tool) cell, assert that a tool the config ALLOWS in
that phase is admitted, and a tool the config FORBIDS or omits from the
allowlist is blocked with a reason — and that nothing raises.

LAYER-B ACTIVATION (the crux)
-----------------------------
``Guardian.__init__(policy, *, phase_config=None)``. When ``phase_config`` is
None there is NO per-phase restriction — only Layer-A category checks run
(``core.py`` ``Guardian.evaluate`` falls straight through ``_phase_layer_check``
which returns None on empty ``stages``). The existing ``tests/e2e/driver.py``
constructs ``Guardian(policy)`` WITHOUT ``phase_config``, so it does NOT enforce
per-phase allowlists. This test deliberately constructs Guardian WITH
``phase_config={"stages": <real stages mapping>}`` so Layer-B is live, and keeps
a second control Guardian WITHOUT ``phase_config`` to PROVE that the block on an
allowlist-miss cell comes from Layer-B alone (control admits; Layer-B blocks).

See ``core.py`` ``Guardian._phase_layer_check`` (skills/uacp-core/scripts):
  * ``tool_name in forbidden_tools``          -> block  (any category)
  * ``allowed_tools`` set, miss, protected cat -> block  (allowlist miss)
  * read.local / external.network_read         -> pass   (reads never gated)
  * unknown phase (stages populated)           -> block

EXPECTATIONS ARE DERIVED FROM THE CONFIG, not hardcoded: the parametrize lists
are built by reading the real ``stages`` mapping at import time, then asserting
the kernel agrees. This tests ENFORCEMENT of the declared envelope.

BUG-SHAKING / FAILURE POLICY
----------------------------
Assertions encode CORRECT behavior. No kernel code is patched and no assertion
is weakened to make a cell pass. A genuine Layer-B enforcement bug would be
marked ``pytest.mark.xfail`` with a precise reason (none were needed — see the
task report). Kernel fixes are Task 4c.

A NOTE ON ``terminal`` / ``execute_code``
-----------------------------------------
These raw-exec tools classify as ``exec.shell`` / ``exec.code_with_tool_proxy``,
whose Layer-A default for a UACP-bound call is a hard / heartgate block. They
are FORBIDDEN in every phase except ``execute``, and even in ``execute`` (where
the config allowlists them) Layer-A still blocks them — they are reachable only
via the governed ``uacp_contained_shell`` surface. That Layer-A behavior is out
of scope here. So this matrix:
  * EXCLUDES raw-exec tools from the "admitted" expectations (the config
    allowlisting them in ``execute`` does not mean Layer-A admits them), and
  * For the FORBIDDEN cells, asserts the block carries the Layer-B signature
    (``phase_layer=forbidden`` evidence tag) so we know Layer-B fired first.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from core import (
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    DECISION_BLOCK,
    Guardian,
    GuardianEvent,
    GuardianPolicy,
)

# --------------------------------------------------------------------------
# Load the REAL production policy + phase-transitions config (not the temp
# fixture, whose stages are identical across phases and therefore cannot show
# per-phase differentiation). Resolved relative to the repo root.
# --------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_TRANSITIONS_PATH = REPO_ROOT / "config" / "phase-transitions.yaml"

_PHASE_CONFIG = yaml.safe_load(PHASE_TRANSITIONS_PATH.read_text())
_STAGES: dict = _PHASE_CONFIG.get("stages") or {}

# Raw-exec tools: Layer-A blocks these regardless of phase allowlisting, so
# they are not valid "admitted" expectations (see module docstring).
_RAW_EXEC = {"terminal", "execute_code"}

_ALLOW = {DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT}


def _make_event(tool_name: str, phase: str) -> GuardianEvent:
    """A fully-contexted governed tool-call event for ``tool_name`` in ``phase``.

    ``filesystem_guard_verified=True`` removes the Layer-A write-containment
    block so that, for the ADMITTED cells, the ONLY thing that could block a
    governed writer is Layer-B (which must not, since the tool is allowlisted).
    """
    return GuardianEvent(
        runtime="test",
        adapter="e2e",
        event_type="tool_call",
        tool_provider="core",
        tool_name=tool_name,
        tool_args={},
        uacp_run_id="uacp-phasegate-001",
        uacp_phase=phase,
        workspace=str(REPO_ROOT),
        policy_version="0.1",
        declared_authority="plans/test.yaml",
        declared_side_effects=[],
        filesystem_guard_verified=True,
    )


@pytest.fixture(scope="module")
def policy() -> GuardianPolicy:
    return GuardianPolicy.load(str(REPO_ROOT))


@pytest.fixture(scope="module")
def guardian_layer_b(policy: GuardianPolicy) -> Guardian:
    """Guardian WITH phase_config => Layer-B ACTIVE."""
    return Guardian(policy, phase_config={"stages": _STAGES})


@pytest.fixture(scope="module")
def guardian_no_layer_b(policy: GuardianPolicy) -> Guardian:
    """Control Guardian WITHOUT phase_config => Layer-B OFF (Layer-A only).

    Used to prove allowlist-miss blocks originate in Layer-B: this control
    admits the same cell that ``guardian_layer_b`` blocks.
    """
    return Guardian(policy)


# --------------------------------------------------------------------------
# Matrix derivation from the real config.
# --------------------------------------------------------------------------
def _allowed(phase: str) -> set[str]:
    return set((_STAGES.get(phase) or {}).get("allowed_tools") or [])


def _forbidden(phase: str) -> set[str]:
    return set((_STAGES.get(phase) or {}).get("forbidden_tools") or [])


# Union of every governed writer that is allowlisted in at least one phase,
# minus raw-exec. Used to derive allowlist-MISS cells per phase.
_ALL_ALLOWED_WRITERS: set[str] = set()
for _st in _STAGES.values():
    if isinstance(_st, dict):
        _ALL_ALLOWED_WRITERS |= set(_st.get("allowed_tools") or [])
_ALL_ALLOWED_WRITERS -= _RAW_EXEC

# Cell lists, derived from config:
_ADMIT_CELLS = [(phase, tool) for phase in _STAGES for tool in sorted(_allowed(phase) - _RAW_EXEC)]

_FORBIDDEN_CELLS = [(phase, tool) for phase in _STAGES for tool in sorted(_forbidden(phase))]

# Allowlist-miss: a governed writer that IS allowlisted somewhere but is
# neither in this phase's allowed_tools nor its forbidden_tools.
_ALLOWLIST_MISS_CELLS = [
    (phase, tool)
    for phase in _STAGES
    for tool in sorted(_ALL_ALLOWED_WRITERS)
    if tool not in _allowed(phase) and tool not in _forbidden(phase)
]


def _cell_id(cell: tuple[str, str]) -> str:
    return f"{cell[0]}-{cell[1]}"


# Sanity: the config must actually differentiate tools per phase, otherwise the
# matrix proves nothing. (The temp fixture would fail this — it is uniform.)
def test_config_is_differentiated():
    assert _STAGES, "real phase-transitions.yaml has no stages"
    assert _ADMIT_CELLS, "no admitted cells derived"
    assert _FORBIDDEN_CELLS, "config declares no forbidden_tools anywhere"
    assert _ALLOWLIST_MISS_CELLS, "config does not differentiate allowlists per phase"


# --------------------------------------------------------------------------
# 1. ADMITTED: every allowlisted governed writer (minus raw-exec) is admitted.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("phase,tool", _ADMIT_CELLS, ids=[_cell_id(c) for c in _ADMIT_CELLS])
def test_allowed_tool_is_admitted(guardian_layer_b: Guardian, phase: str, tool: str):
    decision = guardian_layer_b.evaluate(_make_event(tool, phase))
    assert decision.decision in _ALLOW, (
        f"Layer-B FALSE-BLOCKED allowlisted tool {tool!r} in phase {phase!r}: "
        f"{decision.decision} / {decision.reason} / {decision.evidence}"
    )


# --------------------------------------------------------------------------
# 2. FORBIDDEN: every forbidden tool is blocked, and the block is Layer-B's.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phase,tool", _FORBIDDEN_CELLS, ids=[_cell_id(c) for c in _FORBIDDEN_CELLS]
)
def test_forbidden_tool_is_blocked_by_layer_b(guardian_layer_b: Guardian, phase: str, tool: str):
    decision = guardian_layer_b.evaluate(_make_event(tool, phase))
    assert decision.decision == DECISION_BLOCK, (
        f"forbidden tool {tool!r} in phase {phase!r} was not blocked: "
        f"{decision.decision} / {decision.reason}"
    )
    # Prove Layer-B is the layer that blocked (these raw-exec tools would also
    # be blocked by Layer-A, so we pin the Layer-B signature explicitly).
    assert "phase_layer=forbidden" in decision.evidence, (
        f"expected Layer-B forbidden signature in evidence for {tool!r}/{phase!r}, "
        f"got reason={decision.reason!r} evidence={decision.evidence}"
    )
    assert f"forbidden in phase '{phase}'" in decision.reason


# --------------------------------------------------------------------------
# 3. ALLOWLIST-MISS: a governed writer not in this phase's allowlist is blocked
#    by Layer-B ONLY. Proven by the control Guardian (Layer-B off) ADMITTING
#    the same cell. This is the cleanest possible proof that Layer-B enforces.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "phase,tool", _ALLOWLIST_MISS_CELLS, ids=[_cell_id(c) for c in _ALLOWLIST_MISS_CELLS]
)
def test_allowlist_miss_is_blocked_only_by_layer_b(
    guardian_layer_b: Guardian, guardian_no_layer_b: Guardian, phase: str, tool: str
):
    event = _make_event(tool, phase)

    with_layer_b = guardian_layer_b.evaluate(event)
    assert with_layer_b.decision == DECISION_BLOCK, (
        f"allowlist-miss {tool!r} in {phase!r} should be Layer-B blocked, "
        f"got {with_layer_b.decision} / {with_layer_b.reason}"
    )
    assert "phase_layer=allowlist_miss" in with_layer_b.evidence, (
        f"expected allowlist_miss signature, got evidence={with_layer_b.evidence}"
    )
    assert "not in phase" in with_layer_b.reason and "allowed_tools" in with_layer_b.reason

    # Control: WITHOUT phase_config the SAME call is admitted => the block above
    # is attributable to Layer-B and nothing else.
    without_layer_b = guardian_no_layer_b.evaluate(event)
    assert without_layer_b.decision in _ALLOW, (
        f"control (Layer-B OFF) should admit governed writer {tool!r} in {phase!r}, "
        f"got {without_layer_b.decision} / {without_layer_b.reason} — if this blocks, the "
        f"allowlist-miss block is NOT cleanly attributable to Layer-B"
    )


# --------------------------------------------------------------------------
# 4. EXIT-INVARIANT / robustness extras (kept tight, not over-scoped):
#    - an unknown phase value is rejected when stages are populated;
#    - Layer-B never raises across the full cell space (matrix already covers
#      this implicitly, but assert the no-raise contract explicitly here).
# --------------------------------------------------------------------------
def test_unknown_phase_is_blocked(guardian_layer_b: Guardian):
    decision = guardian_layer_b.evaluate(_make_event("uacp_state_write", "execute_v2"))
    assert decision.decision == DECISION_BLOCK
    assert "unknown uacp_phase" in decision.reason
    assert "phase_layer=unknown_phase" in decision.evidence


def test_layer_b_never_raises_over_full_matrix(guardian_layer_b: Guardian):
    """Every declared (phase, declared-tool) combination evaluates cleanly."""
    for phase in _STAGES:
        for tool in sorted(_allowed(phase) | _forbidden(phase)):
            decision = guardian_layer_b.evaluate(_make_event(tool, phase))
            assert decision.decision  # non-empty decision string, no exception

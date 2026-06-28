# Guardian Layer-B governance for the run-lifecycle tools.
#
# Regression coverage for the gap that let the run-lifecycle tools ship
# un-governed: uacp_run_init / uacp_run_transition / uacp_run_register_artifact
# / uacp_run_finalize were registered in tool_specs but were NOT classified as
# state.uacp, NOT in any phase allowlist, and NOT self-attesting. In the
# governed Hermes path that meant they either fell through to
# external.unknown_mutator (ungoverned allow) or were blocked — never governed
# as the state writers they are.
#
# These tests exercise the REAL Guardian.evaluate decision surface (Layer B +
# Layer A), not the bare handlers, so they would have caught the miss. They
# build phase_config from stages_default() — the production code default that
# the loader injects whenever config/phase-transitions.yaml omits a `stages`
# block (which the real repo config does). The temp_uacp_root fixture writes
# its own slim stages block, so it is intentionally NOT used as the phase
# source here.
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Guardian, GuardianPolicy, make_event  # noqa: E402
from engines.domain.phase_transitions import stages_default  # noqa: E402

RUN_TOOLS = (
    "uacp_run_init",
    "uacp_run_transition",
    "uacp_run_register_artifact",
    "uacp_run_finalize",
)

# Phases where each tool MUST be admitted by Layer B.
ALLOWED = {
    "uacp_run_init": ("brainstorm", "triage"),
    "uacp_run_transition": (
        "brainstorm",
        "triage",
        "propose",
        "plan",
        "execute",
        "verify",
        "resolve",
    ),
    "uacp_run_register_artifact": (
        "brainstorm",
        "triage",
        "propose",
        "plan",
        "execute",
        "verify",
        "resolve",
    ),
    "uacp_run_finalize": ("resolve",),
}

# Phases where each tool MUST be blocked by Layer B (allowlist miss). finalize
# is deliberately excluded from verify (handle_finalize refuses a non-terminal
# manifest) and init from execute (a run is created at entry, not mid-run).
DISALLOWED = {
    "uacp_run_init": ("execute", "verify", "resolve"),
    "uacp_run_finalize": ("triage", "propose", "plan", "execute", "verify"),
}


def _guardian(root: Path, stages: dict | None = None) -> Guardian:
    """Guardian with the repo policy and the production stages_default()."""
    phase_config = {"stages": stages if stages is not None else stages_default()}
    return Guardian(GuardianPolicy.load(str(root)), phase_config=phase_config)


def _ctx(root: Path, phase: str, **extra) -> dict:
    base = {
        "uacp_run_id": "uacp-test-001",
        "uacp_phase": phase,
        "workspace": str(root),
        "policy_version": "0.1",
        "authority_artifact": "plans/test.yaml",
        "reason": "lifecycle test",
        "source": "triage",
        "declared_side_effects": [],
    }
    base.update(extra)
    return base


# --- classification & policy membership -------------------------------------
@pytest.mark.parametrize("tool", RUN_TOOLS)
def test_run_tool_is_classified_state_uacp(temp_uacp_root, tool):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert policy.tool_classification.get(tool) == "state.uacp", (
        f"{tool} must be classified state.uacp or Layer A treats it as an "
        f"ungoverned mutator; got {policy.tool_classification.get(tool)!r}"
    )


@pytest.mark.parametrize("tool", RUN_TOOLS)
def test_run_tool_is_state_uacp_allowed_tool(temp_uacp_root, tool):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert policy.is_allowed_tool_for_category("state.uacp", tool), (
        f"{tool} must be an allowed_tool for state.uacp or Layer A blocks it "
        f"with 'direct UACP state writes must use uacp_state_write'"
    )


@pytest.mark.parametrize("tool", RUN_TOOLS)
def test_run_tool_is_self_attesting(temp_uacp_root, tool):
    policy = GuardianPolicy.load(str(temp_uacp_root))
    assert tool in policy.self_attesting_tools, (
        f"{tool} must be self-attesting (its handler enforces its own "
        f"context/path containment) like uacp_run_registry_update"
    )


# --- stages_default() structural source of truth ----------------------------
@pytest.mark.parametrize("tool", RUN_TOOLS)
def test_stages_default_lists_tool_in_allowed_phases(tool):
    stages = stages_default()
    for phase in ALLOWED[tool]:
        allowed = stages[phase]["allowed_tools"]
        assert tool in allowed, f"{tool} missing from stages_default()[{phase}].allowed_tools"


@pytest.mark.parametrize("tool", DISALLOWED)
def test_stages_default_omits_tool_in_disallowed_phases(tool):
    stages = stages_default()
    for phase in DISALLOWED[tool]:
        allowed = stages[phase]["allowed_tools"]
        assert tool not in allowed, (
            f"{tool} must NOT be in stages_default()[{phase}].allowed_tools"
        )


# --- Guardian Layer B: admitted in allowed phases ---------------------------
def _allowed_cases():
    for tool, phases in ALLOWED.items():
        for phase in phases:
            yield tool, phase


@pytest.mark.parametrize("tool,phase", list(_allowed_cases()))
def test_run_tool_admitted_in_allowed_phase(temp_uacp_root, tool, phase):
    g = _guardian(temp_uacp_root)
    ev = make_event(
        tool_name=tool,
        args=_ctx(temp_uacp_root, phase),
        filesystem_guard_verified=True,
    )
    d = g.evaluate(ev)
    assert d.decision != "block", d
    # Governed as state.uacp, not an ungoverned external mutator.
    assert d.category == "state.uacp", d


# --- Guardian Layer B: blocked in disallowed phases -------------------------
def _disallowed_cases():
    for tool, phases in DISALLOWED.items():
        for phase in phases:
            yield tool, phase


@pytest.mark.parametrize("tool,phase", list(_disallowed_cases()))
def test_run_tool_blocked_in_disallowed_phase(temp_uacp_root, tool, phase):
    g = _guardian(temp_uacp_root)
    ev = make_event(
        tool_name=tool,
        args=_ctx(temp_uacp_root, phase),
        filesystem_guard_verified=True,
    )
    d = g.evaluate(ev)
    assert d.decision == "block", d
    assert "allowed_tools" in d.reason, d


# --- init's no-active-run case (empirically determined) ---------------------
def test_run_init_fails_closed_without_phase(temp_uacp_root):
    """No active run => no phase. Guardian Layer B is skipped (no uacp_phase),
    but Layer A still requires the governed-context fields; uacp_phase is one of
    them, so a truly phaseless init fail-closes. There is no ungoverned
    phaseless backdoor — init is always carried under the agent's declared
    entry phase (see test below)."""
    g = _guardian(temp_uacp_root)
    ctx = _ctx(temp_uacp_root, "")  # empty phase
    ev = make_event(tool_name="uacp_run_init", args=ctx, filesystem_guard_verified=True)
    d = g.evaluate(ev)
    assert d.decision == "block", d
    assert "uacp_phase" in d.reason, d


@pytest.mark.parametrize("phase", ("brainstorm", "triage"))
def test_run_init_admitted_at_entry_phase(temp_uacp_root, phase):
    """At run-creation the agent operates under the declared entry phase; init
    is allowlisted there and admitted as a governed state.uacp writer."""
    g = _guardian(temp_uacp_root)
    ev = make_event(
        tool_name="uacp_run_init",
        args=_ctx(temp_uacp_root, phase),
        filesystem_guard_verified=True,
    )
    d = g.evaluate(ev)
    assert d.decision == "allow_with_audit", d
    assert d.category == "state.uacp", d


# --- non-vacuity guard: an empty allowlist for the phase must block ----------
def test_layer_b_actually_governs_run_tools(temp_uacp_root):
    """Proves the admitted-case tests are non-vacuous: with the tool stripped
    from the phase allowlist (simulating the pre-fix state), Guardian blocks the
    very call the allowed-phase test asserts is admitted."""
    stages = stages_default()
    stages["triage"] = {
        **stages["triage"],
        "allowed_tools": [
            t for t in stages["triage"]["allowed_tools"] if t != "uacp_run_init"
        ],
    }
    g = _guardian(temp_uacp_root, stages=stages)
    ev = make_event(
        tool_name="uacp_run_init",
        args=_ctx(temp_uacp_root, "triage"),
        filesystem_guard_verified=True,
    )
    d = g.evaluate(ev)
    assert d.decision == "block", d
    assert "allowed_tools" in d.reason, d

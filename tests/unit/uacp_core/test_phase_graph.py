"""Agreement tests pinning every transition-graph representation to one source.

The canonical phase graph lives in ``engines/domain/phase_graph.py``. These
tests assert that the production config files, the runtime ``state_machine``
constants, and the canonical projection all agree — so the graph cannot drift
across its four historic representations.

Read the REAL repo config (not the temp fixture): the temp fixture uses the
state-machine ``resolved`` convention and has no ``uacp.toml``, whereas the
production lifecycle graph is what ``phase_graph`` claims to mirror.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import state_machine
from engines.domain import phase_graph
from engines.domain.phase_transitions import stages_default

REPO_ROOT = Path(__file__).resolve().parents[3]


def _code_default_stage_edges() -> set[tuple[str, str]]:
    """Flat ``(from, to)`` edge set from the codified ``stages_default()``.

    Slice 4b T4d-1: production config/phase-transitions.yaml no longer ships a
    ``stages`` block (the grammar is codified). The former
    "phase_graph == YAML stages.*.exits_to" agreement is replaced by this
    INTERNAL-consistency check: the codified stages must DERIVE their
    ``exits_to`` from ``phase_graph`` (not a re-hardcoded second copy of the
    graph). The EXTERNAL drift-guard against config/uacp.toml is unchanged below.
    """
    stages = stages_default()
    return {
        (phase, target)
        for phase, body in stages.items()
        for target in (body.get("exits_to") or [])
    }


def _uacp_toml_allowed_edges() -> set[tuple[str, str]]:
    """Flat ``(from, to)`` edge set from config/uacp.toml [heartgate]."""
    path = REPO_ROOT / "config" / "uacp.toml"
    with path.open("rb") as fh:
        cfg = tomllib.load(fh)
    allowed = (cfg.get("heartgate") or {}).get("allowed_transitions") or []
    edges: set[tuple[str, str]] = set()
    for item in allowed:
        src, _, dst = str(item).partition("->")
        edges.add((src, dst))
    return edges


def test_code_default_stages_exits_to_derive_from_phase_graph() -> None:
    """Codified stages_default() exits_to == phase_graph (internal consistency).

    This is the T4d-1 replacement for the old "phase_graph == YAML
    stages.*.exits_to" assertion: it proves the codified stages derive their
    ``exits_to`` from ``phase_graph.LIFECYCLE_GRAPH`` rather than carrying a
    second hardcoded copy of the graph. The EXTERNAL graph drift-guard lives in
    test_canonical_graph_matches_uacp_toml_allowed_transitions (uacp.toml).
    """
    assert phase_graph.lifecycle_edges() == _code_default_stage_edges(), (
        "stages_default() exits_to drifted from phase_graph.LIFECYCLE_GRAPH "
        "(exits_to must be DERIVED from the canonical graph, not re-hardcoded)"
    )


def test_canonical_graph_matches_uacp_toml_allowed_transitions() -> None:
    """phase_graph lifecycle graph == config/uacp.toml [heartgate].allowed_transitions."""
    assert phase_graph.lifecycle_edges() == _uacp_toml_allowed_edges(), (
        "phase_graph.LIFECYCLE_GRAPH drifted from config/uacp.toml [heartgate].allowed_transitions"
    )


def test_state_machine_valid_transitions_is_the_projection() -> None:
    """state_machine.VALID_TRANSITIONS == phase_graph.state_machine_projection()."""
    assert state_machine.VALID_TRANSITIONS == phase_graph.state_machine_projection(), (
        "state_machine.VALID_TRANSITIONS drifted from the canonical phase-graph projection"
    )


def test_state_machine_terminal_phases_matches_runtime_terminal_set() -> None:
    """state_machine.TERMINAL_PHASES == phase_graph runtime-terminal set."""
    assert state_machine.TERMINAL_PHASES == phase_graph.runtime_terminal_phases(), (
        "state_machine.TERMINAL_PHASES drifted from the canonical runtime-terminal set"
    )


def test_projection_reproduces_the_historic_five_edges() -> None:
    """The projection must reproduce the canonical 6-edge state-machine graph.

    Updated in Brainstorm-phase slice: brainstorm->triage is a new edge.
    The `historic five edges` comment is updated to reflect the current graph.
    triage->terminal is dropped (terminal sink rule);
    resolve->resolved is the phase-collapse rule.
    brainstorm->terminal is not in LIFECYCLE_GRAPH for this slice
    (explore-and-bail is a tracked follow-up).
    """
    assert phase_graph.state_machine_projection() == {
        "brainstorm": {"triage"},
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }


def test_terminal_phases_are_resolved_and_aborted() -> None:
    assert phase_graph.runtime_terminal_phases() == {"resolved", "aborted"}


def test_brainstorm_is_a_lifecycle_node() -> None:
    """brainstorm must be a node in LIFECYCLE_GRAPH with exits_to {triage}."""
    assert "brainstorm" in phase_graph.LIFECYCLE_GRAPH, (
        "brainstorm not yet in LIFECYCLE_GRAPH — add it in phase_graph.py T3"
    )
    assert phase_graph.LIFECYCLE_GRAPH["brainstorm"] == {"triage"}, (
        "brainstorm exits must be {triage} for this slice "
        "(explore-and-bail via abort-status path is a tracked follow-up)"
    )


def test_projection_reproduces_the_new_six_edges() -> None:
    """After brainstorm lands, state_machine_projection() gains brainstorm->triage."""
    assert phase_graph.state_machine_projection() == {
        "brainstorm": {"triage"},
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }

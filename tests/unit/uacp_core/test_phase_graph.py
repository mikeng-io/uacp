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

import yaml

import state_machine
from engines.domain import phase_graph

REPO_ROOT = Path(__file__).resolve().parents[3]


def _production_lifecycle_edges() -> set[tuple[str, str]]:
    """Flat ``(from, to)`` edge set from config/phase-transitions.yaml stages."""
    path = REPO_ROOT / "config" / "phase-transitions.yaml"
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    stages = cfg.get("stages") or {}
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


def test_canonical_graph_matches_phase_transitions_yaml() -> None:
    """phase_graph lifecycle graph == config/phase-transitions.yaml exits_to."""
    assert phase_graph.lifecycle_edges() == _production_lifecycle_edges(), (
        "phase_graph.LIFECYCLE_GRAPH drifted from config/phase-transitions.yaml stages.*.exits_to"
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
    """The projection must reproduce the exact historic 5-edge graph."""
    assert phase_graph.state_machine_projection() == {
        "triage": {"propose"},
        "propose": {"plan"},
        "plan": {"execute"},
        "execute": {"verify"},
        "verify": {"resolved"},
    }


def test_terminal_phases_are_resolved_and_aborted() -> None:
    assert phase_graph.runtime_terminal_phases() == {"resolved", "aborted"}

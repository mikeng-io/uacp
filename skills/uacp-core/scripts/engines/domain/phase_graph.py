"""Canonical UACP phase graph — the single source of truth for transitions.

PURE LEAF MODULE. Imports nothing from ``state_machine``, ``config``,
``engines``, or any other kernel module — only the stdlib. This is deliberate:
``state_machine`` imports this module as a bare module (via a ``sys.path``
bootstrap) to derive its ``VALID_TRANSITIONS`` / ``TERMINAL_PHASES`` without
triggering ``engines/domain/__init__`` (which would create an import cycle,
since that package re-exports symbols sourced from ``state_machine``).

Consequence: this module is loaded under two names — bare ``phase_graph`` (from
``state_machine``) and ``engines.domain.phase_graph`` (from the package). The
two are distinct module objects. **Keep this module stateless** (no mutable
module-level cache, no registration side-effects): every accessor must return
freshly-built data from the immutable-by-convention ``LIFECYCLE_GRAPH`` so the
two copies stay interchangeable. The value-comparing agreement test cannot
catch divergence introduced by hidden module state.

The transition graph historically lived in four representations:

  1. ``state_machine.VALID_TRANSITIONS`` — runtime "state-machine" convention.
  2. ``config/phase-transitions.yaml`` ``stages.<phase>.exits_to`` — the richer
     "lifecycle/governance" convention.
  3. ``config/uacp.toml [heartgate].allowed_transitions`` — a flat edge list
     that must match (2).
  4. ``tests/conftest.py`` synthetic fixture — state-machine convention.

This module establishes ONE canonical source: the lifecycle/governance graph
(representations 2 and 3). ``state_machine``'s runtime graph is a documented
*projection* of it (see below). The repo-level agreement test
(``tests/unit/uacp_core/test_phase_graph.py``) pins all representations to this
one source so they cannot drift.

Terminal-naming reconciliation (lifecycle <-> state-machine)
------------------------------------------------------------
The two conventions name the end of a run differently. The runtime state
machine is a *coarser* model: it does not model early-exit ``terminal`` edges,
and it does not represent RESOLVE as a distinct phase — it collapses the
lifecycle ``resolve`` phase into the terminal ``resolved`` run-status.

Projection rules (lifecycle graph -> state-machine graph):

  * lifecycle phase ``resolve``  -> runtime terminal status ``resolved``.
    So the edge ``verify -> resolve`` becomes ``verify -> resolved``.
  * drop every edge whose target is ``terminal`` (e.g. ``triage -> terminal``,
    ``resolve -> terminal``). Runtime early-termination is ``Status.aborted``,
    not a phase edge; ``resolved`` is the absorbing terminal state with no
    outgoing edge.
  * every other edge passes through unchanged.

Applying these rules to the 7-edge lifecycle graph yields EXACTLY the historic
5-edge ``VALID_TRANSITIONS``:

    triage   -> {propose}
    propose  -> {plan}
    plan     -> {execute}
    execute  -> {verify}
    verify   -> {resolved}

Mapping table
-------------
    lifecycle phase   state-machine name    notes
    ---------------   ------------------    -----------------------------------
    triage            triage                pass-through
    propose           propose               pass-through
    plan              plan                  pass-through
    execute           execute               pass-through
    verify            verify                pass-through
    resolve           resolved              phase collapsed into terminal status
    terminal (sink)   (dropped)             early-exit; runtime uses aborted
    -                 aborted               runtime-only early-termination; no
                                            lifecycle-graph counterpart

Runtime terminal set ``TERMINAL_PHASES = {"resolved", "aborted"}``:
``resolved`` is the projection of the lifecycle ``resolve`` phase; ``aborted``
is a runtime-only early-termination status with no lifecycle-graph counterpart.
Both are kept.
"""

from __future__ import annotations

# --- Canonical lifecycle/governance graph (source of truth) -----------------
# Each key is a lifecycle phase; the value is its set of ``exits_to`` targets.
# Mirrors config/phase-transitions.yaml stages.*.exits_to and
# config/uacp.toml [heartgate].allowed_transitions exactly. The agreement test
# enforces that equality against the production config files.
LIFECYCLE_GRAPH: dict[str, set[str]] = {
    "brainstorm": {"triage"},
    "triage": {"propose", "terminal"},
    "propose": {"plan"},
    "plan": {"execute"},
    "execute": {"verify"},
    "verify": {"resolve"},
    "resolve": {"terminal"},
}

# The synthetic terminal sink target used by early-exit lifecycle edges. It is
# not itself a phase node; it is dropped by the state-machine projection.
TERMINAL_SINK: str = "terminal"

# Lifecycle phase that the state machine collapses into a terminal run-status.
_RESOLVE_PHASE: str = "resolve"
_RESOLVED_STATUS: str = "resolved"

# Runtime-only early-termination status. No lifecycle-graph counterpart.
_ABORTED_STATUS: str = "aborted"

# Belt-and-suspenders: keep the named tokens honest against the graph literal so
# a future edit to LIFECYCLE_GRAPH cannot silently desync the projection.
assert _RESOLVE_PHASE in LIFECYCLE_GRAPH, "_RESOLVE_PHASE must be a lifecycle phase"
assert any(TERMINAL_SINK in targets for targets in LIFECYCLE_GRAPH.values()), (
    "TERMINAL_SINK must appear as an exits_to target"
)


def lifecycle_edges() -> set[tuple[str, str]]:
    """Return the canonical lifecycle graph as a flat set of ``(from, to)`` edges."""
    return {(src, dst) for src, targets in LIFECYCLE_GRAPH.items() for dst in targets}


def state_machine_projection() -> dict[str, set[str]]:
    """Project the canonical lifecycle graph onto the runtime state-machine graph.

    Applies the documented projection rules:
      * map the ``resolve`` phase target to the ``resolved`` terminal status,
      * drop every edge whose target is the ``terminal`` sink,
      * pass everything else through unchanged.

    Returns the 5-edge ``VALID_TRANSITIONS`` graph.
    """
    projected: dict[str, set[str]] = {}
    for src, targets in LIFECYCLE_GRAPH.items():
        new_targets: set[str] = set()
        for dst in targets:
            if dst == TERMINAL_SINK:
                continue  # early-exit edge; not modeled as a phase edge at runtime
            if dst == _RESOLVE_PHASE:
                new_targets.add(_RESOLVED_STATUS)  # phase collapsed into terminal status
            else:
                new_targets.add(dst)
        if new_targets:
            projected[src] = new_targets
    return projected


def canonical_transition_target(to_phase: str) -> str:
    """Canonicalize a caller-supplied transition target to the state-machine vocabulary
    (#114 alias, not a graph change).

    Docs, skills, config `allowed_transitions`, and the agent-path `validate_transition`
    all speak the LIFECYCLE phase name ``resolve``; the state-machine projection
    collapses that phase into the ``resolved`` terminal STATUS, so the governed
    ``VALID_TRANSITIONS`` only lists ``resolved``. An agent following the docs and
    driving ``verify -> resolve`` was therefore rejected (the user-visible schism). This
    accepts ``resolve`` as an alias for the projected ``resolved`` at the transition
    boundary — every other phase passes through unchanged, so nothing downstream (which
    already speaks ``resolved``) is affected. It is INPUT normalization only; the
    recorded/canonical edge stays ``VERIFY->RESOLVED``.

    Expects an already-stripped, lowercase target (as ``handle_transition`` supplies —
    phase tokens are lowercase-exact); a non-normalized ``"Resolve"`` passes through
    unchanged and is then rejected by the membership check.
    """
    return _RESOLVED_STATUS if to_phase == _RESOLVE_PHASE else to_phase


def runtime_terminal_phases() -> set[str]:
    """Return the runtime ``TERMINAL_PHASES`` set.

    ``resolved`` is the projection of the lifecycle ``resolve`` phase;
    ``aborted`` is a runtime-only early-termination status.
    """
    return {_RESOLVED_STATUS, _ABORTED_STATUS}

"""Phase-exit invariants validator (A3.1 extraction from the Heartgate god-class).

Enforces ``stages.<from_phase>.phase_exit_invariants`` at a transition: each
required invariant is checked by kind (artifact glob / gate-ledger entry / graph
invariant). Carved out of ``Heartgate._validate_phase_exit_invariants`` (design/
graph-engine nodes 30/31) as a pure function of explicit inputs; the hub keeps a
thin delegating method so its callers (and the tests that drive it directly) are
unaffected.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .helpers import glob_matches_any, ledger_contains_gate


def validate_phase_exit_invariants(
    artifact: Mapping[str, Any],
    *,
    stages: Any,
    uacp_root: Path,
    governed_root: Path,
    blockers: list[str],
) -> None:
    """Phase 1 / Item 1.2: enforce phase_exit_invariants from config.

    For the transition's `from_phase`, load `stages.<from_phase>.phase_exit_invariants`
    and check each required invariant by its kind:
    - `artifact_glob` — must match at least one file under UACP_ROOT;
    - `gate_ledger_entry` — must appear in state/gate-ledger/{run_id}.jsonl;
    - `graph_invariant` (D35) — runs the phase-scoped structural subset of the
      graph_projection engine for this transition (scope = `<from_phase>_exit`,
      e.g. `plan_exit`); any block-severity violation becomes a transition
      blocker. This is what makes a dropped intent / orphan / missing coverage
      fail at the boundary where its inputs first complete, instead of only at
      terminal closure.
    """
    from_phase = str(artifact.get("from_phase") or "")
    run_id = str(artifact.get("run_id") or "")
    if not isinstance(stages, Mapping):
        blockers.append("phase_exit_invariants: stages config must be a mapping")
        return
    stage = stages.get(from_phase) or {}
    if not isinstance(stage, Mapping):
        blockers.append(f"phase_exit_invariants: stage '{from_phase}' config must be a mapping")
        return
    invariants = stage.get("phase_exit_invariants") or []
    if not invariants:
        return
    for inv in invariants:
        if not isinstance(inv, Mapping):
            blockers.append("phase_exit_invariant must be a mapping")
            continue
        required = bool(inv.get("required"))
        if not required:
            continue
        glob_pattern = str(inv.get("artifact_glob") or "")
        ledger_gate = str(inv.get("gate_ledger_entry") or "")
        graph_scope = str(inv.get("graph_invariant") or "")
        if glob_pattern:
            if "{run_id}" in glob_pattern and not run_id:
                blockers.append(
                    f"phase_exit_invariant unmet: run_id required to resolve glob '{glob_pattern}'"
                )
                continue
            pat = glob_pattern.replace("{run_id}", run_id) if run_id else glob_pattern
            if not glob_matches_any(governed_root, pat):
                blockers.append(f"phase_exit_invariant unmet: no artifact matches '{pat}'")
        elif ledger_gate:
            if not run_id:
                blockers.append(
                    f"phase_exit_invariant unmet: run_id required to verify ledger entry "
                    f"'{ledger_gate}'"
                )
            elif not ledger_contains_gate(governed_root, run_id, ledger_gate):
                blockers.append(
                    f"phase_exit_invariant unmet: gate ledger missing entry '{ledger_gate}'"
                )
        elif graph_scope:
            if not run_id:
                blockers.append(
                    "phase_exit_invariant unmet: run_id required for graph_invariant "
                    f"'{graph_scope}'"
                )
                continue
            # D35: run the phase-scoped structural subset of graph_projection for
            # this transition. The engine never raises; block-severity violations
            # (dropped intent / orphan / phantom / missing coverage / contradiction)
            # gate the phase exit.
            from engines.graph_projection import validate_graph_invariants

            for v in validate_graph_invariants(uacp_root, run_id, graph_scope):
                if v.severity == "block":
                    blockers.append(f"phase_exit_invariant unmet: {v.code}: {v.message}")

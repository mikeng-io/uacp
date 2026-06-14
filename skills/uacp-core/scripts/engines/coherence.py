"""Manifest coherence validator for UACP runs.

Read-only, defensive consumer of the kernel's emitted state. Given a workspace
(UACP_ROOT) and a run_id, it checks that the run manifest, the gate ledger,
``state/current.yaml`` and the referenced artifacts all AGREE — i.e. that the
run is internally COHERENT end-to-end.

This module never mutates anything and NEVER raises on a malformed or missing
run: every failure mode (absent file, garbled YAML, broken JSONL line, schema
drift) is converted into a :class:`~engines.base.Violation` rather than an
exception. An empty result list means "coherent".

It is the first of the computed Heartgate engines: it imports the shared
``Violation`` from :mod:`engines.base` and registers itself in that module's
``ENGINES`` registry. It imports only public-ish kernel helpers and re-reads
files from disk; it does not depend on kernel internals beyond path resolution
and the state-machine's transition graph / terminal-phase set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

# This module lives at skills/uacp-core/scripts/engines/coherence.py. Make the
# sibling kernel modules (skills/uacp-core/scripts) and the uacp-state
# state_machine importable regardless of how this file is invoked.
_ENGINES_DIR = Path(__file__).resolve().parent
_CORE_DIR = _ENGINES_DIR.parent
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))
_STATE_DIR = _CORE_DIR.parents[1] / "uacp-state" / "scripts"
if str(_STATE_DIR) not in sys.path:
    sys.path.insert(0, str(_STATE_DIR))

from filesystem import _resolve_uacp_path  # noqa: E402

# VALID_TRANSITIONS / TERMINAL_PHASES are the single source of truth for the
# legal phase graph. Import them rather than re-declaring (no field invention).
from state_machine import TERMINAL_PHASES, VALID_TRANSITIONS  # noqa: E402

# The shared violation type + engine registry. Every engine reports the same
# Violation; coherence registers itself in ENGINES at the bottom of this module.
from engines.base import ENGINES, Violation  # noqa: E402

# Artifact types (manifest.artifacts keys) and/or filename conventions whose
# file body carries a top-level ``run_id`` we can cross-check (C1). Grounded in
# config/artifact-schemas.yaml: scope, lessons, run_registry all declare run_id.
_RUN_ID_BEARING_KEYS = {"scope", "lessons"}


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _safe_load_yaml(path: Path) -> tuple[Any, str | None]:
    """Return (parsed, error). error is a human string when the load failed."""
    try:
        if not path.exists():
            return None, f"file not found: {path}"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw, None
    except Exception as exc:  # defensive: garbled YAML must not raise
        return None, f"{type(exc).__name__}: {exc}"


def _parse_gate_edge(gate: str) -> tuple[str, str] | None:
    """Parse a ledger ``gate`` like 'TRIAGE->PROPOSE' into (from, to) lowercased.

    Returns None for gates that are not phase-transition gates (so non-transition
    ledger records — should the kernel ever emit them — are not mistaken for
    orphans in C2).
    """
    if not isinstance(gate, str) or "->" not in gate:
        return None
    left, _, right = gate.partition("->")
    left, right = left.strip().lower(), right.strip().lower()
    if not left or not right:
        return None
    return left, right


def _read_ledger(path: Path) -> tuple[list[dict[str, Any]], list[Violation]]:
    """Read the gate-ledger JSONL. Returns (records, violations).

    Each malformed line becomes a violation rather than an exception.
    """
    records: list[dict[str, Any]] = []
    violations: list[Violation] = []
    if not path.exists():
        # Absence is reported by the caller against the manifest's expectations;
        # here we simply return empty so callers can decide if that's a problem.
        return records, violations
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        violations.append(_v("C2_LEDGER_UNREADABLE", f"gate ledger unreadable: {type(exc).__name__}: {exc}"))
        return records, violations
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception as exc:
            violations.append(
                _v("C2_LEDGER_LINE_MALFORMED", f"gate ledger line {lineno} is not valid JSON: {exc}")
            )
            continue
        if not isinstance(rec, dict):
            violations.append(
                _v("C2_LEDGER_LINE_MALFORMED", f"gate ledger line {lineno} is not a JSON object")
            )
            continue
        records.append(rec)
    return records, violations


def validate_run_coherence(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that a UACP run is internally coherent end-to-end.

    Returns a list of Violation. Empty == coherent. Never raises.
    """
    violations: list[Violation] = []
    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("C0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("C0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    manifest_path = root / "state" / "runs" / f"{run_id}.yaml"
    manifest, err = _safe_load_yaml(manifest_path)
    if err is not None:
        return [_v("C0_MANIFEST_MISSING", f"run manifest could not be loaded: {err}")]
    if not isinstance(manifest, dict):
        return [_v("C0_MANIFEST_MALFORMED", "run manifest is not a YAML mapping")]

    m_run_id = manifest.get("run_id")
    status = manifest.get("status")
    current_phase = manifest.get("current_phase")
    finalized_at = manifest.get("finalized_at")
    artifacts = manifest.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        violations.append(_v("C0_MANIFEST_MALFORMED", "manifest.artifacts is not a mapping"))
        artifacts = {}
    state_history = manifest.get("state_history") or []
    if not isinstance(state_history, list):
        violations.append(_v("C0_MANIFEST_MALFORMED", "manifest.state_history is not a list"))
        state_history = []

    # Phase transitions recorded in history, in order.
    history_edges: list[tuple[str, str]] = []
    for entry in state_history:
        if not isinstance(entry, dict):
            continue
        if entry.get("event") != "phase_transition":
            continue
        frm = entry.get("from_phase")
        to = entry.get("to_phase")
        if isinstance(frm, str) and isinstance(to, str):
            history_edges.append((frm.strip().lower(), to.strip().lower()))

    # Read the gate ledger once (shared by C1 + C2).
    ledger_path = root / "state" / "gate-ledger" / f"{run_id}.jsonl"
    ledger_records, ledger_read_violations = _read_ledger(ledger_path)
    violations.extend(ledger_read_violations)

    violations.extend(_check_c1_run_id(root, run_id, m_run_id, ledger_records, artifacts))
    violations.extend(_check_c2_ledger_history(history_edges, ledger_records, ledger_path))
    violations.extend(_check_c3_phase_path(history_edges))
    violations.extend(
        _check_c4_terminal(root, status, current_phase, finalized_at, artifacts)
    )
    violations.extend(_check_c5_artifacts(root, artifacts))
    violations.extend(_check_c6_scope_registry(root, run_id, artifacts))

    return violations


# --------------------------------------------------------------------------- C1
def _check_c1_run_id(
    root: Path,
    run_id: str,
    m_run_id: Any,
    ledger_records: list[dict[str, Any]],
    artifacts: dict[str, Any],
) -> list[Violation]:
    """manifest.run_id must equal: the requested run_id, current.yaml's
    active_run_id (only when current.yaml points at THIS run), every ledger
    record's run_id, and the run_id inside every referenced run-id-bearing
    artifact."""
    out: list[Violation] = []

    if m_run_id != run_id:
        out.append(
            _v(
                "C1_RUN_ID_MISMATCH",
                f"manifest.run_id '{m_run_id}' does not match requested run_id '{run_id}'",
            )
        )

    # current.yaml — only cross-check when it points at this run.
    current_path = root / "state" / "current.yaml"
    current, err = _safe_load_yaml(current_path)
    if err is None and isinstance(current, dict):
        active = current.get("active_run_id")
        # If the pointer names this run, its id must agree with the manifest.
        if active == run_id or active == m_run_id:
            if active != m_run_id:
                out.append(
                    _v(
                        "C1_RUN_ID_MISMATCH",
                        f"current.yaml active_run_id '{active}' disagrees with manifest.run_id '{m_run_id}'",
                    )
                )
    elif err is not None and current_path.exists():
        out.append(_v("C1_CURRENT_UNREADABLE", f"state/current.yaml unreadable: {err}", severity="warn"))

    # Every gate-ledger record must carry this run's id.
    for idx, rec in enumerate(ledger_records, start=1):
        rid = rec.get("run_id")
        if rid != m_run_id:
            out.append(
                _v(
                    "C1_RUN_ID_MISMATCH",
                    f"gate-ledger record #{idx} (gate {rec.get('gate')!r}) run_id '{rid}' "
                    f"!= manifest.run_id '{m_run_id}'",
                )
            )

    # Each referenced run-id-bearing artifact's body must carry this run's id.
    for key in _RUN_ID_BEARING_KEYS:
        rel = artifacts.get(key)
        if not isinstance(rel, str) or not rel:
            continue
        apath = _safe_resolve(root, rel)
        if apath is None or not apath.exists():
            # Existence is C5's job; skip the run_id check on a missing file.
            continue
        body, aerr = _safe_load_yaml(apath)
        if aerr is not None or not isinstance(body, dict):
            out.append(
                _v(
                    "C1_ARTIFACT_UNREADABLE",
                    f"artifact '{key}' ({rel}) could not be parsed for run_id check: {aerr}",
                    severity="warn",
                )
            )
            continue
        body_rid = body.get("run_id")
        if body_rid is not None and body_rid != m_run_id:
            out.append(
                _v(
                    "C1_RUN_ID_MISMATCH",
                    f"artifact '{key}' ({rel}) run_id '{body_rid}' != manifest.run_id '{m_run_id}'",
                )
            )

    return out


# --------------------------------------------------------------------------- C2
def _check_c2_ledger_history(
    history_edges: list[tuple[str, str]],
    ledger_records: list[dict[str, Any]],
    ledger_path: Path,
) -> list[Violation]:
    """The phase transitions in state_history must correspond 1:1 to
    phase-transition gates in the ledger.

    Relationship (confirmed against the happy-path run): a transition
    ``from -> to`` is recorded in the ledger as a gate ``FROM->TO`` (upper-cased)
    that is appended BEFORE the transition. So the multiset of history edges
    must equal the multiset of phase-transition gate edges in the ledger.
    Orphans in either direction are violations.
    """
    out: list[Violation] = []

    ledger_edges: list[tuple[str, str]] = []
    for rec in ledger_records:
        edge = _parse_gate_edge(rec.get("gate", ""))
        if edge is not None:
            ledger_edges.append(edge)

    if not ledger_path.exists() and history_edges:
        out.append(
            _v(
                "C2_LEDGER_MISSING",
                f"manifest records {len(history_edges)} phase transition(s) but no gate ledger exists at "
                f"{ledger_path}",
            )
        )
        return out

    from collections import Counter

    h_counts = Counter(history_edges)
    l_counts = Counter(ledger_edges)

    # History edges without a matching ledger gate.
    for edge, n in (h_counts - l_counts).items():
        out.append(
            _v(
                "C2_HISTORY_WITHOUT_LEDGER",
                f"state_history has {n} unmatched transition(s) {edge[0]}->{edge[1]} with no corresponding "
                f"gate-ledger entry",
            )
        )
    # Ledger gates without a matching history edge.
    for edge, n in (l_counts - h_counts).items():
        out.append(
            _v(
                "C2_LEDGER_WITHOUT_HISTORY",
                f"gate ledger has {n} phase-transition gate(s) {edge[0].upper()}->{edge[1].upper()} with no "
                f"corresponding state_history transition",
            )
        )

    return out


# --------------------------------------------------------------------------- C3
def _check_c3_phase_path(history_edges: list[tuple[str, str]]) -> list[Violation]:
    """The sequence of (from,to) edges must be a contiguous legal walk through
    VALID_TRANSITIONS, starting at 'triage', with each edge legal, each step
    continuing from the previous step's destination, and no repeated phase
    (no cycles)."""
    out: list[Violation] = []
    if not history_edges:
        return out  # a run with no transitions yet is vacuously path-coherent

    first_from = history_edges[0][0]
    if first_from != "triage":
        out.append(
            _v(
                "C3_PHASE_PATH_BAD_START",
                f"phase path must start at 'triage'; first transition starts at '{first_from}'",
            )
        )

    visited = {history_edges[0][0]}
    prev_to: str | None = None
    for frm, to in history_edges:
        # contiguity: each edge must start where the previous ended
        if prev_to is not None and frm != prev_to:
            out.append(
                _v(
                    "C3_PHASE_PATH_GAP",
                    f"non-contiguous phase path: transition '{frm}->{to}' does not continue from previous "
                    f"phase '{prev_to}'",
                )
            )
        # legality: edge must exist in VALID_TRANSITIONS
        allowed = VALID_TRANSITIONS.get(frm, set())
        if to not in allowed:
            out.append(
                _v(
                    "C3_PHASE_PATH_ILLEGAL_EDGE",
                    f"illegal phase transition '{frm}->{to}' (allowed from '{frm}': {sorted(allowed)})",
                )
            )
        # no cycles: destination must not have been visited already
        if to in visited:
            out.append(
                _v(
                    "C3_PHASE_PATH_CYCLE",
                    f"phase path revisits '{to}' (cycle) via transition '{frm}->{to}'",
                )
            )
        visited.add(to)
        prev_to = to

    return out


# --------------------------------------------------------------------------- C4
def _check_c4_terminal(
    root: Path,
    status: Any,
    current_phase: Any,
    finalized_at: Any,
    artifacts: dict[str, Any],
) -> list[Violation]:
    """Terminal coherence.

    If status == 'resolved': current_phase must be in TERMINAL_PHASES, finalized_at
    must be set, and a closure/lessons artifact must be referenced AND exist.
    If status != 'resolved': finalized_at must be unset.
    """
    out: list[Violation] = []

    is_resolved = status == "resolved"
    if is_resolved:
        if current_phase not in TERMINAL_PHASES:
            out.append(
                _v(
                    "C4_TERMINAL_PHASE_MISMATCH",
                    f"status is 'resolved' but current_phase '{current_phase}' is not terminal "
                    f"({sorted(TERMINAL_PHASES)})",
                )
            )
        if not finalized_at:
            out.append(
                _v(
                    "C4_FINALIZED_AT_MISSING",
                    "status is 'resolved' but finalized_at is unset",
                )
            )
        # Closure evidence: a lessons artifact must be referenced and present.
        lessons_rel = artifacts.get("lessons")
        if not isinstance(lessons_rel, str) or not lessons_rel:
            out.append(
                _v(
                    "C4_CLOSURE_ARTIFACT_MISSING",
                    "resolved run does not reference a 'lessons' (closure) artifact",
                )
            )
        else:
            apath = _safe_resolve(root, lessons_rel)
            if apath is None or not apath.exists():
                out.append(
                    _v(
                        "C4_CLOSURE_ARTIFACT_MISSING",
                        f"resolved run references lessons artifact '{lessons_rel}' but it does not exist on disk",
                    )
                )
    else:
        if finalized_at:
            out.append(
                _v(
                    "C4_FINALIZED_AT_SET_WHILE_UNRESOLVED",
                    f"status is '{status}' (not resolved) but finalized_at is set to '{finalized_at}'",
                )
            )

    return out


# --------------------------------------------------------------------------- C5
def _check_c5_artifacts(root: Path, artifacts: dict[str, Any]) -> list[Violation]:
    """Every referenced artifact path must exist on disk and resolve INSIDE the
    workspace (no traversal / escape)."""
    out: list[Violation] = []
    for key, rel in artifacts.items():
        if not isinstance(rel, str) or not rel:
            out.append(
                _v("C5_ARTIFACT_PATH_INVALID", f"artifact '{key}' has a non-string/empty path: {rel!r}")
            )
            continue
        apath = _safe_resolve(root, rel)
        if apath is None:
            out.append(
                _v(
                    "C5_ARTIFACT_PATH_ESCAPES",
                    f"artifact '{key}' path '{rel}' does not resolve inside the workspace",
                )
            )
            continue
        if not apath.exists():
            out.append(
                _v(
                    "C5_ARTIFACT_MISSING",
                    f"artifact '{key}' path '{rel}' does not exist on disk ({apath})",
                )
            )
    return out


# --------------------------------------------------------------------------- C6
def _check_c6_scope_registry(
    root: Path, run_id: str, artifacts: dict[str, Any]
) -> list[Violation]:
    """scope.write_paths and the run-registry's active_runs entry for this run
    must declare the same write_paths.

    Only checked when BOTH a scope artifact (with write_paths) is referenced AND
    the run appears in state/run-registry.yaml. If either is absent this check is
    a no-op (there is no durable write-log to compare against — see report).
    """
    out: list[Violation] = []

    scope_rel = artifacts.get("scope")
    if not isinstance(scope_rel, str) or not scope_rel:
        return out
    scope_path = _safe_resolve(root, scope_rel)
    if scope_path is None or not scope_path.exists():
        return out  # existence handled by C5
    scope_body, serr = _safe_load_yaml(scope_path)
    if serr is not None or not isinstance(scope_body, dict):
        return out
    if "write_paths" not in scope_body:
        return out
    scope_wps = scope_body.get("write_paths") or []
    if not isinstance(scope_wps, list):
        out.append(
            _v("C6_SCOPE_WRITE_PATHS_MALFORMED", f"scope.write_paths is not a list ({scope_rel})", severity="warn")
        )
        return out

    registry_path = root / "state" / "run-registry.yaml"
    registry, rerr = _safe_load_yaml(registry_path)
    if rerr is not None or not isinstance(registry, dict):
        return out  # no durable registry to compare against
    active = registry.get("active_runs") or []
    if not isinstance(active, list):
        return out
    entry = next(
        (e for e in active if isinstance(e, dict) and e.get("run_id") == run_id), None
    )
    if entry is None:
        return out  # run not registered (e.g. deregistered at RESOLVE) — nothing to compare
    reg_wps = entry.get("write_paths") or []
    if not isinstance(reg_wps, list):
        return out

    if set(scope_wps) != set(reg_wps):
        out.append(
            _v(
                "C6_WRITE_PATHS_DISAGREE",
                f"scope.write_paths {sorted(map(str, scope_wps))} disagree with run-registry write_paths "
                f"{sorted(map(str, reg_wps))} for run '{run_id}'",
            )
        )
    return out


# --------------------------------------------------------------------------- util
def _safe_resolve(root: Path, rel: str) -> Path | None:
    """Resolve a UACP-root-relative path defensively. Returns None if it escapes
    the workspace or is otherwise unresolvable (never raises)."""
    try:
        resolved = _resolve_uacp_path(rel, root)
        resolved.relative_to(root)
        return resolved
    except Exception:
        return None


# Register this engine. Guard against double-registration if the module is
# imported under more than one name (e.g. "coherence" and "engines.coherence").
if not any(name == "coherence" for name, _ in ENGINES):
    ENGINES.append(("coherence", validate_run_coherence))

"""Evidence-completeness validator for UACP runs (codes prefixed ``EV_``).

Enforces the kernel's "no self-attesting closures" invariant: every phase a run
*claims to have completed* must have left REAL backing evidence — the artifact(s)
and gate-ledger entry that the config declares are required to legitimately exit
that phase — not merely a status flag in the manifest.

Grounding (what a "completion claim" and "evidence" actually are here):

* **Completion claim** — a phase ``P`` is treated as completed when the manifest's
  ``state_history`` contains a ``phase_transition`` whose ``from_phase == P``. That
  is the run's own durable assertion that it *left* ``P``. (We deliberately use
  the recorded transition, not ``current_phase`` ordering, because the transition
  is the concrete evidentiary event; a phase the run sits *in* is not yet claimed
  complete and has no exit obligation.)
* **Required evidence** — read from ``config/phase-transitions.yaml`` at
  ``stages.<phase>.phase_exit_invariants``. Each invariant declares EITHER an
  ``artifact_glob`` (a workspace-relative glob, ``{run_id}`` templated) OR a
  ``gate_ledger_entry`` (a gate string that must appear in the run's gate ledger),
  plus ``required: true|false``. Only invariants with ``required: true`` AND no
  unresolved ``applies_when`` condition are enforced (see "What this CANNOT
  verify" below).

The engine reads the *run's own workspace* config (``<root>/config/
phase-transitions.yaml``) — in production that is the full lifecycle config; in a
test it is whatever the test seeded. If a completed phase declares no
``phase_exit_invariants`` (or none that are required), that phase has *no* required
evidence and yields no violation — we compute against whatever invariants ARE
declared and never invent requirements.

Codes:

* ``EV_PHASE_EXIT_ARTIFACT_MISSING`` — a completed phase's required exit artifact
  (``artifact_glob``) matched no file under the workspace.
* ``EV_PHASE_EXIT_LEDGER_MISSING`` — a completed phase's required
  ``gate_ledger_entry`` is absent from the gate ledger.
* ``EV_RESOLVED_WITHOUT_EVIDENCE`` — ``status == 'resolved'`` but the RESOLVE
  phase's own required exit evidence (artifact and/or ledger entry, per its
  ``phase_exit_invariants``) is missing. This catches a run that flipped its
  status to resolved without the resolve-phase artifact ever landing — even when
  the resolve transition is not (yet) in ``state_history``.

What this engine CANNOT verify (honest limits):

* **Adaptive / conditional invariants.** Invariants carrying ``applies_when``
  (e.g. ``adaptive_proposal_package_selected``) depend on a runtime selection
  outcome this read-only engine cannot observe from the manifest alone, so they
  are SKIPPED rather than guessed. Likewise ``package_directory`` invariants are
  not enforced (they are adaptive and human-reviewable).
* **Evidence *quality*.** A matched artifact is checked for existence only, not
  for correctness/sufficiency of its contents. "Has an artifact" is necessary,
  not sufficient — semantic adequacy is a council concern.
* **PIV checkpoint contracts.** If a plan declares per-checkpoint PIV evidence,
  that is not modelled in ``phase_exit_invariants`` and is not computed here.

Relationship to ``coherence`` (deliberate non-overlap):

* coherence **C2** asks "do ``state_history`` and the gate ledger *agree* (1:1 on
  phase-transition gates)?" — a consistency question between two manifest-derived
  views. It says nothing about whether a *required exit artifact* exists.
* coherence **C4** checks that a *resolved* run references a ``lessons`` artifact
  (via ``manifest.artifacts['lessons']``) and that that referenced file exists.
* This engine asks a different question: "for each phase the run CLAIMS to have
  completed, are that phase's CONFIG-DECLARED required exit artifacts + ledger
  entries actually present?" It is config-driven (per ``phase_exit_invariants``),
  not manifest-reference-driven. ``EV_RESOLVED_WITHOUT_EVIDENCE`` specifically
  checks the resolve phase's *declared exit invariants* on disk/ledger — which
  C4's ``manifest.artifacts['lessons']`` reference check does not cover (a run can
  satisfy one and not the other).

Architecture: PURE of filesystem I/O. All disk reads go through :mod:`engines.io`
read-models; this module never raises — every failure mode becomes a
:class:`~engines.base.Violation`. An empty result list means "complete".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engines.base import ENGINES, Violation
from engines.io import (
    glob_in_workspace,
    load_ledger,
    load_manifest,
    load_phase_transitions,
)
from engines.io.loaders import ManifestDoc


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _gate_strings(ledger_entries: list[Any]) -> set[str]:
    """Every non-empty ``gate`` string present in the gate ledger."""
    out: set[str] = set()
    for rec in ledger_entries:
        g = getattr(rec, "gate", None)
        if isinstance(g, str) and g.strip():
            out.add(g.strip())
    return out


def _completed_phases(state_history: list[Any]) -> list[str]:
    """Phases the run CLAIMS to have completed: distinct ``from_phase`` values of
    ``phase_transition`` entries, in first-seen order."""
    seen: list[str] = []
    for entry in state_history:
        if not isinstance(entry, dict):
            continue
        if entry.get("event") != "phase_transition":
            continue
        frm = entry.get("from_phase")
        if isinstance(frm, str) and frm.strip():
            p = frm.strip().lower()
            if p not in seen:
                seen.append(p)
    return seen


def _stage_invariants(config: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    """Return the ``phase_exit_invariants`` list for ``phase`` (or [] if absent /
    malformed). Tolerant of a missing ``stages`` block or non-mapping stage."""
    stages = config.get("stages")
    if not isinstance(stages, dict):
        return []
    stage = stages.get(phase)
    if not isinstance(stage, dict):
        return []
    inv = stage.get("phase_exit_invariants")
    if not isinstance(inv, list):
        return []
    return [i for i in inv if isinstance(i, dict)]


def _is_enforceable(inv: dict[str, Any]) -> bool:
    """An invariant is enforced only when it is explicitly required AND carries no
    unresolved adaptive condition we cannot evaluate read-only."""
    if inv.get("required") is not True:
        return False
    if "applies_when" in inv:
        return False  # adaptive selection outcome is not observable here
    return True


def _check_phase_evidence(
    workspace: Path,
    run_id: str,
    phase: str,
    invariants: list[dict[str, Any]],
    ledger_gates: set[str],
    *,
    artifact_code: str,
    ledger_code: str,
) -> list[Violation]:
    """Assert every enforceable required invariant for ``phase`` is satisfied:
    each ``artifact_glob`` matches >=1 file, each ``gate_ledger_entry`` is in the
    ledger. Emits ``artifact_code`` / ``ledger_code`` respectively."""
    out: list[Violation] = []
    for inv in invariants:
        if not _is_enforceable(inv):
            continue

        glob = inv.get("artifact_glob")
        if isinstance(glob, str) and glob:
            pattern = glob.replace("{run_id}", run_id)
            if not glob_in_workspace(workspace, pattern):
                out.append(
                    _v(
                        artifact_code,
                        f"completed phase '{phase}' requires an exit artifact matching "
                        f"'{pattern}' but no such file exists under the workspace",
                        phase=phase,
                        artifact_glob=pattern,
                    )
                )

        gate = inv.get("gate_ledger_entry")
        if isinstance(gate, str) and gate:
            if gate not in ledger_gates:
                out.append(
                    _v(
                        ledger_code,
                        f"completed phase '{phase}' requires gate-ledger entry "
                        f"'{gate}' but it is absent from the gate ledger",
                        phase=phase,
                        gate_ledger_entry=gate,
                    )
                )
    return out


def validate_evidence_completeness(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that every phase a run claims to have completed left its required
    exit evidence. Returns a list of Violation (empty == complete). Never raises.
    """
    violations: list[Violation] = []
    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("EV0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("EV0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    loaded = load_manifest(root, run_id)
    if loaded.error is not None:
        return [_v("EV0_MANIFEST_MISSING", f"run manifest could not be loaded: {loaded.error}")]
    doc: ManifestDoc = loaded.value
    manifest = doc.raw

    status = manifest.get("status")
    state_history = manifest.get("state_history") or []
    if not isinstance(state_history, list):
        state_history = []

    # Required evidence is declared in the run's own workspace config. If we
    # cannot read it, we cannot compute any required-evidence obligation: emit a
    # single warn and stop (absence of a spec is not a missing-evidence finding).
    cfg = load_phase_transitions(root)
    if cfg.error is not None or cfg.value is None:
        return [
            _v(
                "EV0_PHASE_CONFIG_UNREADABLE",
                f"config/phase-transitions.yaml could not be read; no exit invariants "
                f"to enforce: {cfg.error}",
                severity="warn",
            )
        ]
    config = cfg.value

    ledger_entries, _ledger_errors = load_ledger(root, run_id)
    ledger_gates = _gate_strings(ledger_entries)

    # 1) Every COMPLETED phase (a recorded from_phase) must have its required exit
    #    evidence present.
    for phase in _completed_phases(state_history):
        invariants = _stage_invariants(config, phase)
        violations.extend(
            _check_phase_evidence(
                root,
                run_id,
                phase,
                invariants,
                ledger_gates,
                artifact_code="EV_PHASE_EXIT_ARTIFACT_MISSING",
                ledger_code="EV_PHASE_EXIT_LEDGER_MISSING",
            )
        )

    # 2) A resolved run must satisfy the RESOLVE phase's own required exit
    #    invariants — even if a resolve transition is not in state_history. This
    #    is the dedicated "no self-attesting closure" check, distinct from
    #    coherence C4's manifest.artifacts['lessons'] reference check.
    if status == "resolved" and "resolve" not in _completed_phases(state_history):
        resolve_inv = _stage_invariants(config, "resolve")
        violations.extend(
            _check_phase_evidence(
                root,
                run_id,
                "resolve",
                resolve_inv,
                ledger_gates,
                artifact_code="EV_RESOLVED_WITHOUT_EVIDENCE",
                ledger_code="EV_RESOLVED_WITHOUT_EVIDENCE",
            )
        )

    return violations


# Register this engine (guard against double-registration under alias imports).
if not any(name == "evidence_completeness" for name, _ in ENGINES):
    ENGINES.append(("evidence_completeness", validate_evidence_completeness))

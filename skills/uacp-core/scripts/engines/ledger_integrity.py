"""Gate-ledger integrity validator for UACP runs.

Read-only, defensive consumer of the kernel's emitted state. Given a workspace
(UACP_ROOT) and a run_id, it checks that the run's gate ledger
(``state/gate-ledger/<run_id>.jsonl``) is a well-formed, append-only log — i.e.
that the ledger is INTERNALLY consistent as a durable audit trail, independent
of the manifest (that cross-check is coherence's job, see C1/C2).

This module never mutates anything and NEVER raises on a malformed or missing
ledger: every failure mode (unreadable file, garbled JSON line, out-of-order
timestamp, foreign run_id, duplicated unique gate) is converted into a
:class:`~engines.base.Violation` rather than an exception. An empty result list
means "the ledger is a clean append-only log". Stable codes are prefixed ``LI_``.

Architecture (hexagonal-lite): this engine is PURE of filesystem I/O. All disk
reads go through :mod:`engines.io` (``load_ledger``), which returns typed
:class:`~engines.domain.LedgerEntry` read-models plus a list of per-line parse
errors; the checks below operate on those. The engine self-registers in
``ENGINES`` at the bottom of this module.

Design decisions (grounded in the kernel writer, ``state._handle_uacp_gate_ledger_append``):

* **Absent ledger is a NO-OP, not a violation.** ``load_ledger`` returns
  ``([], [])`` for a missing file. A run that has not yet recorded any gate
  transition legitimately has no ledger; only an *unreadable* or *garbled*
  ledger is flagged. (Coherence's C2 separately flags the case where the
  manifest claims transitions but the ledger is missing — that is a
  manifest/ledger DISAGREEMENT, out of scope for ledger-local integrity.)

* **``ts`` is an epoch integer.** The writer stamps ``record.setdefault("ts",
  int(time.time()))``, so timestamps are integer seconds since the epoch and are
  compared numerically. A record whose ``ts`` is absent or non-integer is
  reported (``LI_TIMESTAMP_MISSING``) and is NOT used as a monotonicity anchor
  (it neither fires nor suppresses a non-monotonic finding by itself).

* **Duplicate gates: only phase-transition gates are uniqueness-checked.** The
  happy-path run emits exactly one ``FROM->TO`` gate per phase transition, and
  the phase graph is acyclic, so every transition gate is unique. Non-transition
  gates (e.g. ``PIV``, ``PLAN_VALIDATION``) legitimately repeat — PIV retries
  append multiple ``PIV`` records — so they are deliberately EXCLUDED from the
  duplicate check. ``LI_DUPLICATE_GATE`` fires only when the same
  ``FROM->TO`` phase-transition edge appears more than once.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

# The shared violation type + engine registry. Every engine reports the same
# Violation; this engine registers itself in ENGINES at the bottom of the module.
from engines.base import ENGINES, Violation

# All filesystem access is delegated to the io layer (no raw reads here).
from engines.io import load_ledger


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _transition_edge(gate: Any) -> tuple[str, str] | None:
    """Parse a phase-transition gate like 'TRIAGE->PROPOSE' into (from, to).

    Returns None for gates that are not phase-transition gates (e.g. 'PIV',
    'PLAN_VALIDATION'), so only transition gates participate in the duplicate
    check — non-transition gates legitimately repeat.
    """
    if not isinstance(gate, str) or "->" not in gate:
        return None
    left, _, right = gate.partition("->")
    left, right = left.strip(), right.strip()
    if not left or not right:
        return None
    return left, right


def validate(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that a run's gate ledger is a well-formed append-only log.

    Returns a list of Violation. Empty == the ledger is a clean append-only log
    (or is legitimately absent). Never raises.
    """
    violations: list[Violation] = []

    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("LI_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("LI_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    # The io layer never raises: it returns parsed entries plus one error string
    # per unreadable file / malformed line. A missing ledger yields ([], []) and
    # is treated as a no-op (no transitions recorded yet — see module docstring).
    entries, errors = load_ledger(root, run_id)
    for msg in errors:
        if msg.startswith("gate ledger unreadable"):
            violations.append(_v("LI_LEDGER_UNREADABLE", msg))
        else:
            violations.append(_v("LI_LINE_MALFORMED", msg))

    violations.extend(_check_run_id(run_id, entries))
    violations.extend(_check_monotonic_ts(entries))
    violations.extend(_check_duplicate_gate(entries))

    return violations


def _check_run_id(run_id: str, entries: list[Any]) -> list[Violation]:
    """LI_RUN_ID_INCONSISTENT — every ledger record's run_id must equal the
    requested run_id. The ledger file is keyed by run_id, so any foreign run_id
    inside it means the append-only log was written for / corrupted by another
    run (ledger-local integrity, distinct from coherence's manifest-anchored C1).
    """
    out: list[Violation] = []
    for idx, rec in enumerate(entries, start=1):
        rid = rec.run_id
        if rid != run_id:
            out.append(
                _v(
                    "LI_RUN_ID_INCONSISTENT",
                    f"gate-ledger record #{idx} (gate {rec.gate!r}) run_id '{rid}' "
                    f"!= requested run_id '{run_id}'",
                )
            )
    return out


def _check_monotonic_ts(entries: list[Any]) -> list[Violation]:
    """LI_TIMESTAMP_NON_MONOTONIC — ``ts`` (epoch int) must be non-decreasing in
    file order: an append-only log only ever moves forward in time. A record
    without an integer ``ts`` is reported via LI_TIMESTAMP_MISSING and skipped as
    a monotonicity anchor (so a single missing ts neither masks nor fabricates a
    non-monotonic finding).
    """
    out: list[Violation] = []
    prev_ts: int | None = None
    prev_idx: int | None = None
    for idx, rec in enumerate(entries, start=1):
        ts = rec.ts
        if not isinstance(ts, int):
            out.append(
                _v(
                    "LI_TIMESTAMP_MISSING",
                    f"gate-ledger record #{idx} (gate {rec.gate!r}) has no integer "
                    f"'ts' (got {ts!r}); cannot verify monotonicity at this record",
                    severity="warn",
                )
            )
            continue
        if prev_ts is not None and ts < prev_ts:
            out.append(
                _v(
                    "LI_TIMESTAMP_NON_MONOTONIC",
                    f"gate-ledger record #{idx} (gate {rec.gate!r}) ts {ts} is earlier "
                    f"than record #{prev_idx} ts {prev_ts}; append-only ledger must be "
                    f"non-decreasing in time",
                )
            )
        prev_ts = ts
        prev_idx = idx
    return out


def _check_duplicate_gate(entries: list[Any]) -> list[Violation]:
    """LI_DUPLICATE_GATE — the same phase-transition gate (``FROM->TO``) must not
    appear twice. The phase graph is acyclic and the kernel emits one gate per
    transition, so every transition edge is unique. Non-transition gates (PIV,
    PLAN_VALIDATION, ...) are EXCLUDED: they legitimately repeat (e.g. PIV
    retries), so flagging them would be a false positive.
    """
    out: list[Violation] = []
    edges = [edge for rec in entries if (edge := _transition_edge(rec.gate)) is not None]
    counts = Counter(edges)
    for (frm, to), n in counts.items():
        if n > 1:
            out.append(
                _v(
                    "LI_DUPLICATE_GATE",
                    f"phase-transition gate '{frm}->{to}' appears {n} times in the "
                    f"gate ledger; each transition gate must be unique (append-only)",
                )
            )
    return out


# Register this engine. Guard against double-registration if the module is
# imported under more than one name (e.g. "ledger_integrity" and
# "engines.ledger_integrity").
if not any(name == "ledger_integrity" for name, _ in ENGINES):
    ENGINES.append(("ledger_integrity", validate))

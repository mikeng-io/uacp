"""Shared leaf helpers for the Heartgate validators (A3.1 extraction).

Small, dependency-free predicates and filesystem probes used by more than one
validator (or by the hub). They take explicit inputs (a ``governed_root`` /
``run_id``) instead of reaching through a gate instance, so they are pure leaves
with no import back into the hub — keeping the package acyclic. Carved out of the
``Heartgate`` god-class (design/graph-engine nodes 30/31; node 30 lists
"helpers (glob, ledger, transition, safe-id)").

``_is_safe_run_id`` keeps its name verbatim: it is re-exported by ``core.py`` for
external importers (``state.py``, the hermes guardian kernel shim) and has many
internal call sites, so a rename is a separate, tested change.
"""

from __future__ import annotations

import glob as _glob
import json
import re
from pathlib import Path

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _is_safe_run_id(run_id: str) -> bool:
    """True if run_id is safe for use as a filesystem name segment.

    Phase 1 remediation (skeptic F1 / technical F1): bound run_id to a
    conservative charset so it cannot escape state/gate-ledger/ via "..",
    "/", "\\", control chars, or pathological lengths.

    Phase 2 hardening (pc_p1_t2 / CRR-2): also reject the literal `.` and
    `..` so any future code that uses run_id without the .jsonl suffix
    cannot construct a directory reference.
    """
    if not isinstance(run_id, str) or not run_id:
        return False
    if run_id in {".", ".."}:
        return False
    return bool(_RUN_ID_RE.match(run_id))


def glob_matches_any(governed_root: Path, pattern: str) -> bool:
    """True if ``pattern`` matches at least one real file under ``governed_root``.

    Phase 1 remediation (skeptic F3): reject symlinks and out-of-root matches. A
    glob match must resolve to a real file under UACP_ROOT and not be a symlink
    whose target is outside the root.
    """
    try:
        root = governed_root.resolve()
        matches = _glob.glob(str(governed_root / pattern), recursive=True)
        for raw in matches:
            p = Path(raw)
            if p.is_symlink():
                # Resolve and re-check that the target is inside UACP_ROOT.
                try:
                    resolved = p.resolve(strict=True)
                except Exception:
                    continue
                if root != resolved and root not in resolved.parents:
                    continue
                # symlink to in-root real file is acceptable
            else:
                try:
                    resolved = p.resolve(strict=True)
                except Exception:
                    continue
            if not resolved.is_file():
                continue
            if root != resolved and root not in resolved.parents:
                continue
            return True
        return False
    except Exception:
        return False


def ledger_contains_gate(governed_root: Path, run_id: str, gate: str) -> bool:
    """True if the run's gate-ledger contains an entry for ``gate``."""
    if not _is_safe_run_id(run_id):
        return False
    ledger_path = governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
    if not ledger_path.exists():
        return False
    try:
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            # Phase 3 (pc_p2_minor): a corrupted line in the ledger is treated as
            # fail-closed; callers should re-derive coverage rather than silently
            # skip suspicious lines.
            try:
                rec = json.loads(line)
            except Exception:
                return False
            if str(rec.get("gate") or "") == gate:
                return True
    except Exception:
        return False
    return False


__all__ = ["glob_matches_any", "ledger_contains_gate"]

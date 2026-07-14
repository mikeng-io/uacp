"""Witness-advisory ledger I/O — the promotion-evidence substrate (#80).

The conformance witnesses (scope diff/cascade, class) ship **advisory** and their findings
surface transiently in the closure response — nothing tallies them across runs, so the
promotion design (`design/conformance-witnesses/` nodes 02–04) bar for advisory→blocking
promotion cannot be measured. This module records, at each closure, WHICH witness codes fired
for a run, under the governed verification surface
(``<base>/verification/<run_id>-witness-ledger.yaml``), so a later promotion report can
aggregate the SOUND signals: per-family substantive-advisory counts (the false-positive
numerator) and starvation counts. NB (Codex #80): a witness that ran clean emits nothing, and
so does one that never ran — so the clean-run DENOMINATOR is not directly measurable here; that
needs positive witness attestation from the engines (a follow-up), and the report withholds any
"clean" verdict rather than overclaim one.

This is pure OBSERVATION — writing a ledger record changes NO gate outcome and promotes NO
witness. The record is gate-owned evidence (never read back as a gate INPUT), mirroring the
cascade-forecast record (``forecastio``); like every io helper it NEVER raises (a failed
write returns ``False``).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from config import dir_for

# Promotion evidence is PER WITNESS FAMILY, not per run (council #80): a run that starves one
# witness (e.g. the class prober is absent) must NOT mask a real advisory from another (the
# diff witness fired) — collapsing to a single per-run bucket would drop that advisory from
# the false-positive denominator, letting readiness overclaim CLEAN. Each family independently
# classifies a run as witnessable / starved and counts ITS OWN advisories.
#
#   * ``substantive`` — the ADVISORY findings that count toward the FP bar (the ones pending
#     advisory->blocking promotion). Excludes already-blocking codes (see below).
#   * ``unavailable`` — the family's prober was absent / failed (run out of its FP population).
#   * ``unresolved``  — a claimed/touched symbol could not be resolved (a starved witness).


class WitnessFamily:
    """One conformance-witness family and the codes that classify a run FOR IT."""

    __slots__ = ("name", "substantive", "unavailable", "unresolved")

    def __init__(
        self,
        name: str,
        substantive: frozenset[str],
        unavailable: frozenset[str],
        unresolved: frozenset[str],
    ) -> None:
        self.name = name
        self.substantive = substantive
        self.unavailable = unavailable
        self.unresolved = unresolved

    @property
    def codes(self) -> frozenset[str]:
        return self.substantive | self.unavailable | self.unresolved


WITNESS_FAMILIES: tuple[WitnessFamily, ...] = (
    WitnessFamily(
        "scope_diff",
        substantive=frozenset({"SC_DIFF_OUT_OF_SCOPE"}),
        unavailable=frozenset({"SC_DIFF_UNAVAILABLE"}),
        unresolved=frozenset(),
    ),
    WitnessFamily(
        "scope_cascade",
        substantive=frozenset({"SC_UNDECLARED_CASCADE", "SC_SCOPE_OVERDECLARED"}),
        unavailable=frozenset({"SC_WITNESS_UNAVAILABLE"}),
        unresolved=frozenset({"SC_WITNESS_UNRESOLVED_CLAIM", "SC_WITNESS_UNRESOLVED_TOUCHED"}),
    ),
    WitnessFamily(
        "class",
        # Only the ADVISORY class-witness codes. CHK_CLASS_UNDERCLAIM / CHK_ENTAILED_CLASS_INVALID
        # are already BLOCK-severity (see _ALREADY_BLOCKING) — nothing to promote, so they are
        # recorded but never counted as advisory evidence (council #80 P3).
        substantive=frozenset({"CHK_CLASS_REF_UNTOUCHED", "CHK_ENTAILED_CLASS_SUPERSEDED"}),
        unavailable=frozenset({"CHK_CLASS_WITNESS_UNAVAILABLE"}),
        unresolved=frozenset(),
    ),
)

# Witness-family codes that already ship as BLOCK severity (not advisory) — recorded in the raw
# ledger for completeness but excluded from every family's substantive advisory numerator.
_ALREADY_BLOCKING: frozenset[str] = frozenset(
    {"CHK_CLASS_UNDERCLAIM", "CHK_ENTAILED_CLASS_INVALID"}
)

# Every recognized witness code (family codes + already-blocking). Explicit set (not an
# "SC_"/"CHK_" prefix match) so unrelated scope/check codes (SC_SCOPE_REGISTRY_DISAGREE,
# CHK_FLOOR_UNMET, ...) are never miscounted as witness firings.
WITNESS_CODES: frozenset[str] = frozenset(
    _ALREADY_BLOCKING.union(*(f.codes for f in WITNESS_FAMILIES))
)


def witness_counts(codes: Iterable[str]) -> dict[str, int]:
    """Tally only the recognized witness codes in ``codes`` (a run's fired violation codes),
    dropping everything else. Returns ``{code: count}`` (sorted-key insertion for stable
    serialization). Never raises."""
    counts: dict[str, int] = {}
    for c in codes:
        if isinstance(c, str) and c in WITNESS_CODES:
            counts[c] = counts.get(c, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def family_status(family: WitnessFamily, codes: Iterable[str]) -> str:
    """Classify a run FOR THIS FAMILY from the codes it emitted: ``"unavailable"`` (its prober
    was absent/failed), else ``"unresolved"`` (a starved symbol), else ``"unstarved"``.

    IMPORTANT (Codex #80): ``"unstarved"`` means only "emitted no starvation code" — it does
    NOT prove the witness ran. A witness emits a code ONLY on a finding or on starvation; a run
    where it ran and found nothing is INDISTINGUISHABLE from one where it never ran at all (no
    git diff for scope_diff; no ``code_refs`` for cascade/class). So ``unstarved`` conflates
    "ran clean" with "never ran" — it is NOT a trustworthy clean-run denominator. Measuring
    that soundly needs the witness engines to emit POSITIVE attestation ("I ran, examined X"),
    which they do not yet — a follow-up. Independent of the other families."""
    s = {c for c in codes if isinstance(c, str)}
    if s & family.unavailable:
        return "unavailable"
    if s & family.unresolved:
        return "unresolved"
    return "unstarved"


def build_witness_record(run_id: str, codes: Iterable[str], witnessed_at: float) -> dict[str, Any]:
    """Assemble the per-run witness-ledger record from the closure sweep's fired codes. The
    record carries the raw ``counts`` plus a PER-FAMILY breakdown (status + this family's
    substantive advisory count), so a promotion report can compute a per-witness FP
    denominator that one starved witness cannot corrupt (council #80)."""
    codes = list(codes)
    counts = witness_counts(codes)
    families = {
        f.name: {
            "status": family_status(f, codes),
            "substantive": sum(counts.get(c, 0) for c in f.substantive),
        }
        for f in WITNESS_FAMILIES
    }
    return {
        "kind": "uacp.witness_ledger",
        "run_id": run_id,
        "witnessed_at": witnessed_at,
        "counts": counts,
        "families": families,
    }


def _is_safe_run_id(run_id: Any) -> bool:
    """A run_id is safe to embed in a filename iff it is a non-empty str with no path
    separators, no ``..``, and no leading dot (mirrors state_machine's run-id guard)."""
    return (
        isinstance(run_id, str)
        and bool(run_id)
        and "/" not in run_id
        and "\\" not in run_id
        and ".." not in run_id
        and not run_id.startswith(".")
    )


def witness_ledger_path(root: Path, run_id: str) -> Path | None:
    """``<base>/verification/witness-ledgers/<run_id>.yaml`` (config-aware), or None when the
    governed verification dir cannot be resolved. Never raises.

    NB (Codex #80): the ledger lives in a SUBDIRECTORY of ``verification/``, not directly in
    it, ON PURPOSE. The verify-phase evidence invariant globs ``verification/{run_id}*``
    (non-recursive, ``evidence_completeness`` via ``glob_in_workspace``); a ledger written as
    ``verification/{run_id}-witness-ledger.yaml`` would MATCH it and could, on a re-check of a
    finalized run whose real verification package was removed, be the only matching file and
    falsely satisfy the evidence-presence check. Under ``witness-ledgers/`` it does not match
    that glob, so this gate-owned observer never masks missing verification evidence.

    SECURITY (Codex #80): reject an unsafe ``run_id`` (path separators / ``..`` / leading dot)
    BEFORE building the filename. The ledger writer runs best-effort inside ``validate_closure``
    *before* the invalid-run decision is returned, so an id like ``'../../state/run-registry'``
    would otherwise resolve the write OUT of the sub-namespace and overwrite governed state.
    An unsafe id yields None -> the write is skipped (the closure blocks the run anyway)."""
    if not _is_safe_run_id(run_id):
        return None
    try:
        vdir = dir_for(Path(root).resolve(), "verification")
    except Exception:
        return None
    return vdir / "witness-ledgers" / f"{run_id}.yaml"


def _no_symlinked_component(path: Path, root: Path) -> bool:
    """True iff no path component from the workspace ROOT down to ``path`` is a symlink and the
    target itself is not a symlink — parity with the governed writers' guard
    (``filesystem._resolve_uacp_path``). A symlinked ``verification/witness-ledgers`` dir (e.g.
    pointing at ``state/runs``) would otherwise let the atomic ``os.replace`` write THROUGH the
    link and clobber governed state (Codex #80). Fail-closed: any error / out-of-root path ->
    False (skip the best-effort write)."""
    try:
        root_resolved = Path(root).resolve()
        rel = path.relative_to(root_resolved)
    except Exception:
        return False
    current = root_resolved
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            return False
    return not (path.exists() and path.is_symlink())


def write_witness_ledger(root: Path, run_id: str, record: dict[str, Any]) -> bool:
    """Write the witness-ledger record ATOMICALLY (same-dir temp + fsync + os.replace), so a
    reader never observes a half-written record and a crash cannot leave a partial file
    (last-write-wins across retried closures). On ANY failure the temp is cleaned and
    ``False`` is returned. Creates the verification dir if needed. Never raises."""
    path = witness_ledger_path(root, run_id)
    if path is None:
        return False
    # Fail closed on symlinked path components BEFORE creating/replacing anything: a symlinked
    # ledger directory could redirect the write onto governed state (Codex #80), the same class
    # the _is_safe_run_id guard blocks for the filename.
    if not _no_symlinked_component(path, root):
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = yaml.safe_dump(record, sort_keys=False)
    except Exception:
        return False

    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)  # atomic within the same directory
        return True
    except Exception:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                # best-effort temp cleanup; a lingering temp is harmless (never the target)
                pass
        return False


def load_witness_ledger(root: Path, run_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load the witness-ledger record. ``(record, None)`` when present + well-formed,
    ``(None, None)`` when ABSENT, ``(None, error)`` when present but unreadable / not a
    mapping. Never raises."""
    path = witness_ledger_path(root, run_id)
    if path is None or not path.exists():
        return None, None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"witness ledger unreadable: {type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "witness ledger is not a mapping"
    return data, None

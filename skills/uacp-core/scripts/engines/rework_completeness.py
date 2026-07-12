"""Rework-completeness validator for UACP runs (codes prefixed ``RW_``).

Enforces the closure half of the standard-track rework loop (#109 / #135). A rework
run carries its parent's VERIFY findings forward on the manifest's ``carried_findings``
map — but recording them is not addressing them. This engine makes closure fail-closed
on a rework that IGNORED a carried finding: at RESOLVE, every carried finding must be
DISCHARGED by an explicit disposition, or the run cannot close.

What "discharged" means — the existing LN grammar, not a new one
================================================================

The disposition is the ``handled_findings_chain`` already defined in
``config/phase-transitions.yaml`` (the transition-evidence / verify LN mechanism): a
list of entries, each naming the finding it handles and a ``handling_classification``
from the closed enum ``remediated | expanded | justified | deferred | accepted_warning
| rejected_with_reason``. A rework discharges a carried finding by recording ONE such
entry for it in any of its own registered VERIFY / closure artifacts.

* Correlation — an entry addresses a carried finding when its ``original_finding_id``
  equals the carried manifest KEY (e.g. ``assessment``) OR its ``original_artifact_path``
  equals the carried PARENT-RELATIVE path (the value in ``carried_findings``). Either is
  accepted, because the surfaced briefing (#135 P1) gives the agent both.
* Actually-fixed vs accepted-exception — ``remediated`` / ``expanded`` are the "the fix
  addressed it" classes. The remaining classes (``justified`` / ``deferred`` /
  ``accepted_warning`` / ``rejected_with_reason``) are the "not fixed, but explicitly
  accounted for" accepted-exceptions; each MUST carry a rationale (``residual_risk``) or
  an exception artifact (``accepted_exception_artifact``) — an empty ``deferred`` is not
  an explicit accepted-exception, it is an ignored finding wearing a label.

Codes
=====

* ``RW_CARRIED_FINDING_UNADDRESSED`` (block) — a carried finding has NO disposition
  entry in any of the rework's registered VERIFY/closure artifacts (or only entries with
  an unrecognized ``handling_classification``, which are not valid handling decisions).
* ``RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE`` (block) — a carried finding is disposed
  with an accepted-exception class but carries neither ``residual_risk`` nor
  ``accepted_exception_artifact``.
* ``RW_REWORK_DEPTH_ESCALATION`` (warn) — the run's ``rework_depth`` is at/above the
  configured ``[heartgate] max_rework_depth`` (#135 P4). ESCALATES as a warning, never a
  hard block — a long findings->fix chain is a signal to a human, not an automatic stop.

Scope / honest limits
=====================

* **No-op for non-rework runs.** A run with an empty ``carried_findings`` and
  ``rework_depth == 0`` returns ``[]`` — the common path is untouched.
* **The UNADDRESSED / EXCEPTION checks are a CLOSURE obligation** — they fire only once
  the run is ``status == 'resolved'`` (the closure gate finalizes first, then sweeps), so
  an in-flight rework that has not yet authored its dispositions is not false-flagged.
  The depth escalation is pure visibility and fires whenever it is a rework run.
* **Structural completeness only.** A disposition is checked for PRESENCE + a valid class
  + (for exceptions) a non-empty rationale — NOT for whether the fix or the justification
  is semantically adequate. Adequacy is a council concern (matching
  ``deferral_completeness``'s documented limit).

Architecture: PURE of filesystem I/O — all disk reads go through :mod:`engines.io`
read-models; this module never raises (every failure becomes a :class:`Violation` or a
no-op). An empty result list means "clean".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import get_config
from engines.base import ENGINES, Violation
from engines.io import load_artifact, load_manifest
from engines.io.loaders import ManifestDoc

# The full LN handling_classification enum (config/phase-transitions.yaml
# handled_findings_chain.handling_classification). A class outside this set is not a
# recognized handling decision and does not discharge a finding.
_VALID_CLASSES: frozenset[str] = frozenset(
    {"remediated", "expanded", "justified", "deferred", "accepted_warning", "rejected_with_reason"}
)
# The "not fixed, but explicitly accepted" classes — each needs a rationale/exception
# artifact. ``remediated`` / ``expanded`` are the "actually addressed" classes and need
# no extra field (their evidence is the fix itself, checked by execute/verify coverage).
_ACCEPTED_EXCEPTION_CLASSES: frozenset[str] = _VALID_CLASSES - {"remediated", "expanded"}

# Where a rework records its dispositions: its own closure/lessons artifact plus its own
# VERIFY finding artifacts (the same keys it carried from the parent — a rework re-authors
# its own verify evidence). Scanned for a ``handled_findings_chain`` list.
_CLOSURE_ARTIFACT_KEYS: tuple[str, ...] = ("lessons", "resolution", "learning")

_DEFAULT_MAX_REWORK_DEPTH = 5


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _max_rework_depth(root: Path) -> int:
    """The operator-tunable ``[heartgate] max_rework_depth`` (code default when absent).

    Honors an explicit ``0`` (escalate on every rework) — the fallback is for an
    absent / null / non-int / negative value only (council #135 D2). ``bool`` is
    rejected explicitly (it is an ``int`` subclass, so ``max_rework_depth = true`` would
    otherwise resolve to 1)."""
    try:
        cfg = get_config(root).model_dump()
        raw = (cfg.get("heartgate") or {}).get("max_rework_depth")
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            return _DEFAULT_MAX_REWORK_DEPTH
        return raw
    except Exception:
        return _DEFAULT_MAX_REWORK_DEPTH


def _str_field(entry: dict[str, Any], key: str) -> str:
    v = entry.get(key)
    return v.strip() if isinstance(v, str) else ""


def _collect_dispositions(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Every ``handled_findings_chain`` entry across the rework's own registered
    VERIFY / closure artifacts. Tolerant: a missing / garbled / non-list artifact
    contributes nothing (a genuinely absent disposition is caught as UNADDRESSED)."""
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return []

    # Import here (not at module load) to avoid any import-order coupling to the schema
    # engine; the derivation is cheap and cached upstream.
    from engines.domain.schema import verify_finding_artifact_keys

    source_keys = set(_CLOSURE_ARTIFACT_KEYS) | set(verify_finding_artifact_keys())

    entries: list[dict[str, Any]] = []
    seen_rels: set[str] = set()
    for key, rel in artifacts.items():
        # keys can carry a ':seq=N' composite suffix — match on the base key. Guard the key
        # type too (council #135 D3): a non-str manifest key would raise on .split and break
        # the module's never-raises contract — skip it (the value guard already exists).
        if not isinstance(key, str) or not isinstance(rel, str) or not rel.strip():
            continue
        base = key.split(":", 1)[0]
        if base not in source_keys:
            continue
        if rel in seen_rels:
            continue
        seen_rels.add(rel)
        loaded = load_artifact(root, rel)
        if loaded.error is not None or not isinstance(loaded.value, dict):
            continue
        chain = loaded.value.get("handled_findings_chain")
        if isinstance(chain, list):
            entries.extend(e for e in chain if isinstance(e, dict))
    return entries


def _entry_addresses(entry: dict[str, Any], carried_key: str, carried_path: str) -> bool:
    """True iff the disposition entry references this carried finding with a RECOGNIZED
    handling class. Correlation is CONJUNCTIVE over the fields the entry provides: a field
    it declares (original_finding_id / original_artifact_path) MUST match this finding; a
    field it omits is a wildcard; and it must declare at least one. A disjunctive match
    would let one malformed entry whose id points at finding A and whose path points at
    finding B discharge BOTH (gemini #135 P1) — an entry that names two different findings
    matches NEITHER."""
    if _str_field(entry, "handling_classification") not in _VALID_CLASSES:
        return False
    fid = _str_field(entry, "original_finding_id")
    fpath = _str_field(entry, "original_artifact_path")
    if not fid and not fpath:
        return False  # a disposition that names no finding cannot discharge one
    id_ok = (fid == carried_key) if fid else True
    path_ok = (bool(carried_path) and fpath == carried_path) if fpath else True
    return id_ok and path_ok


def validate_rework_completeness(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that a rework run discharged every carried finding, and surface a long
    rework chain as a warning. Returns a list of Violation (empty == clean). Never raises.
    """
    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("RW0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("RW0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    loaded = load_manifest(root, run_id)
    if loaded.error is not None:
        return [_v("RW0_MANIFEST_MISSING", f"run manifest could not be loaded: {loaded.error}")]
    doc: ManifestDoc = loaded.value
    manifest = doc.raw

    carried = manifest.get("carried_findings")
    carried = carried if isinstance(carried, dict) else {}
    try:
        depth = int(manifest.get("rework_depth") or 0)
    except (TypeError, ValueError):
        depth = 0

    # No-op for the common (non-rework) path — never touch a plain run.
    if not carried and depth == 0:
        return []

    violations: list[Violation] = []

    # Depth escalation (P4): a long findings->fix chain warns, never blocks. Pure
    # visibility, so it fires regardless of status.
    max_depth = _max_rework_depth(root)
    if depth >= max_depth:
        violations.append(
            _v(
                "RW_REWORK_DEPTH_ESCALATION",
                f"rework chain depth {depth} has reached the escalation threshold "
                f"(max_rework_depth={max_depth}) — a human should review whether the "
                f"findings->fix loop is converging",
                severity="warn",
                rework_depth=depth,
                max_rework_depth=max_depth,
            )
        )

    # The carried-findings discharge check is a CLOSURE obligation: only enforce once the
    # run is closing, so an in-flight rework mid-authoring is not false-flagged. Keyed off
    # EITHER status=="resolved" OR finalized_at set (council #135 D4): validate_closure's
    # documented precondition is finalized_at, and handle_finalize sets both before the
    # sweep — accepting either means a future non-finalize closure path (or the mooted
    # uacp_validate_closure tool run on a finalized run) cannot silently bypass the check by
    # carrying a status token other than the literal "resolved".
    if carried and (manifest.get("status") == "resolved" or manifest.get("finalized_at")):
        dispositions = _collect_dispositions(root, manifest)
        for carried_key, carried_path in carried.items():
            path_str = carried_path.strip() if isinstance(carried_path, str) else ""
            matches = [e for e in dispositions if _entry_addresses(e, carried_key, path_str)]
            if not matches:
                violations.append(
                    _v(
                        "RW_CARRIED_FINDING_UNADDRESSED",
                        f"carried finding '{carried_key}' (from the reworked parent) has no "
                        f"disposition in the rework's verify/closure artifacts — a rework may "
                        f"not close having ignored a carried finding; record a "
                        f"handled_findings_chain entry (remediated/justified/deferred/...) for it",
                        carried_finding=carried_key,
                        carried_path=path_str,
                    )
                )
                continue
            # Discharged — but an accepted-exception class must carry a rationale.
            if all(
                _str_field(e, "handling_classification") in _ACCEPTED_EXCEPTION_CLASSES
                and not _str_field(e, "residual_risk")
                and not _str_field(e, "accepted_exception_artifact")
                for e in matches
            ):
                classes = sorted({_str_field(e, "handling_classification") for e in matches})
                violations.append(
                    _v(
                        "RW_CARRIED_FINDING_EXCEPTION_INCOMPLETE",
                        f"carried finding '{carried_key}' is disposed as accepted-exception(s) "
                        f"{classes} but carries neither a 'residual_risk' rationale nor an "
                        f"'accepted_exception_artifact' — an explicit accepted-exception must "
                        f"state what is being accepted",
                        carried_finding=carried_key,
                        handling_classifications=classes,
                    )
                )

    return violations


# Register this engine (guard against double-registration under alias imports).
if not any(name == "rework_completeness" for name, _ in ENGINES):
    ENGINES.append(("rework_completeness", validate_rework_completeness))

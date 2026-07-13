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
* ``RW_CARRIED_FINDING_REMEDIATION_UNEVIDENCED`` (block) — a carried finding is disposed
  as a remediation (``remediated`` / ``expanded``) but no matching entry points to its fix
  via ``handling_artifact_path``; a claimed fix must link its evidence.
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
* **The discharge checks are a CLOSURE obligation** — they fire only once the run is
  closing (``status == 'resolved'`` OR ``finalized_at`` set; the closure gate finalizes
  first, then sweeps), so an in-flight rework that has not yet authored its dispositions is
  not false-flagged. The depth escalation is pure visibility and fires whenever it is a
  rework run.
* **Structural completeness only.** A disposition is checked for PRESENCE + a valid class +
  its class-required evidence FIELD (a remediation's ``handling_artifact_path`` fix pointer;
  an accepted-exception's ``residual_risk`` / ``accepted_exception_artifact``) — NOT for
  whether the fix or the justification is semantically adequate, and the linked path is not
  resolved to a real checkpoint. Adequacy is a council concern (matching
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
# The "actually addressed" classes: each must POINT TO its fix via handling_artifact_path
# (the LN grammar's fix-evidence pointer; the execute skill requires it). A bare
# ``remediated`` with no linked fix is a label, not a discharge (Codex #135).
_REMEDIATION_CLASSES: frozenset[str] = frozenset({"remediated", "expanded"})
# The "not fixed, but explicitly accepted" classes — each needs a residual_risk rationale or
# an accepted_exception_artifact.
_ACCEPTED_EXCEPTION_CLASSES: frozenset[str] = _VALID_CLASSES - _REMEDIATION_CLASSES

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
    """Every ``handled_findings_chain`` entry across ALL of the rework's OWN registered
    artifacts. A rework may record its dispositions in any of its governed evidence — its
    VERIFY package/readiness/assessment OR its RESOLVE closure/lessons artifact — and each
    lands under a different manifest key depending on the writer (a governed
    ``uacp_entity_write`` key = ``kind.removeprefix("uacp.")`` vs a shorter manual alias).
    Curating a source-key list repeatedly missed a valid registration key (Codex #135: first
    the governed VERIFY keys, then the RESOLVE ``resolve_package`` / ``resolve_closure`` keys),
    so scan EVERY registered artifact for the chain instead — they are all the rework's own
    watermarked evidence, and ``handled_findings_chain`` only appears where a disposition was
    authored. Tolerant: a missing / garbled / non-list artifact contributes nothing (a
    genuinely absent disposition is caught as UNADDRESSED)."""
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return []

    entries: list[dict[str, Any]] = []
    seen_rels: set[str] = set()
    for rel in artifacts.values():
        if not isinstance(rel, str) or not rel.strip() or rel in seen_rels:
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


def _disposition_complete(entry: dict[str, Any]) -> bool:
    """True iff the disposition carries the evidence its class demands (structural, not
    adequacy): a remediation (remediated / expanded) must point to the fix via
    ``handling_artifact_path``; an accepted-exception must carry a ``residual_risk`` rationale
    or an ``accepted_exception_artifact``. A bare ``{handling_classification: remediated}`` with
    no fix pointer is a label, not a discharge (Codex #135)."""
    cls = _str_field(entry, "handling_classification")
    if cls in _REMEDIATION_CLASSES:
        return bool(_str_field(entry, "handling_artifact_path"))
    if cls in _ACCEPTED_EXCEPTION_CLASSES:
        return bool(
            _str_field(entry, "residual_risk") or _str_field(entry, "accepted_exception_artifact")
        )
    return False  # unreachable: _entry_addresses already filtered to _VALID_CLASSES


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
            # A finding is discharged when at least one matching disposition is COMPLETE:
            # a remediation must point to the fix, an accepted-exception must state what is
            # being accepted (structural presence — adequacy stays a council concern). If none
            # is complete, report the failure by what the incomplete matches attempted.
            if any(_disposition_complete(e) for e in matches):
                continue
            classes = sorted({_str_field(e, "handling_classification") for e in matches})
            if any(
                _str_field(e, "handling_classification") in _REMEDIATION_CLASSES for e in matches
            ):
                violations.append(
                    _v(
                        "RW_CARRIED_FINDING_REMEDIATION_UNEVIDENCED",
                        f"carried finding '{carried_key}' is disposed as {classes} (a claimed "
                        f"remediation) but no matching entry points to its fix via "
                        f"'handling_artifact_path' — a remediation must link its fix evidence",
                        carried_finding=carried_key,
                        handling_classifications=classes,
                    )
                )
            else:
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

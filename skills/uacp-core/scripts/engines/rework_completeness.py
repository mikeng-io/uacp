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
* ``RW_CARRIED_FINDING_DISPOSITION_MALFORMED`` (block) — a carried finding has a
  class-evidence-complete disposition (its fix pointer / accepted-exception rationale is
  present) but the entry is NOT a well-formed canonical ``handled_findings_chain`` item: a
  required base field is missing/empty or an enum is invalid. Closure must fail-CLOSED on a
  structurally-invalid disposition, not accept the partial one (#149).
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
  an accepted-exception's ``residual_risk`` / ``accepted_exception_artifact``) AND for the
  canonical ``handled_findings_chain`` well-formedness FLOOR — which mirrors the FULL
  ``validate_handled_findings_chain`` per-item grammar (source of truth): the base fields in
  :data:`_CANONICAL_DISPOSITION_REQUIRED_FIELDS` present/non-empty, the enum checks, AND the
  CONDITIONAL followup / carry-forward per-item rules (followup_depth bound; a HARD_FOLLOWUP
  handling opening a tracked followup or carrying an exception artifact; an opened followup
  linking its council synthesis; a CARRY_FORWARD handling naming its next_phase_obligation +
  exception artifact; a blocker/invariant_failure not carried forward without a hard-block
  validation). What is NOT checked: whether the fix or the justification is semantically
  adequate, and the linked path is not resolved to a real checkpoint. Adequacy is a council
  concern (matching ``deferral_completeness``'s documented limit).

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

# The canonical handled_findings_chain ITEM grammar — the well-formedness FLOOR a disposition
# must clear to discharge a carried finding, on top of its class-required evidence. Source of
# truth: ``scripts/validate_uacp_artifacts.py`` ``validate_handled_findings_chain`` (which BLOCKs
# on any of these missing/empty) and ``config/phase-transitions.yaml`` handled_findings_chain
# item schema. Each field must be PRESENT and NON-EMPTY under the validator's exact emptiness
# test ``item.get(field) in (None, "")`` — note ``False`` / ``0`` are PRESENT (valid), only
# ``None`` / ``""`` fail. A disposition carrying only a handling_classification + its class-
# evidence field (e.g. handling_artifact_path) is class-evidence-complete but NOT canonically
# well-formed, so it cannot close a rework (fail-CLOSED, #149).
_CANONICAL_DISPOSITION_REQUIRED_FIELDS: tuple[str, ...] = (
    "original_finding_id",
    "finding_classification",
    "handling_classification",
    "handling_artifact_path",
    "followup_required",
    "owner",
    "residual_risk",
    "heartgate_validation",
)
# Enum members MIRRORED from ``scripts/validate_uacp_artifacts.py``
# (``VALID_FINDING_CLASSIFICATIONS`` / ``VALID_HEARTGATE_VALIDATIONS``) and
# ``config/phase-transitions.yaml`` — kept in sync with those constants. The handling_classification
# enum is already ``_VALID_CLASSES`` above.
_VALID_FINDING_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"blocker", "concern", "invariant_failure", "negative_finding", "material_warning"}
)
_VALID_HEARTGATE_VALIDATIONS: frozenset[str] = frozenset({"pass", "warn", "block"})

# The handling_classification partition the canonical grammar's CONDITIONAL per-item rules
# key off (MIRRORED from ``scripts/validate_uacp_artifacts.py`` — HARD_FOLLOWUP_HANDLINGS /
# CARRY_FORWARD_HANDLINGS / MAX_FOLLOWUP_DEPTH_DEFAULT — the source of truth; kept in sync):
# * HARD_FOLLOWUP handlings ("the fix / justification stands") must EITHER open a tracked
#   followup (followup_required=true) OR carry an accepted_exception_artifact.
# * CARRY_FORWARD handlings ("not fixed, deferred/accepted onward") must name the obligation
#   they push to the next phase (owner / residual_risk / next_phase_obligation), and the
#   explicitly-accepted ones (accepted_warning / rejected_with_reason) an exception artifact.
# NB these are DISTINCT from ``_REMEDIATION_CLASSES`` / ``_ACCEPTED_EXCEPTION_CLASSES`` above
# (which partition on class-EVIDENCE): ``justified`` is a HARD_FOLLOWUP here but an
# accepted-exception for class-evidence; ``deferred`` is CARRY_FORWARD here but likewise an
# accepted-exception for class-evidence. The two partitions answer different questions.
_HARD_FOLLOWUP_HANDLINGS: frozenset[str] = frozenset({"remediated", "expanded", "justified"})
_CARRY_FORWARD_HANDLINGS: frozenset[str] = frozenset(
    {"deferred", "accepted_warning", "rejected_with_reason"}
)
_MAX_FOLLOWUP_DEPTH_DEFAULT = 1

# A rework discharges a carried finding ONLY in its VERIFY / closure evidence — a disposition
# is not evidence until the run has actually reached verify/resolve. The lifecycle artifact
# schemas each pin a ``phase`` const (propose/plan/execute/verify/resolve); dispositions are
# honored only from artifacts declaring one of these phases, so a syntactically-valid
# handled_findings_chain planted in an earlier-phase (proposal/plan/execute) artifact — the
# schemas are open to extra fields — cannot discharge a carried finding before the required
# verify/closure evidence exists (Codex #135).
_DISPOSITION_PHASES: frozenset[str] = frozenset({"verify", "resolve"})

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
    so scan EVERY registered artifact for the chain instead of a fragile key list — BUT only
    honor those declaring a VERIFY / RESOLVE ``phase`` (:data:`_DISPOSITION_PHASES`), so a chain
    in an earlier-phase artifact cannot discharge a finding before verify/closure evidence
    exists (Codex #135). Tolerant: a missing / garbled / non-list / wrong-phase artifact
    contributes nothing (a genuinely absent disposition is caught as UNADDRESSED)."""
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
        # Honor dispositions ONLY from VERIFY / closure artifacts (the contract): a chain in an
        # earlier-phase artifact (proposal/plan/execute) must not discharge a carried finding
        # before verify/closure evidence exists (Codex #135). Gate on the artifact's declared
        # phase — a phase-less / non-verify/resolve artifact contributes nothing.
        if loaded.value.get("phase") not in _DISPOSITION_PHASES:
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


def _disposition_defects(entry: dict[str, Any]) -> list[str]:
    """The human-readable ways ``entry`` violates the canonical handled_findings_chain item
    grammar, MIRRORING ``validate_handled_findings_chain`` in ``scripts/validate_uacp_artifacts.py``
    (source of truth) in FULL: the base fields (:data:`_CANONICAL_DISPOSITION_REQUIRED_FIELDS`),
    the enum checks, AND the conditional followup / carry-forward per-item rules. Each defect is a
    short string (``missing <field>`` / ``invalid <field>`` / the rule's requirement). An empty list
    == canonically well-formed.

    Truthiness is matched to the validator EXACTLY: the base-field emptiness test is
    ``entry.get(field) in (None, "")`` (so ``False`` / ``0`` count as PRESENT); the conditional
    rules use ``not entry.get(field)`` (falsy: None/""/False/0/[]) for
    next_phase_obligation / accepted_exception_artifact / followup_council_synthesis_artifact, and
    the strict ``is True`` / ``is not True`` for followup_required. Enum defects are only reported
    when the value is present (an empty enum field is ``missing``, not ``invalid``)."""
    defects: list[str] = []
    for field in _CANONICAL_DISPOSITION_REQUIRED_FIELDS:
        if entry.get(field) in (None, ""):
            defects.append(f"missing {field}")
    finding = entry.get("finding_classification")
    if finding not in (None, "") and finding not in _VALID_FINDING_CLASSIFICATIONS:
        defects.append(f"invalid finding_classification {finding!r}")
    handling = entry.get("handling_classification")
    if handling not in (None, "") and handling not in _VALID_CLASSES:
        defects.append(f"invalid handling_classification {handling!r}")
    validation = entry.get("heartgate_validation")
    if validation not in (None, "") and validation not in _VALID_HEARTGATE_VALIDATIONS:
        defects.append(f"invalid heartgate_validation {validation!r}")

    # Rule 1 — followup_depth (optional, default 0): int-convertible and within the max.
    depth = entry.get("followup_depth", 0)
    try:
        depth_int = int(depth)
    except Exception:
        defects.append("followup_depth must be integer")
        depth_int = 0
    if depth_int > _MAX_FOLLOWUP_DEPTH_DEFAULT:
        defects.append(f"followup_depth exceeds max {_MAX_FOLLOWUP_DEPTH_DEFAULT}")

    # Rule 2 — a HARD_FOLLOWUP handling must open a tracked followup OR carry an exception artifact.
    if (
        handling in _HARD_FOLLOWUP_HANDLINGS
        and entry.get("followup_required") is not True
        and not entry.get("accepted_exception_artifact")
    ):
        defects.append("requires followup_required=true or accepted_exception_artifact")

    # Rule 3 — an opened followup must link its council synthesis artifact.
    if entry.get("followup_required") is True and not entry.get(
        "followup_council_synthesis_artifact"
    ):
        defects.append("followup_required=true requires followup_council_synthesis_artifact")

    # Rule 4 — a CARRY_FORWARD handling must name the obligation it pushes forward (owner /
    # residual_risk are already base-8; next_phase_obligation is NOT — the validator re-checks
    # all three with ``not entry.get(f)``, a superset of the base emptiness test, so mirror that
    # while not double-reporting a field the base loop already flagged).
    if handling in _CARRY_FORWARD_HANDLINGS:
        for field in ("owner", "residual_risk", "next_phase_obligation"):
            if not entry.get(field) and f"missing {field}" not in defects:
                defects.append(f"missing {field}")
        if handling in {"accepted_warning", "rejected_with_reason"} and not entry.get(
            "accepted_exception_artifact"
        ):
            defects.append("requires accepted_exception_artifact")

    # Rule 5 — a blocker / invariant_failure finding cannot be carried forward unless the
    # heartgate validation is a hard block.
    if (
        finding in {"blocker", "invariant_failure"}
        and handling in _CARRY_FORWARD_HANDLINGS
        and validation != "block"
    ):
        defects.append("cannot carry forward without heartgate_validation=block")

    return defects


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
            # A finding is discharged when at least one matching disposition is BOTH
            # class-evidence-complete (its class's fix pointer / accepted-exception rationale)
            # AND canonically well-formed (a complete handled_findings_chain item — every base
            # field present + valid enums). Class-evidence alone is not enough: a rework may not
            # close on a structurally-INVALID disposition (#149 fail-CLOSED).
            if any(_disposition_complete(e) and not _disposition_defects(e) for e in matches):
                continue
            complete_matches = [e for e in matches if _disposition_complete(e)]
            if not complete_matches:
                # No match carries even its class-required evidence — report by what the
                # incomplete matches attempted (the existing two-way split, unchanged).
                classes = sorted({_str_field(e, "handling_classification") for e in matches})
                if any(
                    _str_field(e, "handling_classification") in _REMEDIATION_CLASSES
                    for e in matches
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
                continue
            # Some match carries its class-evidence but is not a well-formed canonical item — the
            # discharge floor is not met. Name the MINIMAL defect set (the class-evidence-complete
            # match closest to well-formed) so the author sees the smallest fix.
            best = min(complete_matches, key=lambda e: len(_disposition_defects(e)))
            defects = _disposition_defects(best)
            violations.append(
                _v(
                    "RW_CARRIED_FINDING_DISPOSITION_MALFORMED",
                    f"carried finding '{carried_key}' has a class-evidence-complete disposition "
                    f"that is not a well-formed handled_findings_chain item ({', '.join(defects)}) "
                    f"— a carried-finding disposition must be a complete canonical item (all of "
                    f"{list(_CANONICAL_DISPOSITION_REQUIRED_FIELDS)} present with valid enums)",
                    carried_finding=carried_key,
                    defects=defects,
                )
            )

    return violations


# Register this engine (guard against double-registration under alias imports).
if not any(name == "rework_completeness" for name, _ in ENGINES):
    ENGINES.append(("rework_completeness", validate_rework_completeness))

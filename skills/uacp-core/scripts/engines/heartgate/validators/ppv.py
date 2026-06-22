"""Phase Intent Verification (PIV) ledger-record gate (A3.4 extraction).

Carved out of the Heartgate god-class (design/graph-engine nodes 30/31, seam #7)
as free functions taking the gate instance (hg); the hub keeps thin delegating
methods. Each body is AST-identical to the original method (only self -> hg).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .helpers import _is_safe_run_id

if TYPE_CHECKING:
    from ..heartgate import Heartgate


def ppv_rule(hg: Heartgate) -> Mapping[str, Any]:
    """Resolve the ppv_rule.

    Slice 4b T4c-2: the rule grammar (ledger_required, the ppv_* check ids,
    ledger_required_fields, max_attempts, second_failure_action) is codified
    in engines.domain.gate_rules. The block is read from the loaded
    phase-transitions config WHEN PRESENT (production behavior, unchanged);
    when ABSENT it falls back to the code default whose ``ledger_required``
    is True (enforce-by-default / fail-closed: a PPV pass record is required
    on every transition). No operator-tunable knob this wave.

    A test fixture may opt OUT by supplying ``ppv_rule: {ledger_required:
    false}``: present-with-falsy-ledger_required is read as the loaded value,
    so the reader's ``not ppv_rule.get("ledger_required")`` short-circuits the
    gate exactly as the pre-T4c-2 absent block did.
    """
    if "ppv_rule" in hg.config:
        return hg.config.get("ppv_rule") or {}
    from engines.domain.gate_rules import ppv_rule_default

    return ppv_rule_default()


def validate_ppv_record(hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]) -> None:
    """Phase 1 / Item 1.4: require a PPV pass record in the ledger before
    Heartgate accepts a transition for which ppv_rule applies.

    (PPV = the legacy post-phase-verification ledger rule; distinct from the
    newer Phase Intent Verification contract.)

    Tech-F1 remediation: sanitize run_id before constructing the ledger
    path (reject path-traversal characters and resolve under
    state/gate-ledger/ only). Skeptic F5 remediation: tolerate malformed
    ppv_rule fields with explicit blockers instead of crashing.

    Global review R1 (SKEP-G-002): generalize the per-check pass
    evidence pattern Phase 3 R1 introduced for PLAN_VALIDATION.
    ppv_rule declares `ledger_required_fields: [ppv_attempt, result,
    checks]`; when present, the kernel verifies each declared
    ppv_check_id appears in the ledger record's `checks` list AND
    has explicit per-check pass evidence (mapping-form or sibling
    `check_results: {ppv_id: pass}`).
    """
    ppv_rule = hg._ppv_rule()
    if not isinstance(ppv_rule, Mapping) or not ppv_rule.get("ledger_required"):
        return
    run_id = str(artifact.get("run_id") or "")
    if not run_id:
        blockers.append("ppv_rule requires run_id to verify ledger record")
        return
    if not _is_safe_run_id(run_id):
        blockers.append("ppv_rule: unsafe run_id rejected for ledger lookup")
        return
    ledger_path = hg.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
    if not ledger_path.exists():
        blockers.append(
            f"ppv_rule unmet: no gate ledger at {ledger_path.relative_to(hg.governed_root)}"
        )
        return
    from_phase = str(artifact.get("from_phase") or "")
    # Precompute declared ppv_ids when ppv_rule.checks is present.
    declared_check_ids: set[str] = set()
    for c in ppv_rule.get("checks") or []:
        if isinstance(c, Mapping):
            cid = str(c.get("id") or "").strip()
            if cid:
                declared_check_ids.add(cid)
    ledger_required_fields = [
        str(f) for f in (ppv_rule.get("ledger_required_fields") or []) if isinstance(f, str)
    ]
    passing_attempts: list[int] = []
    failing_attempts: list[int] = []
    passing_record_defects: list[str] = []
    try:
        for lineno, raw_line in enumerate(
            ledger_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as exc:
                # Phase 3 (pc_p2_minor): fail-closed on corrupted ledger.
                blockers.append(
                    f"ppv_rule: gate ledger line {lineno} unparseable: {type(exc).__name__}: {exc}"
                )
                return
            if str(rec.get("gate") or "") != "PPV":
                continue
            if from_phase and str(rec.get("phase") or "") != from_phase:
                continue
            try:
                attempt = int(rec.get("ppv_attempt") or 0)
            except (TypeError, ValueError):
                blockers.append(f"ppv_rule: gate ledger line {lineno} has non-integer ppv_attempt")
                return
            result = str(rec.get("result") or "")
            if result == "pass":
                # SKEP-G-002: when ppv_rule declares checks + required fields,
                # this pass record must carry per-check evidence. If it doesn't,
                # it's treated as a per-record defect and not counted as
                # passing (multi-record DoS resistance mirrors PLAN_VALIDATION).
                body: Mapping[str, Any] = (
                    rec["record"] if isinstance(rec.get("record"), Mapping) else rec
                )
                defect: str | None = None
                if ledger_required_fields:
                    missing = [f for f in ledger_required_fields if f not in body and f not in rec]
                    if missing:
                        defect = f"line {lineno}: missing required fields {missing}"
                if defect is None and declared_check_ids:
                    checks_in_rec = (
                        body.get("checks")
                        if isinstance(body.get("checks"), list)
                        else rec.get("checks")
                    )
                    if not isinstance(checks_in_rec, list):
                        defect = (
                            f"line {lineno}: 'checks' must be a list "
                            f"(got {type(checks_in_rec).__name__})"
                        )
                    else:
                        sibling = (
                            body.get("check_results")
                            if isinstance(body.get("check_results"), Mapping)
                            else rec.get("check_results")
                        )
                        recorded_ids: set[str] = set()
                        ids_with_pass: set[str] = set()
                        for entry in checks_in_rec:
                            if isinstance(entry, str):
                                cid = entry.strip()
                                if cid:
                                    recorded_ids.add(cid)
                                    if (
                                        isinstance(sibling, Mapping)
                                        and str(sibling.get(cid) or "") == "pass"
                                    ):
                                        ids_with_pass.add(cid)
                            elif isinstance(entry, Mapping):
                                cid = str(entry.get("id") or "").strip()
                                if cid:
                                    recorded_ids.add(cid)
                                    if str(entry.get("result") or "") == "pass":
                                        ids_with_pass.add(cid)
                        missing_ids = declared_check_ids - recorded_ids
                        extra_ids = recorded_ids - declared_check_ids
                        unproven = declared_check_ids - ids_with_pass
                        if missing_ids:
                            defect = (
                                f"line {lineno}: missing required ppv_ids {sorted(missing_ids)}"
                            )
                        elif extra_ids:
                            defect = f"line {lineno}: unknown ppv_ids {sorted(extra_ids)}"
                        elif unproven:
                            defect = (
                                f"line {lineno}: missing per-check pass evidence "
                                f"for {sorted(unproven)}"
                            )
                if defect:
                    passing_record_defects.append(defect)
                    continue
                passing_attempts.append(attempt)
            elif result in {"warn", "block", "fail"}:
                failing_attempts.append(attempt)
    except Exception as exc:
        blockers.append(f"ppv_rule ledger read failed: {type(exc).__name__}: {exc}")
        return
    raw_max = ppv_rule.get("max_attempts")
    if raw_max is None:
        raw_max = 2
    try:
        max_attempts = int(raw_max)
    except (TypeError, ValueError):
        blockers.append("ppv_rule.max_attempts must be a positive integer")
        return
    if max_attempts <= 0:
        blockers.append("ppv_rule.max_attempts must be >= 1")
        return
    # Skeptic F2 remediation: second-failure block is the default action.
    # Only an explicit known relaxation value bypasses it.
    action = str(ppv_rule.get("second_failure_action") or "block_unconditional")
    if action not in {"block_unconditional", "warn"}:
        blockers.append(f"ppv_rule.second_failure_action unknown value '{action}'")
        return
    if len(failing_attempts) >= max_attempts and action == "block_unconditional":
        blockers.append(
            f"ppv_rule: {len(failing_attempts)} failed PPV attempts for phase "
            f"'{from_phase}' — second-failure unconditional block"
        )
        return
    if not passing_attempts:
        detail = (
            f" (per-record defects: {passing_record_defects})" if passing_record_defects else ""
        )
        blockers.append(
            f"ppv_rule unmet: no PPV pass record in ledger for phase '{from_phase}'{detail}"
        )

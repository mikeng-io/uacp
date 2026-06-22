"""PLAN_VALIDATION ledger-entry gate (A3.4 extraction).

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


def plan_validation_gate_rule(hg: Heartgate) -> Mapping[str, Any]:
    """Resolve the plan_validation_gate rule.

    Slice 4b T4c-2: the rule grammar (required_ledger_gate_for_transition,
    ledger_gate_name, ledger_required_fields, ledger_required_phase, and the
    pv_* check ids) is codified in engines.domain.gate_rules. The block is
    read from the loaded phase-transitions config WHEN PRESENT (production
    behavior, unchanged); when ABSENT it falls back to the code default
    (enforce-by-default / fail-closed). No operator-tunable knob this wave —
    the grammar is non-tunable.

    A test fixture may opt OUT by supplying an empty mapping for the block
    (preserving prior test laxity): an explicit ``{}`` is read as present and
    yields no ``required_ledger_gate_for_transition``, so the reader's
    ``if not required_for: return`` short-circuits the gate exactly as before.
    """
    if "plan_validation_gate" in hg.config:
        return hg.config.get("plan_validation_gate") or {}
    from engines.domain.gate_rules import plan_validation_gate_default

    return plan_validation_gate_default()


def validate_plan_validation_gate(
    hg: Heartgate,
    artifact: Mapping[str, Any],
    blockers: list[str],
    warnings: list[str] | None = None,
) -> None:
    """Phase 3.1: a PLAN_VALIDATION ledger entry with result=pass is
    required for PLAN->EXECUTE. The entry must be tagged phase=plan and
    carry a `checks:` list naming every pv_id declared in
    config/phase-transitions.yaml plan_validation_gate.checks.

    Phase 3 R1 hardening (SKEP-001 / GOV-004): the kernel does not just
    verify gate presence; it enforces the ledger schema so a single-bit
    "PLAN_VALIDATION: pass" assertion is no longer enough.
    """
    rule = hg._plan_validation_gate_rule()
    if not isinstance(rule, Mapping):
        return
    required_for = str(rule.get("required_ledger_gate_for_transition") or "")
    if not required_for:
        return
    from_phase = str(artifact.get("from_phase") or "")
    to_phase = str(artifact.get("to_phase") or "")
    if f"{from_phase}->{to_phase}" != required_for:
        return
    run_id = str(artifact.get("run_id") or "")
    if not _is_safe_run_id(run_id):
        blockers.append("plan_validation_gate: unsafe or missing run_id")
        return
    gate_name = str(rule.get("ledger_gate_name") or "PLAN_VALIDATION")
    # Pre-compute the set of pv_ids the ledger record must cover.
    declared_check_ids: set[str] = set()
    for c in rule.get("checks") or []:
        if isinstance(c, Mapping):
            cid = str(c.get("id") or "").strip()
            if cid:
                declared_check_ids.add(cid)
    # Required-field policy for the ledger record (mirrors ppv_rule.ledger_required_fields).
    ledger_required_fields = [
        str(f)
        for f in (rule.get("ledger_required_fields") or ["phase", "checks", "result"])
        if isinstance(f, str)
    ]
    required_phase = str(rule.get("ledger_required_phase") or "plan")
    ledger_path = hg.governed_root / "state" / "gate-ledger" / f"{run_id}.jsonl"
    if not ledger_path.exists():
        blockers.append(
            f"plan_validation_gate: missing {gate_name} ledger entry "
            f"(no ledger file at {ledger_path.relative_to(hg.governed_root)})"
        )
        return
    try:
        raw = ledger_path.read_text(encoding="utf-8")
    except Exception as exc:
        blockers.append(f"plan_validation_gate: ledger unreadable: {type(exc).__name__}")
        return
    # Phase 3 R2 (SKEP-R1-007): scan ALL PLAN_VALIDATION pass records and
    # accept if ANY satisfies the contract. First-defect-wins semantics
    # turned the ledger into a DoS surface — any caller could append a
    # bad PLAN_VALIDATION record to block the gate forever. Per-record
    # defects now accumulate as warnings on the transition; only the
    # absence of ANY valid record blocks.
    candidate_defects: list[str] = []
    found_pass = False
    for line_no, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception as exc:
            # Corrupt lines still block: ledger integrity is foundational.
            blockers.append(
                f"plan_validation_gate: gate ledger line {line_no} unparseable: "
                f"{type(exc).__name__}: {exc}"
            )
            return
        if str(rec.get("gate") or "") != gate_name:
            continue
        if str(rec.get("result") or "") != "pass":
            continue
        # Reject entries from the wrong phase (must be plan).
        rec_phase = str(rec.get("phase") or "")
        if not rec_phase and isinstance(rec.get("record"), Mapping):
            rec_phase = str(rec["record"].get("phase") or "")
        if rec_phase != required_phase:
            candidate_defects.append(
                f"line {line_no}: phase '{rec_phase}' != required '{required_phase}'"
            )
            continue
        body: Mapping[str, Any] = rec["record"] if isinstance(rec.get("record"), Mapping) else rec
        missing_fields = [f for f in ledger_required_fields if f not in body and f not in rec]
        if missing_fields:
            candidate_defects.append(f"line {line_no}: missing required fields {missing_fields}")
            continue
        checks_in_rec = (
            body.get("checks") if isinstance(body.get("checks"), list) else rec.get("checks")
        )
        if not isinstance(checks_in_rec, list):
            candidate_defects.append(
                f"line {line_no}: 'checks' must be a list (got {type(checks_in_rec).__name__})"
            )
            continue
        sibling_results = (
            body.get("check_results")
            if isinstance(body.get("check_results"), Mapping)
            else rec.get("check_results")
        )
        if sibling_results is not None and not isinstance(sibling_results, Mapping):
            candidate_defects.append(f"line {line_no}: 'check_results' must be a mapping")
            continue
        recorded_ids: set[str] = set()
        ids_with_pass_evidence: set[str] = set()
        per_check_defects: list[str] = []
        for entry in checks_in_rec:
            if isinstance(entry, str):
                cid = entry.strip()
                if cid:
                    recorded_ids.add(cid)
                    # String-form: per-check pass evidence must come from sibling check_results.
                    if (
                        isinstance(sibling_results, Mapping)
                        and str(sibling_results.get(cid) or "") == "pass"
                    ):
                        ids_with_pass_evidence.add(cid)
            elif isinstance(entry, Mapping):
                cid = str(entry.get("id") or "").strip()
                if cid:
                    recorded_ids.add(cid)
                    per_check_result = str(entry.get("result") or "")
                    if per_check_result == "pass":
                        ids_with_pass_evidence.add(cid)
                    elif per_check_result and per_check_result != "pass":
                        per_check_defects.append(f"check '{cid}' has non-pass result")
        if per_check_defects:
            candidate_defects.append(f"line {line_no}: " + "; ".join(per_check_defects))
            continue
        missing_ids = declared_check_ids - recorded_ids
        if missing_ids:
            candidate_defects.append(
                f"line {line_no}: missing required pv_ids {sorted(missing_ids)}"
            )
            continue
        # SKEP-R1-006: reject extra/unknown pv_ids.
        extra_ids = recorded_ids - declared_check_ids
        if extra_ids:
            candidate_defects.append(f"line {line_no}: carries unknown pv_ids {sorted(extra_ids)}")
            continue
        # SKEP-R1-003: each declared pv_id must have explicit per-check pass evidence.
        unproven = declared_check_ids - ids_with_pass_evidence
        if unproven:
            candidate_defects.append(
                f"line {line_no}: missing per-check pass evidence for {sorted(unproven)}"
            )
            continue
        # This record satisfies the full contract.
        found_pass = True
        break
    if not found_pass:
        detail = f" (per-record defects: {candidate_defects})" if candidate_defects else ""
        blockers.append(
            f"plan_validation_gate: no '{gate_name}' pass record in ledger "
            f"for run '{run_id}'{detail}"
        )
    elif candidate_defects and warnings is not None:
        warnings.append(
            f"plan_validation_gate: earlier PLAN_VALIDATION records were rejected "
            f"before a clean one was accepted: {candidate_defects}"
        )

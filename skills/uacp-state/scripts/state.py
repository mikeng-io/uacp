"""UACP state mutation handlers.

Runtime-neutral — contains no Hermes or framework-specific imports.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

# Add uacp-core/scripts to path so we can import core and filesystem.
_CORE_DIR = Path(__file__).resolve().parents[2] / "uacp-core" / "scripts"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from core import GuardianPolicy, Heartgate, _is_safe_run_id
from filesystem import _resolve_uacp_path, _write_uacp_file


def _required_uacp_context_missing(args: Mapping[str, Any]) -> list[str]:
    # Use "in" not truthiness so empty lists (e.g. declared_side_effects=[])
    # are accepted as present while missing keys are rejected.
    return [
        key
        for key in (
            "workspace",
            "uacp_run_id",
            "uacp_phase",
            "policy_version",
            "declared_side_effects",
        )
        if key not in args
    ]


def _validate_common_write_args(args: Mapping[str, Any]) -> tuple[str, str, str, str] | str:
    target_path = str(args.get("target_path") or "")
    content = args.get("content")
    reason = str(args.get("reason") or "")
    authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
    if not target_path:
        return "target_path is required"
    if not isinstance(content, str):
        return "content must be a string"
    if not reason:
        return "reason is required"
    if not authority:
        return "authority_artifact is required"
    if missing_context := _required_uacp_context_missing(args):
        return f"missing UACP context field(s): {', '.join(missing_context)}"
    return target_path, content, reason, authority


def _handle_uacp_gate_ledger_append(args: dict, **_: Any) -> str:
    """Append a single JSONL record to the run's gate ledger.

    Enforces append-only semantics: opens the file in append mode, writes
    exactly one record terminated by a newline, never truncates or seeks.
    The ledger path is fixed per run: state/gate-ledger/{run_id}.jsonl.
    Returns the byte offset of the appended record as proof.
    """
    try:
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        root = policy.uacp_root
        if missing_context := _required_uacp_context_missing(args):
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing_context)}"})
        run_id = str(args.get("uacp_run_id") or "")
        gate = str(args.get("gate") or "")
        record = args.get("record")
        authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
        if not run_id:
            return json.dumps({"error": "uacp_run_id is required"})
        if not gate:
            return json.dumps({"error": "gate is required"})
        if not isinstance(record, (dict, str)):
            return json.dumps({"error": "record must be a dict or a JSON string"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})

        # Reject path-traversal in run_id and reserve the canonical path.
        if any(c in run_id for c in ("/", "\\", "..")) or run_id in {"", ".", ".."}:
            return json.dumps({"error": "uacp_run_id contains illegal path characters"})

        # Normalize the record and stamp required envelope fields.
        if isinstance(record, str):
            try:
                record = json.loads(record)
            except Exception as exc:
                return json.dumps({"error": f"record is not valid JSON: {exc}"})
        if not isinstance(record, dict):
            return json.dumps({"error": "record must decode to a JSON object"})
        record.setdefault("gate", gate)
        record.setdefault("run_id", run_id)
        record.setdefault("ts", int(time.time()))
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if "\n" in line:
            return json.dumps({"error": "record must not contain embedded newlines"})
        # Phase 3 (pc_p2_minor): bound per-record length to stay within POSIX
        # PIPE_BUF (4096 bytes) so O_APPEND remains atomic across concurrent
        # writers. Reserve 512 bytes for the trailing newline and headroom.
        if len(line.encode("utf-8")) > 3584:
            return json.dumps({"error": "record exceeds 3584-byte ledger limit (PIPE_BUF atomicity)"})

        ledger_root = (root / "state" / "gate-ledger").resolve()
        if (root / "state").resolve() not in ledger_root.parents and ledger_root != (root / "state").resolve():
            return json.dumps({"error": "gate-ledger root resolved outside state/"})
        ledger_root.mkdir(parents=True, exist_ok=True)
        ledger_path = ledger_root / f"{run_id}.jsonl"
        # Append-only — no seek, no truncate.
        with ledger_path.open("a", encoding="utf-8") as fh:
            offset = fh.tell()
            fh.write(line + "\n")
        return json.dumps(
            {
                "ok": True,
                "path": str(ledger_path.relative_to(root)),
                "gate": gate,
                "run_id": run_id,
                "byte_offset": offset,
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_gate_ledger_append failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_state_write(args: dict, **_: Any) -> str:
    try:
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        target = _resolve_uacp_path(target_path, root)
        state_root = (root / "state").resolve()
        if target != state_root and state_root not in target.parents:
            return json.dumps({"error": "uacp_state_write may only write under state/"})
        # Phase 1 remediation (skeptic F1): the gate ledger is append-only and
        # must only be written through uacp_gate_ledger_append. uacp_state_write
        # refuses any path under state/gate-ledger/, eliminating the forge-
        # PIV-record bypass.
        gate_ledger_root = (root / "state" / "gate-ledger").resolve()
        if target == gate_ledger_root or gate_ledger_root in target.parents:
            return json.dumps({"error": "uacp_state_write may not write under state/gate-ledger/; use uacp_gate_ledger_append"})
        # Phase 3 R1 (GOV-002 / SKEP-002): the run registry is exclusively
        # mutated by the uacp-state skill. Mirror the gate-ledger pattern —
        # refuse direct writes through uacp_state_write so the registry
        # cannot be clobbered by an EXECUTE-phase caller.
        run_registry_path = (root / "state" / "run-registry.yaml").resolve()
        if target == run_registry_path:
            return json.dumps({"error": "uacp_state_write may not write state/run-registry.yaml directly; use uacp_run_registry_update via the uacp-state skill"})
        # Global review R1 (TECH-G-001): state/escalations/ is exclusively
        # written by uacp_escalation_event (Phase 4.4). Extend the pattern
        # established by gate-ledger and run-registry so uacp_state_write
        # cannot clobber JSONL files or skip the trigger/severity/mode
        # validation done in the narrow writer.
        escalations_root = (root / "state" / "escalations").resolve()
        if target == escalations_root or escalations_root in target.parents:
            return json.dumps({"error": "uacp_state_write may not write under state/escalations/; use uacp_escalation_event"})
        # Global review R1 (SKEP-G-005): state/current.yaml is the active-run
        # pointer. Phase 5 will introduce kernel readers for current.yaml's
        # uacp_mode and active_phase fields; allowing any phase's caller to
        # rewrite the pointer would let a skill downgrade its own mode or
        # repoint the active run. Caller-binding mirrors run-registry: writes
        # are only accepted when the caller's uacp_run_id matches the new
        # content's active_run_id.
        #
        # R1 confirmation R2 (SKEP-G5-001): distinguish bootstrap (current.yaml
        # does not yet exist) from pointer-clear-attack (current.yaml exists
        # but new content has empty active_run_id). Bootstrap permits any
        # caller to seed the file; once the file exists, every write must
        # declare a non-empty active_run_id that matches the caller.
        current_pointer_path = (root / "state" / "current.yaml").resolve()
        if target == current_pointer_path:
            caller_run_id = str(args.get("uacp_run_id") or "")
            try:
                import yaml as _yaml
                parsed = _yaml.safe_load(content) or {}
            except Exception as exc:
                return json.dumps({"error": f"uacp_state_write: state/current.yaml content unparseable as YAML: {type(exc).__name__}: {exc}"})
            if not isinstance(parsed, dict):
                return json.dumps({"error": "uacp_state_write: state/current.yaml content must be a YAML mapping"})
            declared_run_id = str(parsed.get("active_run_id") or "")
            pointer_exists = current_pointer_path.exists()
            if pointer_exists:
                # Post-bootstrap: every write must carry a caller-bound active_run_id.
                if not declared_run_id:
                    return json.dumps({"error": "uacp_state_write: state/current.yaml#active_run_id is required (pointer-clear-attack refused; current.yaml already exists)"})
                if declared_run_id != caller_run_id:
                    return json.dumps({"error": f"uacp_state_write: state/current.yaml#active_run_id '{declared_run_id}' does not match caller uacp_run_id '{caller_run_id}' — current-pointer mutations must be caller-owned"})
            else:
                # Bootstrap path: file does not yet exist. Permit seeding; if
                # the new content carries an active_run_id, still require it
                # match the caller (defense-in-depth).
                if declared_run_id and caller_run_id and declared_run_id != caller_run_id:
                    return json.dumps({"error": f"uacp_state_write: bootstrap seed of state/current.yaml#active_run_id '{declared_run_id}' does not match caller uacp_run_id '{caller_run_id}'"})

        _write_uacp_file(target, content)
        return json.dumps(
            {
                "ok": True,
                "path": str(target.relative_to(root)),
                "reason": reason,
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_state_write failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_run_registry_update(args: dict, **_: Any) -> str:
    """Phase 3 R1 (GOV-002 / SKEP-002): the exclusive mechanical mutator of
    state/run-registry.yaml. Supports two ops:

      op=register    add an active_runs[] entry. Required keys in `entry`:
                     run_id, phase, write_paths, scope_artifact_path,
                     started_at.
      op=deregister  remove the active_runs[] entry whose run_id matches
                     `entry.run_id`.

    Refuses any other operation. Validates `entry.run_id` with
    _is_safe_run_id. Schema-checks write_paths (must be a list of strings).

    Phase 3 R2 hardening:
      * TECH-R1-001: enforces UACP context fields via _required_uacp_context_missing.
      * SKEP-R1-001: rejects requests where entry.run_id != caller uacp_run_id
        (caller cannot squat or evict another run's registration).
      * TECH-R1-002: canonicalizes each write_paths entry on write and rejects
        entries that canonicalize to empty (no '..' segments, no absolute
        paths, no whitespace-only / wildcard prefixes).
      * The scope artifact at plans/{run_id}-scope.yaml is validated by
        Heartgate at PLAN->EXECUTE (see _validate_scope_artifact); this
        handler does NOT pre-check it during register, deferring authority
        to the Heartgate transition. Phase 4 may tighten this with a
        pre-check (see pc_p3_skep_r1_001).
    """
    try:
        # TECH-R1-001 — enforce UACP context fields.
        missing_context = _required_uacp_context_missing(args)
        if missing_context:
            return json.dumps({"error": f"missing UACP context fields: {', '.join(missing_context)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        root = policy.uacp_root
        op = str(args.get("op") or "").strip().lower()
        if op not in {"register", "deregister"}:
            return json.dumps({"error": "uacp_run_registry_update: op must be 'register' or 'deregister'"})
        entry = args.get("entry") or {}
        if not isinstance(entry, dict):
            return json.dumps({"error": "uacp_run_registry_update: 'entry' must be a mapping"})
        run_id = str(entry.get("run_id") or "")
        if not _is_safe_run_id(run_id):
            return json.dumps({"error": "uacp_run_registry_update: entry.run_id unsafe or missing"})
        # SKEP-R1-001 — caller-binding: entry.run_id MUST equal caller uacp_run_id.
        caller_run_id = str(args.get("uacp_run_id") or "")
        if caller_run_id != run_id:
            return json.dumps({"error": f"uacp_run_registry_update: entry.run_id '{run_id}' does not match caller uacp_run_id '{caller_run_id}' — registry mutations must be caller-owned"})
        reason = str(args.get("reason") or "")
        authority = str(args.get("authority_artifact") or "")
        if not reason or not authority:
            return json.dumps({"error": "uacp_run_registry_update: reason and authority_artifact are required"})
        registry_path = (root / "state" / "run-registry.yaml").resolve()
        # Read existing registry.
        try:
            import yaml as _yaml
        except Exception:
            return json.dumps({"error": "uacp_run_registry_update: PyYAML required"})
        if registry_path.exists():
            try:
                data = _yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                return json.dumps({"error": f"uacp_run_registry_update: existing registry unparseable: {type(exc).__name__}: {exc}"})
            if not isinstance(data, dict):
                return json.dumps({"error": "uacp_run_registry_update: existing registry top-level must be a mapping"})
        else:
            data = {"schema_version": "0.1", "active_runs": []}
        active = data.get("active_runs", [])
        if not isinstance(active, list):
            return json.dumps({"error": "uacp_run_registry_update: existing active_runs must be a list"})
        if op == "register":
            wps = entry.get("write_paths") or []
            if not isinstance(wps, list) or not all(isinstance(w, str) for w in wps):
                return json.dumps({"error": "uacp_run_registry_update: entry.write_paths must be a list of strings"})
            # TECH-R1-002 — canonicalize each write_path; reject any that
            # canonicalize to empty (parent escape, absolute path, wildcard,
            # whitespace-only). This makes write_paths non-cloakable.
            canon_wps: list[str] = []
            for w in wps:
                cw = Heartgate._canon_write_path(w)
                if not cw:
                    return json.dumps({"error": f"uacp_run_registry_update: write_path '{w}' is not canonicalizable (rejects '..', absolute paths, wildcards, whitespace-only)"})
                canon_wps.append(cw)
            # SKEP-R1-004 defense-in-depth — empty write_paths is suspicious;
            # require either at least one canonical entry or an explicit
            # no_writes_intended sentinel.
            if not canon_wps and not entry.get("no_writes_intended"):
                return json.dumps({"error": "uacp_run_registry_update: empty write_paths requires explicit entry.no_writes_intended=true"})
            # Replace any existing entry for this run_id.
            active = [e for e in active if isinstance(e, dict) and str(e.get("run_id") or "") != run_id]
            active.append({
                "run_id": run_id,
                "phase": str(entry.get("phase") or ""),
                "write_paths": canon_wps,
                "scope_artifact_path": str(entry.get("scope_artifact_path") or ""),
                "started_at": int(entry.get("started_at") or 0),
            })
        else:  # deregister
            active = [e for e in active if isinstance(e, dict) and str(e.get("run_id") or "") != run_id]
        data["active_runs"] = active
        # Write through the canonical writer (Phase 4 will add atomic-rename
        # + advisory locking per pc_p3_skep_r1_005).
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        body = _yaml.safe_dump(data, sort_keys=False)
        _write_uacp_file(registry_path, body)
        return json.dumps({"ok": True, "op": op, "run_id": run_id, "active_count": len(active), "authority_artifact": authority}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"uacp_run_registry_update failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_escalation_event(args: dict, **_: Any) -> str:
    """Phase 4.4 — append an operator-facing escalation record to
    state/escalations/{run_id}.jsonl.

    Required args (plus standard UACP context):
      trigger: string id matching an entry in config/autonomy-policy.yaml#escalation_triggers.triggers
      severity: enum {info, warn, block}
      reason: string explanation
      mode: current uacp_mode {manual, semi_auto, supervised_auto, full_auto}
      details: optional mapping with extra context

    Phase 4 R1 absorbed constraint (pc_p3_tech_r1_001): this handler
    enforces UACP context fields via _required_uacp_context_missing.

    The handler is intentionally a stub. It writes the JSONL record and
    returns. The Hermes core seam — push-notify the operator — is
    Phase 5. In Phase 4 operators poll state/escalations/.
    """
    try:
        missing_context = _required_uacp_context_missing(args)
        if missing_context:
            return json.dumps({"error": f"missing UACP context fields: {', '.join(missing_context)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        root = policy.uacp_root
        run_id = str(args.get("uacp_run_id") or "")
        if not _is_safe_run_id(run_id):
            return json.dumps({"error": "uacp_escalation_event: unsafe or missing uacp_run_id"})
        trigger = str(args.get("trigger") or "").strip()
        severity = str(args.get("severity") or "").strip().lower()
        reason = str(args.get("reason") or "").strip()
        mode = str(args.get("mode") or "").strip().lower()
        authority = str(args.get("authority_artifact") or "").strip()
        if not trigger:
            return json.dumps({"error": "uacp_escalation_event: 'trigger' is required"})
        if severity not in {"info", "warn", "block"}:
            return json.dumps({"error": "uacp_escalation_event: 'severity' must be info|warn|block"})
        if not reason:
            return json.dumps({"error": "uacp_escalation_event: 'reason' is required"})
        # Phase 4 R1 (TECH-P4-002): state.yaml#escalations.record_schema.required_fields
        # lists `mode` as required. Honor the schema contract — empty mode is
        # rejected, not silently written as "".
        if not mode:
            return json.dumps({"error": "uacp_escalation_event: 'mode' is required (must be manual|semi_auto|supervised_auto|full_auto)"})
        if mode not in {"manual", "semi_auto", "supervised_auto", "full_auto"}:
            return json.dumps({"error": "uacp_escalation_event: 'mode' must be manual|semi_auto|supervised_auto|full_auto"})
        if not authority:
            return json.dumps({"error": "uacp_escalation_event: 'authority_artifact' is required"})
        details = args.get("details") or {}
        if details and not isinstance(details, dict):
            return json.dumps({"error": "uacp_escalation_event: 'details' must be a mapping when present"})
        record = {
            "run_id": run_id,
            "phase": str(args.get("uacp_phase") or ""),
            "mode": mode,
            "trigger": trigger,
            "severity": severity,
            "reason": reason,
            "authority_artifact": authority,
            "ts": int(time.time()),
        }
        if details:
            record["details"] = details
        # Append-only JSONL, one record per line. Mirror PIPE_BUF (3584-byte)
        # atomicity bound from uacp_gate_ledger_append.
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        if len(line.encode("utf-8")) > 3584:
            return json.dumps({"error": "record exceeds 3584-byte escalation limit (PIPE_BUF atomicity)"})
        # Phase 4 R1 (TECH-P4-005): containment check — ensure resolved path
        # remains under root/state/escalations. Defense-in-depth alongside
        # _is_safe_run_id (which already prevents traversal).
        out_path = (root / "state" / "escalations" / f"{run_id}.jsonl").resolve()
        escalations_root = (root / "state" / "escalations").resolve()
        if escalations_root not in out_path.parents:
            return json.dumps({"error": "uacp_escalation_event: resolved path escapes state/escalations/"})
        # Phase 4 R1 (TECH-P4-009): mirror gate-ledger's explicit embedded-newline
        # refusal (json.dumps escapes them, but belt-and-braces).
        if "\n" in line:
            return json.dumps({"error": "uacp_escalation_event: serialized line must not contain embedded newlines"})
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return json.dumps({"ok": True, "path": str(out_path.relative_to(root)), "trigger": trigger, "severity": severity, "run_id": run_id, "authority_artifact": authority}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"uacp_escalation_event failed: {type(exc).__name__}: {exc}"})

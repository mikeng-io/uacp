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

from config import base_dir
from contracts import _required_uacp_context_missing, _validate_common_write_args
from core import GuardianPolicy, Heartgate, _is_safe_run_id
from filesystem import _resolve_uacp_path, _write_uacp_file
from engines.domain import EscalationMode, EscalationSeverity
from typing import get_args as _get_args

# Re-exported for backward compatibility: callers historically imported these
# validators from `state`; they now live in the neutral `contracts` module.
__all__ = [
    "_required_uacp_context_missing",
    "_validate_common_write_args",
    "_handle_uacp_gate_ledger_append",
    "_handle_uacp_state_write",
    "_handle_uacp_run_registry_update",
    "_handle_uacp_escalation_event",
    "_handle_uacp_run_init",
    "_handle_uacp_run_transition",
    "_handle_uacp_run_register_artifact",
    "_handle_uacp_run_finalize",
]


def _gate_ledger_path(root: Path, run_id: str) -> Path:
    """Canonical per-run gate-ledger path (state/gate-ledger/{run_id}.jsonl),
    containment-checked under state/. Creates the ledger dir. Raises ValueError if
    it would resolve outside state/. Single source of the ledger path shape,
    reused by the append handler AND handle_transition's canonical-gate emit."""
    base = base_dir(root)
    ledger_root = (base / "state" / "gate-ledger").resolve()
    if (base / "state").resolve() not in ledger_root.parents and ledger_root != (
        base / "state"
    ).resolve():
        raise ValueError("gate-ledger root resolved outside state/")
    ledger_root.mkdir(parents=True, exist_ok=True)
    return ledger_root / f"{run_id}.jsonl"


def _append_gate_ledger_record(root: Path, run_id: str, record: dict) -> tuple[Path, int]:
    """Append one record to the run's gate ledger as a single canonical JSONL line
    (sorted keys; PIPE_BUF-bounded so O_APPEND stays atomic). Append-only — no seek,
    no truncate. The ONE place that knows the ledger line format; reused by the
    governed uacp_gate_ledger_append handler AND state_machine.handle_transition.
    Raises ValueError on an unwritable record. Returns (ledger_path, byte_offset)."""
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    if "\n" in line:
        raise ValueError("record must not contain embedded newlines")
    if len(line.encode("utf-8")) > 3584:
        raise ValueError("record exceeds 3584-byte ledger limit (PIPE_BUF atomicity)")
    ledger_path = _gate_ledger_path(root, run_id)
    with ledger_path.open("a", encoding="utf-8") as fh:
        offset = fh.tell()
        fh.write(line + "\n")
    return ledger_path, offset


def _existing_gate_ledger_gates(root: Path, run_id: str) -> set[str]:
    """The set of ``gate`` strings already present in the run's gate ledger — the
    idempotency read for handle_transition's auto-emit. Never raises: a missing or
    partially-garbled ledger yields whatever gates parse cleanly."""
    try:
        path = _gate_ledger_path(root, run_id)
    except ValueError:
        return set()
    if not path.exists():
        return set()
    gates: set[str] = set()
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except Exception:
                continue
            gate = rec.get("gate") if isinstance(rec, dict) else None
            if isinstance(gate, str) and gate:
                gates.add(gate)
    except Exception:
        return gates
    return gates


def _run_manifest_goal_id(root: Path, run_id: str) -> str | None:
    """Read a run's goal_id from its manifest (state/runs/{run_id}.yaml).

    Council M-1: the manifest goal_id is the AUTHORITATIVE goal binding (the
    convergence cap counts the run-chain by scanning manifests). The registry
    register cross-checks against this value and fails closed on mismatch.

    Returns the manifest's goal_id as a string (``""`` when the manifest carries
    no goal_id), or ``None`` when the manifest is missing/unreadable/invalid — so
    a caller without a positive manifest binding cannot assert a goal_id in the
    registry. Never raises.
    """
    if not _is_safe_run_id(run_id):
        return None
    try:
        from engines.io.loaders import load_manifest

        loaded = load_manifest(root, run_id)
        if loaded.error is not None or loaded.value is None:
            return None
        model = loaded.value.model
        if model is not None:
            return str(getattr(model, "goal_id", "") or "")
        raw = loaded.value.raw
        if isinstance(raw, Mapping):
            return str(raw.get("goal_id") or "")
        return None
    except Exception:
        return None


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
        # Serialize + append via the shared canonical ledger IO (line format,
        # PIPE_BUF bound, containment, append-only) — the same seam
        # handle_transition reuses so the two paths cannot diverge on format.
        try:
            base = base_dir(root)
            ledger_path, offset = _append_gate_ledger_record(root, run_id, record)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        return json.dumps(
            {
                "ok": True,
                "path": str(ledger_path.relative_to(base)),
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

        base = base_dir(root)
        target = _resolve_uacp_path(target_path, base)
        state_root = (base / "state").resolve()
        if target != state_root and state_root not in target.parents:
            return json.dumps({"error": "uacp_state_write may only write under state/"})
        # Phase 1 remediation (skeptic F1): the gate ledger is append-only and
        # must only be written through uacp_gate_ledger_append. uacp_state_write
        # refuses any path under state/gate-ledger/, eliminating the forge-
        # PIV-record bypass.
        gate_ledger_root = (base / "state" / "gate-ledger").resolve()
        if target == gate_ledger_root or gate_ledger_root in target.parents:
            return json.dumps({"error": "uacp_state_write may not write under state/gate-ledger/; use uacp_gate_ledger_append"})
        # Phase 3 R1 (GOV-002 / SKEP-002): the run registry is exclusively
        # mutated by the uacp-state skill. Mirror the gate-ledger pattern —
        # refuse direct writes through uacp_state_write so the registry
        # cannot be clobbered by an EXECUTE-phase caller.
        run_registry_path = (base / "state" / "run-registry.yaml").resolve()
        if target == run_registry_path:
            return json.dumps({"error": "uacp_state_write may not write state/run-registry.yaml directly; use uacp_run_registry_update via the uacp-state skill"})
        # Global review R1 (TECH-G-001): state/escalations/ is exclusively
        # written by uacp_escalation_event (Phase 4.4). Extend the pattern
        # established by gate-ledger and run-registry so uacp_state_write
        # cannot clobber JSONL files or skip the trigger/severity/mode
        # validation done in the narrow writer.
        escalations_root = (base / "state" / "escalations").resolve()
        if target == escalations_root or escalations_root in target.parents:
            return json.dumps({"error": "uacp_state_write may not write under state/escalations/; use uacp_escalation_event"})
        # F2 (verification-method council, 2026-06-25): state/runs/ holds the run
        # MANIFEST (state/runs/{run_id}.yaml) whose `artifacts:` map is the graph that
        # the coverage projection, the registration precondition, and scope-conformance's
        # governance-by-kind exemption all TRUST. A generic uacp_state_write to this
        # subdir let an EXECUTE-phase caller forge manifest.artifacts / phase and defeat
        # every graph-trust gate. Mirror the gate-ledger / run-registry / escalations
        # carve-outs: run state is authoritative and mutated ONLY by the uacp-state
        # operations (handle_init / handle_transition / handle_register_artifact /
        # handle_finalize / handle_workspace), which write it directly — never through
        # this generic escape hatch.
        runs_root = (base / "state" / "runs").resolve()
        if target == runs_root or runs_root in target.parents:
            return json.dumps({"error": "uacp_state_write may not write under state/runs/; run state (the run manifest + transition artifacts) is mutated only via the uacp-state operations (init/transition/register-artifact/finalize), which own manifest.artifacts integrity"})
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
        current_pointer_path = (base / "state" / "current.yaml").resolve()
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
                "path": str(target.relative_to(base)),
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
        base = base_dir(root)
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
        registry_path = (base / "state" / "run-registry.yaml").resolve()
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
            new_entry = {
                "run_id": run_id,
                "phase": str(entry.get("phase") or ""),
                "write_paths": canon_wps,
                "scope_artifact_path": str(entry.get("scope_artifact_path") or ""),
                "started_at": int(entry.get("started_at") or 0),
            }
            # Goal-chaining (Task 3): record the persistent goal link when
            # present so the chain is queryable by goal_id (list_runs_for_goal).
            # Caller-binding (SKEP-R1-001) above is unchanged — goal_id does not
            # widen who may register an entry. Standard runs omit goal_id.
            goal_id = entry.get("goal_id")
            if goal_id is not None:
                # Council M-1 (defense-in-depth): a registry goal_id must match
                # the caller's run-MANIFEST goal_id. The manifest is the
                # authoritative binding (the convergence cap counts the chain by
                # manifest), so the registry must not be poisoned with a
                # different goal_id (which a registry-based count would have
                # trusted). Fail CLOSED on mismatch — error, no write. A run
                # whose manifest is absent/unreadable cannot assert a goal_id
                # binding either.
                manifest_goal_id = _run_manifest_goal_id(root, run_id)
                if manifest_goal_id is None:
                    return json.dumps({"error": f"uacp_run_registry_update: cannot bind goal_id '{goal_id}' — run manifest for '{run_id}' is missing or unreadable (the manifest goal_id is authoritative)"})
                if str(goal_id) != manifest_goal_id:
                    return json.dumps({"error": f"uacp_run_registry_update: entry.goal_id '{goal_id}' does not match run-manifest goal_id '{manifest_goal_id}' for '{run_id}' — the manifest goal_id is authoritative (registry-poisoning refused)"})
                new_entry["goal_id"] = str(goal_id)
            active.append(new_entry)
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
      trigger: string id matching an entry in config/uacp.toml [autonomy.escalation_triggers] triggers
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
        base = base_dir(root)
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
        _VALID_SEVERITY = set(_get_args(EscalationSeverity))
        if severity not in _VALID_SEVERITY:
            return json.dumps({"error": "uacp_escalation_event: 'severity' must be info|warn|block"})
        if not reason:
            return json.dumps({"error": "uacp_escalation_event: 'reason' is required"})
        # Phase 4 R1 (TECH-P4-002): state.yaml#escalations.record_schema.required_fields
        # lists `mode` as required. Honor the schema contract — empty mode is
        # rejected, not silently written as "".
        if not mode:
            return json.dumps({"error": "uacp_escalation_event: 'mode' is required (must be manual|semi_auto|supervised_auto|full_auto)"})
        _VALID_MODE = set(_get_args(EscalationMode))
        if mode not in _VALID_MODE:
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
        out_path = (base / "state" / "escalations" / f"{run_id}.jsonl").resolve()
        escalations_root = (base / "state" / "escalations").resolve()
        if escalations_root not in out_path.parents:
            return json.dumps({"error": "uacp_escalation_event: resolved path escapes state/escalations/"})
        # Phase 4 R1 (TECH-P4-009): mirror gate-ledger's explicit embedded-newline
        # refusal (json.dumps escapes them, but belt-and-braces).
        if "\n" in line:
            return json.dumps({"error": "uacp_escalation_event: serialized line must not contain embedded newlines"})
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return json.dumps({"ok": True, "path": str(out_path.relative_to(base)), "trigger": trigger, "severity": severity, "run_id": run_id, "authority_artifact": authority}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"uacp_escalation_event failed: {type(exc).__name__}: {exc}"})


# ---------------------------------------------------------------------------
# Run lifecycle tools — governed wrappers for state_machine.handle_* functions.
# Each handler enforces the standard UACP context fields (via
# _required_uacp_context_missing) and requires reason + authority_artifact
# before delegating to the neutral state machine.  The state machine itself
# carries no governed-context contract; these thin wrappers are the seam.
# ---------------------------------------------------------------------------


def _handle_uacp_run_init(args: dict, **_: Any) -> str:
    """Governed wrapper for state_machine.handle_init.

    Creates a new run manifest at state/runs/{run_id}.yaml with governed-context
    enforcement: validates UACP context fields and requires reason +
    authority_artifact before delegating.  Maps the tool-level ``uacp_run_id``
    field to the state machine's ``run_id`` parameter.
    """
    try:
        missing = _required_uacp_context_missing(args)
        if missing:
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        reason = (args.get("reason") or "").strip()
        authority = (args.get("authority_artifact") or "").strip()
        if not reason:
            return json.dumps({"error": "reason is required"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})
        run_id = str(args.get("uacp_run_id") or "").strip()
        params: dict[str, Any] = {
            "workspace": str(policy.uacp_root),
            "run_id": run_id,
            "source": str(args.get("source") or "").strip(),
        }
        for key in (
            "initial_phase",
            "track",
            "workspace_kind",
            "workspace_path",
            "workspace_branch",
            "goal_id",
            "inherits_from",
            "scope",
            "granularity",
            "risk",
            "domains",
        ):
            if key in args:
                params[key] = args[key]
        from state_machine import handle_init  # lazy: avoids any future import cycles

        return handle_init(params)
    except Exception as exc:
        return json.dumps({"error": f"uacp_run_init failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_run_transition(args: dict, **_: Any) -> str:
    """Governed wrapper for state_machine.handle_transition.

    Executes a locked phase transition with governed-context enforcement.
    Validates UACP context fields, requires reason + authority_artifact, and
    validates from_phase / to_phase before delegating to the state machine,
    which enforces the canonical phase graph and phase-exit structural gates.
    """
    try:
        missing = _required_uacp_context_missing(args)
        if missing:
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        reason = (args.get("reason") or "").strip()
        authority = (args.get("authority_artifact") or "").strip()
        if not reason:
            return json.dumps({"error": "reason is required"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})
        run_id = str(args.get("uacp_run_id") or "").strip()
        from_phase = str(args.get("from_phase") or "").strip()
        to_phase = str(args.get("to_phase") or "").strip()
        if not from_phase:
            return json.dumps({"error": "from_phase is required"})
        if not to_phase:
            return json.dumps({"error": "to_phase is required"})
        params: dict[str, Any] = {
            "workspace": str(policy.uacp_root),
            "run_id": run_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
        }
        from state_machine import handle_transition  # lazy: avoids any future import cycles

        return handle_transition(params)
    except Exception as exc:
        return json.dumps({"error": f"uacp_run_transition failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_run_register_artifact(args: dict, **_: Any) -> str:
    """Governed wrapper for state_machine.handle_register_artifact.

    Links a phase artifact path into manifest.artifacts[artifact_type] with
    governed-context enforcement.  Validates UACP context fields, requires
    reason + authority_artifact + artifact_type + path before delegating.
    """
    try:
        missing = _required_uacp_context_missing(args)
        if missing:
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        reason = (args.get("reason") or "").strip()
        authority = (args.get("authority_artifact") or "").strip()
        if not reason:
            return json.dumps({"error": "reason is required"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})
        run_id = str(args.get("uacp_run_id") or "").strip()
        artifact_type = str(args.get("artifact_type") or "").strip()
        path = str(args.get("path") or "").strip()
        if not artifact_type:
            return json.dumps({"error": "artifact_type is required"})
        if not path:
            return json.dumps({"error": "path is required"})
        params: dict[str, Any] = {
            "workspace": str(policy.uacp_root),
            "run_id": run_id,
            "artifact_type": artifact_type,
            "path": path,
        }
        from state_machine import handle_register_artifact  # lazy: avoids any future import cycles

        return handle_register_artifact(params)
    except Exception as exc:
        return json.dumps({"error": f"uacp_run_register_artifact failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_run_finalize(args: dict, **_: Any) -> str:
    """Governed wrapper for state_machine.handle_finalize.

    Finalizes a run from verify to resolved, gated by the Heartgate closure
    sweep.  Validates UACP context fields and requires reason +
    authority_artifact before delegating.  The state machine tentatively
    stamps the run resolved/finalized, runs the closure gate, and reverts on
    block — this wrapper does NOT bypass that gate.
    """
    try:
        missing = _required_uacp_context_missing(args)
        if missing:
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})
        workspace = args.get("workspace")
        policy = GuardianPolicy.load(workspace)
        reason = (args.get("reason") or "").strip()
        authority = (args.get("authority_artifact") or "").strip()
        if not reason:
            return json.dumps({"error": "reason is required"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})
        run_id = str(args.get("uacp_run_id") or "").strip()
        params: dict[str, Any] = {
            "workspace": str(policy.uacp_root),
            "run_id": run_id,
        }
        from state_machine import handle_finalize  # lazy: avoids any future import cycles

        return handle_finalize(params)
    except Exception as exc:
        return json.dumps({"error": f"uacp_run_finalize failed: {type(exc).__name__}: {exc}"})

"""Hermes adapter for UACP Guardian runtime enforcement."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from .kernel import (
    Guardian,
    GuardianDecision,
    GuardianEvent,
    GuardianPolicy,
    GuardianPolicyError,
    Heartgate,
    HeartgateError,
    make_event,
    write_audit_record,
)


_POLICY: GuardianPolicy | None = None
_POLICY_ERROR: str = ""
_PHASE_CONFIG: dict[str, Any] | None = None
_CONTAINED_SHELL_ATTESTATIONS: dict[str, dict[str, Any]] = {}


def _phase_config() -> dict[str, Any]:
    """Phase-transition config used for Layer B (per-phase tool admissibility).

    Loaded once per process from `config/phase-transitions.yaml`. Cached at
    module level alongside `_POLICY`; see runtime-integration-guide.md for the
    reload model.
    """
    global _PHASE_CONFIG
    if _PHASE_CONFIG is not None:
        return _PHASE_CONFIG
    try:
        import yaml as _yaml
        path = _policy().uacp_root / "config" / "phase-transitions.yaml"
        raw = _yaml.safe_load(path.read_text(encoding="utf-8"))
        _PHASE_CONFIG = raw if isinstance(raw, dict) else {}
    except Exception:
        _PHASE_CONFIG = {}
    return _PHASE_CONFIG

# Self-attesting tools are declared in `config/guardian-policy.yaml` under
# `self_attesting_tools.names` (moved out of adapter code in Phase 1 / pc_1 to
# remove the hidden authority list flagged by the Phase 0 Codex review).
# `_self_attesting_tools()` returns the active set from the loaded policy.


def _self_attesting_tools() -> frozenset[str]:
    try:
        return _policy().self_attesting_tools
    except GuardianPolicyError:
        return frozenset()


def _policy() -> GuardianPolicy:
    global _POLICY, _POLICY_ERROR
    if _POLICY is not None:
        return _POLICY
    try:
        _POLICY = GuardianPolicy.load()
        _POLICY_ERROR = ""
        return _POLICY
    except GuardianPolicyError as exc:
        _POLICY_ERROR = str(exc)
        raise


def _decision_for_event(event: GuardianEvent) -> GuardianDecision:
    policy = _policy()
    return Guardian(policy, phase_config=_phase_config()).evaluate(event)


def _filesystem_guard_verified(tool_name: str, args: Mapping[str, Any] | None) -> bool:
    """Whether this event satisfies UACP filesystem-containment requirements.

    Returns True when either:
      - The tool is one of the UACP-governed writers/checks whose handler
        performs its own path-bounded containment (the active policy's
        `self_attesting_tools` list — see config/guardian-policy.yaml).
      - The args include an `attestation_id` that matches an unexpired,
        containment-verified record produced by `uacp_contained_shell` with
        a policy version matching the currently-loaded policy.
    Returns False otherwise.

    This wiring closes the gap where the kernel checked
    `event.filesystem_guard_verified` but the adapter never set it, blocking
    every UACP-bound writer call.
    """
    if tool_name in _self_attesting_tools():
        return True
    args = args or {}
    attestation_id = str(args.get("attestation_id") or "")
    if not attestation_id:
        return False
    try:
        policy_version = str(_policy().version)
    except GuardianPolicyError:
        return False
    ok, _ = _validate_contained_shell_attestation(attestation_id, policy_version)
    return ok


def _block_for_policy_error(tool_name: str, args: Mapping[str, Any] | None) -> dict[str, str] | None:
    event = make_event(tool_name=tool_name, args=args or {})
    category = "external.unknown_mutator"
    if event.tool_name in {"read_file", "search_files"} and not event.uacp_run_id:
        return None
    message = _POLICY_ERROR or "Guardian policy failed to load"
    return {"action": "block", "message": f"UACP Guardian blocked {category}: {message}"}


def on_pre_tool_call(
    *,
    tool_name: str = "",
    args: Mapping[str, Any] | None = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    tool_provider: str = "",
    **_: Any,
) -> dict[str, str] | None:
    try:
        if not tool_provider:
            tool_provider = _infer_hermes_tool_provider(tool_name)
        event = make_event(
            tool_name=tool_name,
            args=args or {},
            event_type="pre_tool_call",
            tool_provider=tool_provider,
            task_id=task_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            filesystem_guard_verified=_filesystem_guard_verified(tool_name, args),
        )
        decision = _decision_for_event(event)
        if decision.audit_required:
            audit_path = write_audit_record(decision.to_audit_record(event))
            decision = GuardianDecision(
                decision.decision,
                decision.category,
                decision.reason,
                decision.evidence,
                decision.audit_required,
            )
        if decision.blocks_execution:
            return decision.to_hook_result()
        return None
    except GuardianPolicyError:
        return _block_for_policy_error(tool_name, args)


def on_post_tool_call(
    *,
    tool_name: str = "",
    args: Mapping[str, Any] | None = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    tool_provider: str = "",
    duration_ms: int | None = None,
    **_: Any,
) -> None:
    try:
        if not tool_provider:
            tool_provider = _infer_hermes_tool_provider(tool_name)
        event = make_event(
            tool_name=tool_name,
            args=args or {},
            event_type="post_tool_call",
            tool_provider=tool_provider,
            task_id=task_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            filesystem_guard_verified=_filesystem_guard_verified(tool_name, args),
        )
        decision = _decision_for_event(event)
        record = decision.to_audit_record(event)
        record["duration_ms"] = duration_ms
        record["result_preview"] = str(result)[:500]
        write_audit_record(record)
    except GuardianPolicyError:
        return None


def _infer_hermes_tool_provider(tool_name: str) -> str:
    """Hermes-specific provider lookup kept in the adapter, not the kernel."""
    if tool_name.startswith("mcp_"):
        return "mcp"
    try:
        from model_tools import _AGENT_LOOP_TOOLS

        if tool_name in _AGENT_LOOP_TOOLS:
            return "inline_agent_loop"
    except Exception:
        pass
    try:
        from hermes_cli.plugins import get_plugin_manager

        manager = get_plugin_manager()
        if tool_name in getattr(manager, "_plugin_tool_names", set()):
            return "plugin"
    except Exception:
        pass
    return "core"


def _resolve_uacp_path(raw: str, root: Path) -> Path:
    root = root.resolve()
    path = Path(raw)
    if path.is_absolute():
        raise ValueError("target_path must be UACP-root-relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("target_path must not contain empty, current, or parent path segments")
    candidate = root / path
    # Fail closed on symlinked path components before writing.  A symlink inside
    # UACP_ROOT can otherwise resolve outside the governed workspace.
    current = root
    for part in path.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError("target_path must not traverse symlinked directories")
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("target_path must not be a symlink")
    resolved = candidate.resolve(strict=False)
    if resolved == root:
        raise ValueError("target_path must point to a file under UACP_ROOT")
    if root not in resolved.parents:
        raise ValueError("target_path escapes UACP_ROOT")
    return resolved


def _required_uacp_context_missing(args: Mapping[str, Any]) -> list[str]:
    return [
        key
        for key in (
            "workspace",
            "uacp_run_id",
            "uacp_phase",
            "policy_version",
            "declared_side_effects",
        )
        if not args.get(key)
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


def _write_uacp_file(target: Path, content: str) -> None:
    if target.exists() and target.is_dir():
        raise ValueError("target_path must point to a file, not a directory")
    if target.suffix in {".yaml", ".yml"}:
        import yaml

        yaml.safe_load(content)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")




def _path_relationship(root: Path, workspace: Path) -> dict[str, Any]:
    root = root.resolve()
    workspace = workspace.expanduser().resolve(strict=False)
    return {
        "uacp_root_resolved": str(root),
        "workspace_resolved": str(workspace),
        "workspace_exists": workspace.exists(),
        "workspace_is_dir": workspace.is_dir(),
        "workspace_under_uacp_root": root == workspace or root in workspace.parents,
        "uacp_root_under_workspace": workspace == root or workspace in root.parents,
    }


def _run_bwrap_readonly_probe(root: Path, workspace: Path, *, timeout: int = 20) -> dict[str, Any]:
    """Probe whether bubblewrap can run with UACP_ROOT read-only and workspace writable.

    This proves availability of a lower-level bwrap containment mechanism. It does
    not by itself prove that the standard Hermes terminal/execute_code tool path
    is wrapped; callers must keep standard tool paths fail-closed unless the
    runtime actually executes through this containment layer.
    """
    code = """
from pathlib import Path
import json
import sys
root = Path(sys.argv[1])
workspace = Path(sys.argv[2])
probe = root / '.uacp_sandbox_write_probe'
try:
    probe.write_text('probe', encoding='utf-8')
    write_blocked = False
    write_error = 'write_succeeded'
    try:
        probe.unlink()
    except Exception:
        pass
except OSError as exc:
    write_blocked = True
    write_error = f'{type(exc).__name__}:{getattr(exc, "errno", "")}'
workspace_probe = workspace / '.uacp_sandbox_workspace_probe'
try:
    workspace_probe.write_text('ok', encoding='utf-8')
    workspace_writable = workspace_probe.exists()
    workspace_probe.unlink()
except OSError as exc:
    workspace_writable = False
print(json.dumps({
    'uacp_root_exists': root.exists(),
    'workspace_exists': workspace.exists(),
    'write_probe_blocked': write_blocked,
    'write_probe_error': write_error,
    'workspace_writable': workspace_writable,
}, sort_keys=True))
"""
    cmd = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        str(workspace),
        str(workspace),
        "--chdir",
        str(workspace),
        "python3",
        "-c",
        code,
        str(root),
        str(workspace),
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {"ok": False, "mechanism": "bwrap_readonly_root", "error": "bwrap not found"}
    except Exception as exc:
        return {"ok": False, "mechanism": "bwrap_readonly_root", "error": f"{type(exc).__name__}: {exc}"}
    parsed: dict[str, Any] = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception as exc:
            parsed = {"parse_error": f"{type(exc).__name__}: {exc}", "stdout": proc.stdout[-500:]}
    ok = (
        proc.returncode == 0
        and parsed.get("uacp_root_exists") is True
        and parsed.get("workspace_exists") is True
        and parsed.get("write_probe_blocked") is True
        and parsed.get("workspace_writable") is True
    )
    return {
        "ok": ok,
        "mechanism": "bwrap_readonly_root",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
        "probe": parsed,
    }


def _sandbox_check(args: Mapping[str, Any]) -> dict[str, Any]:
    policy = _policy()
    root = policy.uacp_root.resolve()
    workspace_raw = str(args.get("execution_workspace") or args.get("workdir") or args.get("cwd") or args.get("workspace") or "")
    tool_surface = str(args.get("tool_surface") or "exec.shell")
    backend = str(args.get("backend") or "local")
    mechanism = str(args.get("mechanism") or "bwrap_readonly_root")
    if missing_context := _required_uacp_context_missing(args):
        return {"ok": False, "error": f"missing UACP context field(s): {', '.join(missing_context)}"}
    authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
    if not authority:
        return {"ok": False, "error": "authority_artifact is required"}
    if not workspace_raw:
        return {"ok": False, "error": "execution_workspace, workdir, cwd, or workspace is required"}
    workspace = Path(workspace_raw).expanduser()
    relationship = _path_relationship(root, workspace)
    evidence: dict[str, Any] = {
        "tool_surface": tool_surface,
        "backend": backend,
        "mechanism": mechanism,
        "path_relationship": relationship,
        "standard_tool_path_verified": False,
        "standard_tool_path_reason": "Hermes standard terminal/execute_code path is not automatically wrapped by this evidence check.",
    }
    blockers: list[str] = []
    if not relationship["workspace_exists"] or not relationship["workspace_is_dir"]:
        blockers.append("execution workspace does not exist or is not a directory")
    if relationship["workspace_under_uacp_root"]:
        blockers.append("execution workspace is under UACP_ROOT")
    if relationship["uacp_root_under_workspace"]:
        blockers.append("UACP_ROOT is under execution workspace")
    if tool_surface == "exec.code_with_tool_proxy":
        blockers.append("execute_code backend containment is not proven by the Hermes adapter yet")
    if mechanism != "bwrap_readonly_root":
        blockers.append(f"unsupported containment mechanism: {mechanism}")
    if not blockers:
        evidence["bwrap_probe"] = _run_bwrap_readonly_probe(root, Path(relationship["workspace_resolved"]))
        if not evidence["bwrap_probe"].get("ok"):
            blockers.append("bwrap read-only root probe failed")
    containment_verified = not blockers
    return {
        "ok": True,
        "containment_verified": containment_verified,
        "allow_standard_tool_path": False,
        "verdict_reason": "bwrap containment mechanism is available for a wrapped execution surface" if containment_verified else "; ".join(blockers),
        "blockers": blockers,
        "evidence": evidence,
        "ttl_seconds": 60,
        "authority_artifact": authority,
    }


def _handle_uacp_sandbox_check(args: dict, **_: Any) -> str:
    """Return filesystem containment evidence for UACP-bound execution surfaces."""
    try:
        return json.dumps(_sandbox_check(args), ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"uacp_sandbox_check failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_contained_shell(args: dict, **_: Any) -> str:
    """Execute shell commands inside verified bwrap containment and return attestation evidence."""
    try:
        return json.dumps(_sandbox_contained_shell(args), ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"uacp_contained_shell failed: {type(exc).__name__}: {exc}"})


def _prune_expired_attestations(except_id: str | None = None) -> None:
    """Phase 1 / pc_3: prune expired entries from the in-memory cache.

    Called from every attestation validation so the cache cannot grow without
    bound across a long-running adapter session. The currently-validated
    attestation_id (if any) is preserved so the validator can report a
    specific "expired" reason rather than a generic "not found".
    """
    now = time.time()
    expired = [
        aid for aid, rec in _CONTAINED_SHELL_ATTESTATIONS.items()
        if aid != except_id
        and float(rec.get("expires_at") or 0.0)
        and float(rec.get("expires_at") or 0.0) <= now
    ]
    for aid in expired:
        _CONTAINED_SHELL_ATTESTATIONS.pop(aid, None)


def _validate_contained_shell_attestation(attestation_id: str | None, policy_version: str) -> tuple[bool, str]:
    _prune_expired_attestations(except_id=attestation_id)
    if not attestation_id:
        return True, "new attestation"
    record = _CONTAINED_SHELL_ATTESTATIONS.get(attestation_id)
    if record is None:
        return False, "attestation not found"
    now = time.time()
    expires_at = float(record.get("expires_at") or 0.0)
    if expires_at and expires_at <= now:
        return False, "attestation expired"
    if str(record.get("policy_version") or "") != policy_version:
        return False, "attestation policy version mismatch"
    if not bool(record.get("containment_verified")):
        return False, "attestation is not containment-verified"
    return True, "attestation valid"


def _run_bwrap_contained_shell(root: Path, workspace: Path, command: str, *, timeout: int = 60) -> dict[str, Any]:
    if not command.strip():
        return {"ok": False, "mechanism": "bwrap_readonly_root", "error": "command is required"}

    probe = _run_bwrap_readonly_probe(root, workspace, timeout=min(timeout, 20))
    if not probe.get("ok"):
        return {
            "ok": False,
            "mechanism": "bwrap_readonly_root",
            "write_probe_blocked": False,
            "bwrap_probe": probe,
            "error": "containment probe failed",
        }

    cmd = [
        "bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/tmp",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--bind",
        str(workspace),
        str(workspace),
        "--chdir",
        str(workspace),
        "--setenv",
        "HOME",
        str(workspace),
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "sh",
        "-lc",
        command,
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {"ok": False, "mechanism": "bwrap_readonly_root", "error": "bwrap not found", "write_probe_blocked": True, "bwrap_probe": probe}
    except Exception as exc:
        return {"ok": False, "mechanism": "bwrap_readonly_root", "error": f"{type(exc).__name__}: {exc}", "write_probe_blocked": True, "bwrap_probe": probe}

    attestation_id = uuid.uuid4().hex
    ttl_seconds = max(30, min(int(timeout) if timeout else 60, 300))
    expires_at = time.time() + ttl_seconds
    record = {
        "attestation_id": attestation_id,
        "expires_at": expires_at,
        "ttl_seconds": ttl_seconds,
        "policy_version": str(_policy().version),
        "workspace_resolved": str(workspace.resolve()),
        "uacp_root_resolved": str(root.resolve()),
        "containment_verified": True,
        "mechanism": "bwrap_readonly_root",
        "command": command,
        "exit_code": proc.returncode,
    }
    _CONTAINED_SHELL_ATTESTATIONS[attestation_id] = record

    write_probe = probe.get("probe") or {}
    write_probe_blocked = bool(write_probe.get("write_probe_blocked"))
    verdict_reason = "command executed inside bwrap read-only-root containment" if write_probe_blocked else "containment write probe did not block as expected"
    return {
        "ok": True,
        "containment_verified": bool(write_probe_blocked and probe.get("ok") is True),
        "allow_standard_tool_path": False,
        "verdict_reason": verdict_reason,
        "blockers": [] if write_probe_blocked else ["write probe did not block writes to UACP_ROOT"],
        "evidence": {
            "tool_surface": "exec.shell.contained",
            "backend": "local",
            "mechanism": "bwrap_readonly_root",
            "path_relationship": {
                "uacp_root_resolved": str(root.resolve()),
                "workspace_resolved": str(workspace.resolve()),
                "workspace_exists": workspace.exists(),
                "workspace_is_dir": workspace.is_dir(),
                "workspace_under_uacp_root": False,
                "uacp_root_under_workspace": False,
            },
            "write_probe_blocked": write_probe_blocked,
            "bwrap_probe": probe,
            "command": command,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-500:],
            "stderr_tail": proc.stderr[-500:],
            "attestation_id": attestation_id,
            "expires_at": expires_at,
            "ttl_seconds": ttl_seconds,
            "policy_version": str(_policy().version),
        },
        "attestation_id": attestation_id,
        "expires_at": expires_at,
        "ttl_seconds": ttl_seconds,
        "policy_version": str(_policy().version),
        "write_probe_blocked": write_probe_blocked,
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
        "exit_code": proc.returncode,
        "command": command,
    }


def _sandbox_contained_shell(args: Mapping[str, Any]) -> dict[str, Any]:
    policy = _policy()
    root = policy.uacp_root.resolve()
    authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
    command = str(args.get("command") or "")
    workspace_raw = str(args.get("workspace") or args.get("workdir") or args.get("cwd") or "")
    attestation_id = str(args.get("attestation_id") or "")
    if missing_context := _required_uacp_context_missing(args):
        return {"ok": False, "error": f"missing UACP context field(s): {', '.join(missing_context)}"}
    if not authority:
        return {"ok": False, "error": "authority_artifact is required"}
    if not workspace_raw:
        return {"ok": False, "error": "workspace, workdir, or cwd is required"}
    if not command:
        return {"ok": False, "error": "command is required"}
    workspace = Path(workspace_raw).expanduser()
    relationship = _path_relationship(root, workspace)
    blockers: list[str] = []
    if not relationship["workspace_exists"] or not relationship["workspace_is_dir"]:
        blockers.append("execution workspace does not exist or is not a directory")
    if relationship["workspace_under_uacp_root"]:
        blockers.append("execution workspace is under UACP_ROOT")
    if relationship["uacp_root_under_workspace"]:
        blockers.append("UACP_ROOT is under execution workspace")
    attestation_ok, attestation_reason = _validate_contained_shell_attestation(attestation_id or None, str(policy.version))
    if not attestation_ok and attestation_id:
        blockers.append(attestation_reason)
    if blockers:
        return {
            "ok": True,
            "containment_verified": False,
            "allow_standard_tool_path": False,
            "verdict_reason": "; ".join(blockers),
            "blockers": blockers,
            "evidence": {
                "tool_surface": "exec.shell.contained",
                "backend": "local",
                "mechanism": "bwrap_readonly_root",
                "path_relationship": relationship,
                "command": command,
                "attestation_id": attestation_id,
                "policy_version": str(policy.version),
            },
            "authority_artifact": authority,
        }
    result = _run_bwrap_contained_shell(root, workspace, command, timeout=int(args.get("timeout") or 60))
    result["authority_artifact"] = authority
    result["policy_version"] = str(policy.version)
    result["path_relationship"] = relationship
    if result.get("ok") is True and result.get("containment_verified") is True:
        result["verdict_reason"] = result.get("verdict_reason") or "command executed inside contained shell surface"
    return result



def _handle_uacp_gate_ledger_append(args: dict, **_: Any) -> str:
    """Append a single JSONL record to the run's gate ledger.

    Enforces append-only semantics: opens the file in append mode, writes
    exactly one record terminated by a newline, never truncates or seeks.
    The ledger path is fixed per run: state/gate-ledger/{run_id}.jsonl.
    Returns the byte offset of the appended record as proof.
    """
    try:
        policy = _policy()
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
        policy = _policy()
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
        policy = _policy()
        root = policy.uacp_root
        op = str(args.get("op") or "").strip().lower()
        if op not in {"register", "deregister"}:
            return json.dumps({"error": "uacp_run_registry_update: op must be 'register' or 'deregister'"})
        entry = args.get("entry") or {}
        if not isinstance(entry, dict):
            return json.dumps({"error": "uacp_run_registry_update: 'entry' must be a mapping"})
        run_id = str(entry.get("run_id") or "")
        from .kernel import _is_safe_run_id as _safe
        from .kernel import Heartgate as _HG
        if not _safe(run_id):
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
                cw = _HG._canon_write_path(w)
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
        policy = _policy()
        root = policy.uacp_root
        from .kernel import _is_safe_run_id as _safe
        run_id = str(args.get("uacp_run_id") or "")
        if not _safe(run_id):
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


def _handle_uacp_artifact_write(args: dict, **_: Any) -> str:
    try:
        policy = _policy()
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        target = _resolve_uacp_path(target_path, root)
        rel = target.relative_to(root)
        if not rel.parts:
            return json.dumps({"error": "target_path must point to an artifact file"})
        allowed_roots = {"plans", "proposals", "executions", "verification", "outputs", "knowledge"}
        forbidden_roots = {"state", "docs", "config"}
        top = rel.parts[0]
        if top in forbidden_roots:
            return json.dumps({"error": f"uacp_artifact_write may not write under {top}/"})
        if top not in allowed_roots:
            return json.dumps(
                {"error": "uacp_artifact_write target must be under plans/, proposals/, executions/, verification/, .outputs/, or knowledge/"}
            )
        if target.name in {"", ".", ".."}:
            return json.dumps({"error": "target_path must point to a file"})

        _write_uacp_file(target, content)
        return json.dumps(
            {
                "ok": True,
                "path": str(rel),
                "reason": reason,
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_artifact_write failed: {type(exc).__name__}: {exc}"})


def _validate_canonical_target(root: Path, target_path: str, *, allowed_top: str, suffixes: set[str]) -> tuple[Path, Path] | str:
    raw = Path(target_path)
    if raw.is_absolute():
        return "target_path must be UACP-root-relative"
    if any(part in {"", ".", ".."} for part in raw.parts):
        return "target_path must not contain empty, current, or parent path segments"
    if not raw.parts or raw.parts[0] != allowed_top:
        return f"target_path must be under {allowed_top}/"
    try:
        target = _resolve_uacp_path(target_path, root)
        rel = target.relative_to(root.resolve())
    except Exception as exc:
        return str(exc)
    if not rel.parts or rel.parts[0] != allowed_top:
        return f"target_path must resolve under {allowed_top}/"
    if target.name in {"", ".", ".."}:
        return "target_path must point to a file"
    if target.exists() and target.is_dir():
        return "target_path must point to a file, not a directory"
    if suffixes and target.suffix not in suffixes:
        return f"target_path must use one of these suffixes: {', '.join(sorted(suffixes))}"
    return target, rel


def _handle_uacp_doc_write(args: dict, **_: Any) -> str:
    """Write canonical UACP docs through an explicit governed docs boundary."""
    try:
        policy = _policy()
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        resolved = _validate_canonical_target(root, target_path, allowed_top="docs", suffixes={".md"})
        if isinstance(resolved, str):
            return json.dumps({"error": resolved})
        target, rel = resolved
        _write_uacp_file(target, content)
        return json.dumps(
            {
                "ok": True,
                "path": str(rel),
                "reason": reason,
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_doc_write failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_config_write(args: dict, **_: Any) -> str:
    """Write canonical UACP YAML config through an explicit governed config boundary."""
    try:
        policy = _policy()
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        resolved = _validate_canonical_target(root, target_path, allowed_top="config", suffixes={".yaml", ".yml"})
        if isinstance(resolved, str):
            return json.dumps({"error": resolved})
        target, rel = resolved
        _write_uacp_file(target, content)
        return json.dumps(
            {
                "ok": True,
                "path": str(rel),
                "reason": reason,
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_config_write failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_heartgate_check(args: dict, **_: Any) -> str:
    """Validate a UACP phase-transition artifact through the Heartgate boundary."""
    try:
        policy = _policy()
        root = policy.uacp_root
        transition_path = str(args.get("transition_path") or args.get("target_path") or "")
        if not transition_path:
            return json.dumps({"error": "transition_path is required"})
        if missing_context := _required_uacp_context_missing(args):
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing_context)}"})
        authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})

        target = _resolve_uacp_path(transition_path, root)
        rel = target.relative_to(root.resolve())
        allowed_transition_roots = {"state", "verification", "executions", "plans", "proposals", "outputs", "knowledge"}
        if not rel.parts or rel.parts[0] not in allowed_transition_roots:
            return json.dumps({"error": "transition_path must be under a managed UACP artifact/state directory"})
        if target.suffix not in {".yaml", ".yml"}:
            return json.dumps({"error": "transition_path must be a YAML file"})
        if not target.exists():
            return json.dumps({"error": "transition artifact not found"})

        decision = Heartgate.load(root).validate_transition_file(rel)
        return json.dumps(
            {
                "ok": not decision.blocks_transition,
                "decision": decision.decision,
                "reason": decision.reason,
                "blockers": decision.blockers,
                "warnings": decision.warnings,
                "path": str(rel),
                "authority_artifact": authority,
            },
            ensure_ascii=False,
        )
    except HeartgateError as exc:
        return json.dumps({"error": f"uacp_heartgate_check failed: HeartgateError: {exc}"})
    except Exception as exc:
        return json.dumps({"error": f"uacp_heartgate_check failed: {type(exc).__name__}: {exc}"})


def _write_tool_schema(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string"},
                "content": {"type": "string"},
                "reason": {"type": "string"},
                "authority_artifact": {"type": "string"},
                "workspace": {"type": "string"},
                "uacp_run_id": {"type": "string"},
                "uacp_phase": {"type": "string"},
                "policy_version": {"type": "string"},
                "declared_side_effects": {"type": "string"},
            },
            "required": [
                "target_path",
                "content",
                "reason",
                "authority_artifact",
                "workspace",
                "uacp_run_id",
                "uacp_phase",
                "policy_version",
                "declared_side_effects",
            ],
        },
    }


def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    ctx.register_tool(
        name="uacp_state_write",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_state_write",
            "description": "Write UACP runtime state through the governed state mutation boundary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "content": {"type": "string"},
                    "reason": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "target_path",
                    "content",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_state_write,
        description="Governed UACP state writer",
    )
    ctx.register_tool(
        name="uacp_run_registry_update",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_run_registry_update",
            "description": "Phase 3.2 narrow writer for state/run-registry.yaml (uacp-state exclusive). Supports op=register|deregister with a structured entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["register", "deregister"]},
                    "entry": {"type": "object"},
                    "reason": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "op",
                    "entry",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_run_registry_update,
        description="Phase 3.2 exclusive registry mutator",
    )
    ctx.register_tool(
        name="uacp_escalation_event",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_escalation_event",
            "description": "Phase 4.4 — emit an operator-facing escalation record to state/escalations/{run_id}.jsonl. Stub for autonomous-mode operator-notify; push-notify is Phase 5.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger": {"type": "string"},
                    "severity": {"type": "string", "enum": ["info", "warn", "block"]},
                    "reason": {"type": "string"},
                    "mode": {"type": "string", "enum": ["manual", "semi_auto", "supervised_auto", "full_auto"], "description": "Required — must match state.yaml#escalations.record_schema"},
                    "details": {"type": "object"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "trigger",
                    "severity",
                    "reason",
                    "mode",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_escalation_event,
        description="Phase 4.4 escalation-event writer",
    )
    ctx.register_tool(
        name="uacp_artifact_write",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_artifact_write",
            "description": "Write non-state UACP artifacts under approved artifact directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_path": {"type": "string"},
                    "content": {"type": "string"},
                    "reason": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "target_path",
                    "content",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_artifact_write,
        description="Governed UACP artifact writer",
    )
    ctx.register_tool(
        name="uacp_doc_write",
        toolset="uacp_guardian",
        schema=_write_tool_schema(
            "uacp_doc_write",
            "Write canonical UACP Markdown docs under docs/ through the governed docs boundary.",
        ),
        handler=_handle_uacp_doc_write,
        description="Governed UACP docs writer",
    )
    ctx.register_tool(
        name="uacp_config_write",
        toolset="uacp_guardian",
        schema=_write_tool_schema(
            "uacp_config_write",
            "Write canonical UACP YAML config under config/ through the governed config boundary.",
        ),
        handler=_handle_uacp_config_write,
        description="Governed UACP config writer",
    )
    ctx.register_tool(
        name="uacp_sandbox_check",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_sandbox_check",
            "description": "Verify filesystem containment evidence for UACP-bound shell/code execution surfaces.",
            "parameters": {
                "type": "object",
                "properties": {
                    "execution_workspace": {"type": "string"},
                    "workdir": {"type": "string"},
                    "cwd": {"type": "string"},
                    "tool_surface": {"type": "string"},
                    "backend": {"type": "string"},
                    "mechanism": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_sandbox_check,
        description="UACP filesystem containment evidence checker",
    )
    ctx.register_tool(
        name="uacp_contained_shell",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_contained_shell",
            "description": "Execute a bounded shell command inside verified bwrap read-only-root containment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "workspace": {"type": "string"},
                    "workdir": {"type": "string"},
                    "cwd": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "attestation_id": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "command",
                    "workspace",
                    "authority_artifact",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_contained_shell,
        description="UACP contained shell execution surface",
    )
    ctx.register_tool(
        name="uacp_gate_ledger_append",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_gate_ledger_append",
            "description": "Append a single JSONL record to the run's gate ledger (append-only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "gate": {"type": "string"},
                    "record": {"type": "object"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "gate",
                    "record",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_gate_ledger_append,
        description="UACP gate ledger append-only writer",
    )
    ctx.register_tool(
        name="uacp_heartgate_check",
        toolset="uacp_guardian",
        schema={
            "name": "uacp_heartgate_check",
            "description": "Validate a UACP phase-transition artifact through Heartgate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transition_path": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "transition_path",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
        },
        handler=_handle_uacp_heartgate_check,
        description="UACP Heartgate transition checker",
    )

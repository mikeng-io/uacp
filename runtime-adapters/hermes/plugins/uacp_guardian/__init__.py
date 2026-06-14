"""Hermes adapter for UACP Guardian runtime enforcement."""

from __future__ import annotations

import json
import subprocess
import sys
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

# Import runtime-neutral filesystem helpers from uacp-core.
from filesystem import _resolve_uacp_path, _write_uacp_file
from config import base_dir

# Add uacp-state/scripts to path so we can import state handlers.
_STATE_SCRIPTS = Path(__file__).resolve().parents[4] / "skills" / "uacp-state" / "scripts"
if str(_STATE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_STATE_SCRIPTS))

from state import (
    _handle_uacp_state_write,
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_registry_update,
    _handle_uacp_escalation_event,
    _validate_common_write_args,
    _required_uacp_context_missing,
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
            write_audit_record(decision.to_audit_record(event))
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



def _handle_uacp_artifact_write(args: dict, **_: Any) -> str:
    try:
        policy = _policy()
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        target = _resolve_uacp_path(target_path, base_dir(root))
        rel = target.relative_to(base_dir(root))
        if not rel.parts:
            return json.dumps({"error": "target_path must point to an artifact file"})
        allowed_roots = {"plans", "proposals", "executions", "verification", "resolutions", "knowledge"}
        forbidden_roots = {"state", "docs", "config"}
        top = rel.parts[0]
        if top in forbidden_roots:
            return json.dumps({"error": f"uacp_artifact_write may not write under {top}/"})
        if top not in allowed_roots:
            return json.dumps(
                {"error": "uacp_artifact_write target must be under plans/, proposals/, executions/, verification/, resolutions/, or knowledge/"}
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

        target = _resolve_uacp_path(transition_path, base_dir(root))
        rel = target.relative_to(base_dir(root))
        allowed_transition_roots = {"state", "verification", "executions", "plans", "proposals", "resolutions", "knowledge"}
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

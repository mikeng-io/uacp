"""Runtime-neutral UACP governed-tool handlers.

These are the 7 governed-tool handlers that previously lived in the Hermes
adapter (``runtime-adapters/hermes/plugins/uacp_guardian/__init__.py``):
``uacp_artifact_write``, ``uacp_doc_write``, ``uacp_config_write``,
``uacp_heartgate_check``, ``uacp_sandbox_check``, ``uacp_contained_shell``,
``uacp_oracle_query``. They are moved here so every runtime adapter (Hermes
today, an MCP server next) consumes the same single source of truth via the
``tool_specs`` registry.

Handler signature convention: ``(args: dict, **_) -> str`` (returns a JSON
string). Handlers are runtime-neutral: instead of a module-level policy
singleton they self-resolve the active policy via
``GuardianPolicy.load(args.get("workspace"))`` (mirroring the uacp-state
handlers), so they carry no per-process cached state and re-read UACP_ROOT on
each call.

Attestation cache (``_CONTAINED_SHELL_ATTESTATIONS``) is per-process. The
Hermes adapter and a future MCP server are separate processes, so a contained
shell attestation minted in one is not visible in the other. That is by design:
an attestation only grants the issuing process's pre_tool_call hook a
filesystem-containment pass, and each process validates against its own cache.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from config import base_dir
from contracts import _required_uacp_context_missing, _validate_common_write_args
from core import GuardianPolicy, Heartgate, HeartgateError
from filesystem import _resolve_uacp_path, _write_uacp_file


# Per-process in-memory attestation cache (see module docstring). Validated by
# `_validate_contained_shell_attestation`; pruned by `_prune_expired_attestations`.
_CONTAINED_SHELL_ATTESTATIONS: dict[str, dict[str, Any]] = {}


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
        return {
            "ok": False,
            "mechanism": "bwrap_readonly_root",
            "error": f"{type(exc).__name__}: {exc}",
        }
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
    policy = GuardianPolicy.load(args.get("workspace"))
    root = policy.uacp_root.resolve()
    workspace_raw = str(
        args.get("execution_workspace")
        or args.get("workdir")
        or args.get("cwd")
        or args.get("workspace")
        or ""
    )
    tool_surface = str(args.get("tool_surface") or "exec.shell")
    backend = str(args.get("backend") or "local")
    mechanism = str(args.get("mechanism") or "bwrap_readonly_root")
    if missing_context := _required_uacp_context_missing(args):
        return {
            "ok": False,
            "error": f"missing UACP context field(s): {', '.join(missing_context)}",
        }
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
        evidence["bwrap_probe"] = _run_bwrap_readonly_probe(
            root, Path(relationship["workspace_resolved"])
        )
        if not evidence["bwrap_probe"].get("ok"):
            blockers.append("bwrap read-only root probe failed")
    containment_verified = not blockers
    return {
        "ok": True,
        "containment_verified": containment_verified,
        "allow_standard_tool_path": False,
        "verdict_reason": "bwrap containment mechanism is available for a wrapped execution surface"
        if containment_verified
        else "; ".join(blockers),
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
        return json.dumps(
            {"ok": False, "error": f"uacp_sandbox_check failed: {type(exc).__name__}: {exc}"}
        )


def _handle_uacp_contained_shell(args: dict, **_: Any) -> str:
    """Execute shell commands inside verified bwrap containment and return attestation evidence."""
    try:
        return json.dumps(_sandbox_contained_shell(args), ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {"ok": False, "error": f"uacp_contained_shell failed: {type(exc).__name__}: {exc}"}
        )


def _prune_expired_attestations(except_id: str | None = None) -> None:
    """Phase 1 / pc_3: prune expired entries from the in-memory cache.

    Called from every attestation validation so the cache cannot grow without
    bound across a long-running adapter session. The currently-validated
    attestation_id (if any) is preserved so the validator can report a
    specific "expired" reason rather than a generic "not found".
    """
    now = time.time()
    expired = [
        aid
        for aid, rec in _CONTAINED_SHELL_ATTESTATIONS.items()
        if aid != except_id
        and float(rec.get("expires_at") or 0.0)
        and float(rec.get("expires_at") or 0.0) <= now
    ]
    for aid in expired:
        _CONTAINED_SHELL_ATTESTATIONS.pop(aid, None)


def _validate_contained_shell_attestation(
    attestation_id: str | None, policy_version: str
) -> tuple[bool, str]:
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


def _run_bwrap_contained_shell(
    root: Path, workspace: Path, command: str, *, timeout: int = 60, policy_version: str = ""
) -> dict[str, Any]:
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
        return {
            "ok": False,
            "mechanism": "bwrap_readonly_root",
            "error": "bwrap not found",
            "write_probe_blocked": True,
            "bwrap_probe": probe,
        }
    except Exception as exc:
        return {
            "ok": False,
            "mechanism": "bwrap_readonly_root",
            "error": f"{type(exc).__name__}: {exc}",
            "write_probe_blocked": True,
            "bwrap_probe": probe,
        }

    attestation_id = uuid.uuid4().hex
    ttl_seconds = max(30, min(int(timeout) if timeout else 60, 300))
    expires_at = time.time() + ttl_seconds
    record = {
        "attestation_id": attestation_id,
        "expires_at": expires_at,
        "ttl_seconds": ttl_seconds,
        "policy_version": policy_version,
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
    verdict_reason = (
        "command executed inside bwrap read-only-root containment"
        if write_probe_blocked
        else "containment write probe did not block as expected"
    )
    return {
        "ok": True,
        "containment_verified": bool(write_probe_blocked and probe.get("ok") is True),
        "allow_standard_tool_path": False,
        "verdict_reason": verdict_reason,
        "blockers": []
        if write_probe_blocked
        else ["write probe did not block writes to UACP_ROOT"],
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
            "policy_version": policy_version,
        },
        "attestation_id": attestation_id,
        "expires_at": expires_at,
        "ttl_seconds": ttl_seconds,
        "policy_version": policy_version,
        "write_probe_blocked": write_probe_blocked,
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
        "exit_code": proc.returncode,
        "command": command,
    }


def _sandbox_contained_shell(args: Mapping[str, Any]) -> dict[str, Any]:
    policy = GuardianPolicy.load(args.get("workspace"))
    root = policy.uacp_root.resolve()
    authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
    command = str(args.get("command") or "")
    workspace_raw = str(args.get("workspace") or args.get("workdir") or args.get("cwd") or "")
    attestation_id = str(args.get("attestation_id") or "")
    if missing_context := _required_uacp_context_missing(args):
        return {
            "ok": False,
            "error": f"missing UACP context field(s): {', '.join(missing_context)}",
        }
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
    attestation_ok, attestation_reason = _validate_contained_shell_attestation(
        attestation_id or None, str(policy.version)
    )
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
    result = _run_bwrap_contained_shell(
        root,
        workspace,
        command,
        timeout=int(args.get("timeout") or 60),
        policy_version=str(policy.version),
    )
    result["authority_artifact"] = authority
    result["policy_version"] = str(policy.version)
    result["path_relationship"] = relationship
    if result.get("ok") is True and result.get("containment_verified") is True:
        result["verdict_reason"] = (
            result.get("verdict_reason") or "command executed inside contained shell surface"
        )
    return result


def _handle_uacp_artifact_write(args: dict, **_: Any) -> str:
    try:
        policy = GuardianPolicy.load(args.get("workspace"))
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        target = _resolve_uacp_path(target_path, base_dir(root))
        rel = target.relative_to(base_dir(root))
        if not rel.parts:
            return json.dumps({"error": "target_path must point to an artifact file"})
        allowed_roots = {
            "plans",
            "proposals",
            "executions",
            "verification",
            "resolutions",
            "knowledge",
            "lessons",
            "brainstorm",
        }
        forbidden_roots = {"state", "docs", "config"}
        top = rel.parts[0]
        if top in forbidden_roots:
            return json.dumps({"error": f"uacp_artifact_write may not write under {top}/"})
        if top not in allowed_roots:
            return json.dumps(
                {
                    "error": "uacp_artifact_write target must be under plans/, proposals/, executions/, verification/, resolutions/, knowledge/, lessons/, or brainstorm/"
                }
            )
        if target.name in {"", ".", ".."}:
            return json.dumps({"error": "target_path must point to a file"})

        # CUT3 (unbypassable): a RELATION-plane MANIFEST kind must go through uacp_entity_write — the
        # typed, validate-on-write, auto-REGISTERING path (so the graph_projection gate sees it). The
        # raw writer neither validates nor registers, so a manifest doc written here would be invisible
        # to the gate (the activation bypass). Reject it HERE (handler level), because the Guardian
        # category block is bypassed by direct/MCP/test calls. Corpus roots (knowledge/, lessons/) and
        # any non-RELATION path resolve to no manifest kind -> still allowed.
        import re as _re

        from engines.domain import layout

        # Reject by the canonical PATH and by the DECLARED kind in the payload (Codex PR#8 P1): a
        # caller could otherwise write manifest CONTENT (`kind: uacp.proposal`) to a NON-template path
        # (e.g. proposals/{run_id}-x.yaml) to dodge the path check — that file escapes validate+register
        # yet still satisfies broad phase-exit globs (proposals/{run_id}*.yaml). Either signal of a
        # RELATION-plane manifest kind is refused.
        manifest_kind = layout.kind_for_relpath(str(rel))
        if not manifest_kind:
            m = _re.search(r"(?m)^\s*kind:\s*[\"']?(uacp\.[\w.]+)", content)
            if m:
                manifest_kind = m.group(1)
        if manifest_kind and layout.plane_of(manifest_kind) == layout.RELATION:
            return json.dumps(
                {
                    "error": f"uacp_artifact_write cannot write manifest kind '{manifest_kind}' "
                    f"({rel}); use uacp_entity_write (the typed, registering manifest write path)"
                }
            )

        existed_before = target.exists()
        _write_uacp_file(target, content)
        # Detection watermark (D24/D25) — FAIL-CLOSED (#5 / Codex P2 on #503-lesson):
        # a governed artifact with NO durable watermark would slip the require-record
        # gate, because an empty hash index reads as a legacy no-op (#4) — so it could
        # pass untrusted-yet-unflagged (the exact fail-open class this gate exists to
        # prevent). If the watermark cannot be persisted, the governed write FAILS; a
        # freshly-created artifact is rolled back so no unwatermarked file is left behind.
        run_id = str(args.get("uacp_run_id") or "")
        if run_id:
            try:
                from engines.domain.artifact_hashes import record_hash

                record_hash(root, run_id, str(rel), content)
            except Exception as exc:
                if not existed_before:
                    try:
                        target.unlink()
                    except Exception:
                        pass
                rollback = (
                    "write rolled back" if not existed_before else "existing artifact retained"
                )
                return json.dumps(
                    {
                        "error": f"uacp_artifact_write failed: watermark could not be persisted "
                        f"({type(exc).__name__}: {exc}); {rollback}"
                    }
                )
        return json.dumps(
            {
                "ok": True,
                "path": str(rel),
                "reason": reason,
                "authority_artifact": authority,
                "watermark": "recorded",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"uacp_artifact_write failed: {type(exc).__name__}: {exc}"})


def _handle_uacp_entity_write(args: dict, **_: Any) -> str:
    """Governed entity writer — the typed, validated, auto-REGISTERING manifest write path.

    Wraps engines.manifest.entity_writer.create_entity: serialize the entity, validate-on-write
    against its registered schema, persist + watermark, and REGISTER it into the run manifest (so
    the graph_projection gate actually sees it). The RELATION-plane guard, unknown-kind guard, ctx
    sanitization, atomic rollback and fail-closed watermark all live in create_entity — this handler
    only marshals tool args (kind / fields / optional per-kind ctx placeholders)."""
    try:
        workspace = str(args.get("workspace") or ".")
        run_id = str(args.get("uacp_run_id") or "").strip()
        kind = str(args.get("kind") or "").strip()
        fields = args.get("fields")
        ctx = args.get("ctx") or {}
        if not kind:
            return json.dumps({"error": "kind is required"})
        if not isinstance(fields, dict):
            return json.dumps({"error": "fields must be an object"})
        if not isinstance(ctx, dict):
            return json.dumps({"error": "ctx must be an object"})
        # Self-attesting governed writer: when invoked via MCP/direct, Guardian is NOT re-run, so the
        # handler must enforce the governed-context contract itself (Codex PR#7 P2) — same bar as the
        # other governed writers' _validate_common_write_args path.
        reason = str(args.get("reason") or "")
        authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
        if not run_id:
            return json.dumps({"error": "uacp_run_id is required"})
        if not reason:
            return json.dumps({"error": "reason is required"})
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})
        if missing := _required_uacp_context_missing(args):
            return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})

        from engines.manifest.entity_writer import create_entity

        result = create_entity(
            workspace, run_id, kind, fields, **{str(k): str(v) for k, v in ctx.items()}
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"uacp_entity_write failed: {type(exc).__name__}: {exc}"})


def _validate_canonical_target(
    root: Path, target_path: str, *, allowed_top: str, suffixes: set[str]
) -> tuple[Path, Path] | str:
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
        policy = GuardianPolicy.load(args.get("workspace"))
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        resolved = _validate_canonical_target(
            root, target_path, allowed_top="docs", suffixes={".md"}
        )
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
        policy = GuardianPolicy.load(args.get("workspace"))
        root = policy.uacp_root
        validated = _validate_common_write_args(args)
        if isinstance(validated, str):
            return json.dumps({"error": validated})
        target_path, content, reason, authority = validated

        resolved = _validate_canonical_target(
            root, target_path, allowed_top="config", suffixes={".yaml", ".yml"}
        )
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
        policy = GuardianPolicy.load(args.get("workspace"))
        root = policy.uacp_root
        transition_path = str(args.get("transition_path") or args.get("target_path") or "")
        if not transition_path:
            return json.dumps({"error": "transition_path is required"})
        if missing_context := _required_uacp_context_missing(args):
            return json.dumps(
                {"error": f"missing UACP context field(s): {', '.join(missing_context)}"}
            )
        authority = str(args.get("authority_artifact") or args.get("declared_authority") or "")
        if not authority:
            return json.dumps({"error": "authority_artifact is required"})

        target = _resolve_uacp_path(transition_path, base_dir(root))
        rel = target.relative_to(base_dir(root))
        allowed_transition_roots = {
            "state",
            "verification",
            "executions",
            "plans",
            "proposals",
            "resolutions",
            "knowledge",
        }
        if not rel.parts or rel.parts[0] not in allowed_transition_roots:
            return json.dumps(
                {"error": "transition_path must be under a managed UACP artifact/state directory"}
            )
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


def _oracle_query_schema() -> dict:
    """JSON schema for the uacp_oracle_query read-only governed tool."""
    return {
        "name": "uacp_oracle_query",
        "description": (
            "Read-only oracle retrieval aggregator. Returns prior-art packets from "
            "run-state, Honcho memory, and (when configured) semantic sources for the "
            "given phase and project. Classified as external.network_read — it "
            "performs a network read via Honcho when enabled; no mutations. Both "
            "external.network_read and read.local are unprotected, so the tool is "
            "never blocked (allow_with_audit)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "description": "Current UACP lifecycle phase (e.g. 'plan', 'propose').",
                },
                "project": {
                    "type": "string",
                    "description": "Project identifier to scope the retrieval.",
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional domain filter list.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional search query string.",
                },
            },
            "required": ["phase", "project"],
        },
    }


def _handle_uacp_oracle_query(args: dict, **_: Any) -> str:
    """Handler for the uacp_oracle_query read-only tool.

    Validates required args, calls the oracle aggregator, and serializes the
    result to JSON. Returns an error JSON string on validation failure.
    """
    phase = args.get("phase")
    project = args.get("project")

    if not phase:
        return json.dumps({"error": "missing required argument: phase"})
    if not project:
        return json.dumps({"error": "missing required argument: project"})

    try:
        from engines.oracle.aggregator import oracle_query

        result = oracle_query(
            workspace=GuardianPolicy.load(args.get("workspace")).uacp_root,
            phase=phase,
            project=project,
            domains=args.get("domains"),
            query=args.get("query", ""),
        )
        # Serialize ProviderPackets to plain dicts
        packets_out = []
        for p in result.get("packets", []):
            packets_out.append(
                {
                    "source": p.source,
                    "trust_class": p.trust_class.value,
                    "payload": p.payload,
                    "score": p.score,
                    "evidence_required": p.evidence_required,
                    "metadata": p.metadata,
                }
            )
        return json.dumps(
            {
                "packets": packets_out,
                "metadata": result.get("metadata", {}),
            }
        )
    except Exception as exc:
        return json.dumps({"error": f"oracle_query failed: {exc}"})


def _handle_uacp_corpus_write(args: dict, **_: Any) -> str:
    """Handler for the uacp_corpus_write governed tool (#119).

    The corpus writeback path (persist an authored OKF lesson/knowledge doc)
    previously existed ONLY inside the Oracle package, so a tool-surface-only agent
    could not do RESOLVE lesson extraction without reaching into internals. This
    exposes it on the governed surface. The agent authors the OKF doc; the tool
    delegates to the Oracle's single ``write_corpus`` entrypoint, which parses +
    persists through the governed artifact writer (Guardian-audited). ALL corpus
    (de)serialization + path knowledge stays inside engines.oracle — this handler
    never touches corpus internals, keeping the data-ownership boundary intact
    (tests/unit/uacp_oracle/test_corpus_boundary.py).
    """
    kind = str(args.get("kind") or "")
    okf = args.get("okf")
    # Accept the documented governed-writer authority alias declared_authority
    # (Guardian's make_event maps it; docs/runtime/runtime-enforcement.md) — mirror
    # _validate_common_write_args so uacp_corpus_write matches every other writer's
    # contract instead of rejecting an otherwise-valid alias call (Codex #147 P2).
    authority = args.get("authority_artifact") or args.get("declared_authority")
    if kind not in ("lesson", "knowledge"):
        return json.dumps({"error": "uacp_corpus_write: kind must be 'lesson' or 'knowledge'"})
    if not isinstance(okf, str) or not okf.strip():
        return json.dumps({"error": "uacp_corpus_write: okf (the OKF markdown) is required"})
    if not authority:
        return json.dumps({"error": "uacp_corpus_write: authority_artifact is required"})
    if missing := _required_uacp_context_missing(args):
        return json.dumps({"error": f"missing UACP context field(s): {', '.join(missing)}"})
    try:
        from engines.oracle import write_corpus

        result = write_corpus(
            GuardianPolicy.load(args.get("workspace")).uacp_root,
            kind=kind,
            okf=okf,
            run_id=str(args.get("uacp_run_id") or ""),
            phase=str(args.get("uacp_phase") or "resolve"),
            reason=str(args.get("reason") or ""),
            authority_artifact=str(authority),
        )
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": f"uacp_corpus_write failed: {type(exc).__name__}: {exc}"})

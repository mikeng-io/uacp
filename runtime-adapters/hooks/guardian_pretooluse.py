#!/usr/bin/env python3
"""UACP Guardian PreToolUse hook — Claude Code / Kimi Code companion.

Defense-in-depth shim. Reads a host PreToolUse payload as JSON on stdin, evaluates
it through the runtime-neutral Guardian kernel, and renders a host-shaped decision.
It is NOT the authoritative containment: the MCP server's governed handlers remain
the authority (they own the actual writers). This hook adds pre-call enforcement to
runtimes that drive UACP through the bare MCP tools — so a write targeting the
governed ``.uacp/`` namespace, or a governed-looking call without UACP context, is
denied before it reaches a tool.

Design decisions (see docs/runtime/cc-kimi-pretooluse-hook.md):
  D1 Fail-OPEN: malformed/unparseable stdin or an unexpected internal exception
     -> exit 0, NO stdout (allow), warn on stderr. The MCP governed handlers stay
     authoritative, so fail-open here never opens the writers.
  D2 Raw edits DEFER: host Edit/Write/MultiEdit/NotebookEdit map to the kernel
     file-write category (require_approval) so ordinary project edits pass through
     to the runtime's own prompt; the kernel still HARD-BLOCKS writes targeting
     ``.uacp/`` via its direct-write/root-touch rules.
  D3 Policy-load failure: block governed-looking calls, allow bare reads.
  D4 Phase source: env (UACP_RUN_ID/UACP_PHASE) first, else state/current.yaml ->
     run manifest current_phase. Degrade gracefully.
  D5: a deny holds even under permission_mode == "bypassPermissions".
  D6: documented as defense-in-depth atop the authoritative MCP handlers.

Output contract:
  block  -> exit 0 + stdout PreToolUse deny JSON (+ stderr reason). If the stdout
            write fails, exit 2 + stderr.
  allow/defer -> exit 0, NO stdout.
  malformed/crash -> exit 0, NO stdout, stderr warning (D1).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

# --- sys.path: make the runtime-neutral kernel importable -------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))


def _warn(msg: str) -> None:
    sys.stderr.write(f"[uacp-guardian-hook] {msg}\n")


def _read_stdin_json() -> Mapping[str, Any] | None:
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw or not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    return payload if isinstance(payload, Mapping) else None


def _extract_tool_name(payload: Mapping[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("toolName") or "")


def _extract_tool_args(payload: Mapping[str, Any]) -> dict[str, Any]:
    args = payload.get("tool_input")
    if not isinstance(args, Mapping):
        args = payload.get("toolInput")
    if not isinstance(args, Mapping):
        args = payload.get("input")
    return dict(args) if isinstance(args, Mapping) else {}


def _infer_profile(payload: Mapping[str, Any]) -> str:
    # Claude Code payloads carry permission_mode; Kimi payloads do not.
    if "permission_mode" in payload or "permissionMode" in payload:
        return "claude_code"
    return "kimi_code"


def _resolve_phase(root: Path) -> tuple[str, str]:
    """Resolve (uacp_run_id, uacp_phase) per D4.

    Env first (UACP_RUN_ID/UACP_PHASE). Else read <base>/state/current.yaml
    #active_run_id and #active_run_manifest, then that manifest's current_phase.
    Degrades gracefully: any missing/unreadable file yields empties (no crash).
    """
    run_id = os.getenv("UACP_RUN_ID", "").strip()
    phase = os.getenv("UACP_PHASE", "").strip()
    if run_id or phase:
        return run_id, phase
    try:
        import yaml  # PyYAML ships with the kernel's normal use; optional here.
        from config import base_dir

        base = base_dir(root)
        current_path = base / "state" / "current.yaml"
        if not current_path.is_file():
            return "", ""
        current = yaml.safe_load(current_path.read_text(encoding="utf-8")) or {}
        if not isinstance(current, Mapping):
            return "", ""
        run_id = str(current.get("active_run_id") or "")
        manifest_rel = str(current.get("active_run_manifest") or "")
        if not manifest_rel:
            return run_id, ""
        manifest_path = (base / manifest_rel).resolve()
        # Containment: the manifest must live under the governed base.
        if base.resolve() not in manifest_path.parents and manifest_path != base.resolve():
            return run_id, ""
        if not manifest_path.is_file():
            return run_id, ""
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        if isinstance(manifest, Mapping):
            phase = str(manifest.get("current_phase") or "")
        return run_id, phase
    except Exception:
        return run_id, phase


def _emit_deny(reason: str) -> int:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    _warn(f"deny: {reason}")
    try:
        sys.stdout.write(json.dumps(payload))
        sys.stdout.flush()
    except Exception as exc:  # stdout write failed -> exit 2 + stderr (per spec).
        _warn(f"failed to write deny decision to stdout: {exc}")
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--profile", choices=["claude", "kimi"], default=None)
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    payload = _read_stdin_json()
    if payload is None:
        # D1: malformed/unparseable stdin -> fail open (allow, no stdout).
        _warn("unparseable or empty stdin payload — failing open (allow)")
        return 0

    try:
        tool_name = _extract_tool_name(payload)
        tool_args = _extract_tool_args(payload)
        if args.profile == "claude":
            profile = "claude_code"
        elif args.profile == "kimi":
            profile = "kimi_code"
        else:
            profile = _infer_profile(payload)

        # Resolve root: explicit cwd from payload can hint, but resolve_uacp_root
        # honors UACP_ROOT/HERMES_HOME first (the canonical resolution).
        from core import GuardianPolicy, GuardianPolicyError, resolve_uacp_root

        root = resolve_uacp_root()

        run_id, phase = _resolve_phase(root)

        # Try to load policy. D3: on policy-load failure, block governed-looking
        # calls but allow bare reads (mirror Hermes _block_for_policy_error).
        try:
            policy = GuardianPolicy.load(root)
        except GuardianPolicyError as exc:
            return _policy_error_decision(tool_name, profile, str(exc))

        # Phase config for Layer B (per-phase admissibility). Degrade to empty.
        phase_config: dict[str, Any] = {}
        try:
            from engines.io import load_phase_transitions

            loaded = load_phase_transitions(root)
            if loaded.error is None and isinstance(loaded.value, dict):
                phase_config = loaded.value
        except Exception:
            phase_config = {}

        classification_map = _guardian_classification_map(root)

        # Inject the resolved run_id/phase into the args so the kernel sees the
        # active phase even when env is unset (the kernel reads uacp_run_id/
        # uacp_phase from args first). Do not overwrite an explicit arg value.
        if run_id and "uacp_run_id" not in tool_args:
            tool_args["uacp_run_id"] = run_id
        if phase and "uacp_phase" not in tool_args:
            tool_args["uacp_phase"] = phase

        # Workspace binding (D2): the kernel treats `workspace` touching the UACP
        # root as a UACP-binding signal. A host runtime's cwd is frequently the
        # repo root itself — which for a UACP-governed repo IS the UACP root — so
        # forwarding cwd-as-workspace would make EVERY ordinary edit look
        # UACP-bound. Instead, bind on the THING being acted on: set workspace to
        # the parent dir of the primary path arg, falling back to the payload cwd.
        #
        # IMPORTANT — this only governs the NO-ACTIVE-RUN case. Once a run is
        # active, the kernel's `is_uacp_bound` short-circuits on the presence of
        # uacp_run_id/uacp_phase (injected just above), so EVERY host write/exec
        # (Edit/Write/Bash) is UACP-bound and blocked for missing UACP context —
        # regardless of this workspace value. That is intended: native host tools
        # carry no UACP context, so during a governed run they must route through
        # the uacp_* governed writers (or the MCP server). The workspace rebind
        # matters only outside a run, where it lets an ordinary project-file edit
        # defer to the runtime's normal approval while a write targeting the
        # governed .uacp/ namespace still hard-blocks (its target path is under
        # root, detected independently of workspace).
        if "workspace" not in tool_args:
            primary = ""
            for key in ("file_path", "path", "target_path", "notebook_path"):
                value = tool_args.get(key)
                if isinstance(value, str) and value:
                    primary = value
                    break
            cwd = str(payload.get("cwd") or "")
            if primary:
                try:
                    tool_args["workspace"] = str(Path(primary).expanduser().parent)
                except Exception:
                    tool_args["workspace"] = cwd
            elif cwd:
                tool_args["workspace"] = cwd

        from hook_kernel import evaluate_pre_tool_call

        decision = evaluate_pre_tool_call(
            tool_name=tool_name,
            args=tool_args,
            runtime=profile,
            adapter="uacp_pretooluse_hook",
            policy=policy,
            phase_config=phase_config,
            self_attesting=policy.self_attesting_tools,
            profile=profile,
            classification_map=classification_map,
            normalize=True,
        )

        # D5: a deny holds regardless of permission_mode (we never short-circuit
        # allow on bypassPermissions — the decision is the kernel's, full stop).
        if decision.blocks_execution:
            reason = f"UACP Guardian blocked {decision.category}: {decision.reason}"
            return _emit_deny(reason)
        # allow / allow_with_audit / require_approval -> defer to the runtime.
        return 0
    except Exception as exc:  # D1: any unexpected internal error -> fail open.
        _warn(f"internal error — failing open (allow): {type(exc).__name__}: {exc}")
        return 0


def _guardian_classification_map(root: Path) -> dict[str, Any]:
    try:
        from config import get_config

        return dict(get_config(root).model_dump().get("guardian", {}))
    except Exception:
        return {}


def _policy_error_decision(tool_name: str, profile: str, message: str) -> int:
    """D3: block governed-looking calls on policy-load failure; allow bare reads.

    Mirrors Hermes _block_for_policy_error: bare read tools (host Read/Grep/…,
    kernel read_file/search_files) pass; everything else (writers, exec, governed
    uacp_* tools) is denied. We normalize with an empty classification map (the
    config could not be trusted) and treat the well-known read names as the
    allowlist.
    """
    bare_reads = {
        "Read", "Grep", "Glob", "LS", "NotebookRead",  # host names
        "read_file", "search_files",  # kernel names
    }
    if tool_name in bare_reads:
        _warn(f"policy load failed but '{tool_name}' is a bare read — allowing: {message}")
        return 0
    return _emit_deny(f"UACP Guardian blocked external.unknown_mutator: {message}")


if __name__ == "__main__":
    raise SystemExit(main())

"""Hermes adapter for UACP Guardian runtime enforcement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .kernel import (
    Guardian,
    GuardianDecision,
    GuardianEvent,
    GuardianPolicy,
    GuardianPolicyError,
    make_event,
    write_audit_record,
)


_POLICY: GuardianPolicy | None = None
_POLICY_ERROR: str = ""


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
    return Guardian(policy).evaluate(event)


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
    resolved = (root / path).resolve(strict=False)
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
                {"error": "uacp_artifact_write target must be under plans/, proposals/, executions/, verification/, outputs/, or knowledge/"}
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

"""Hermes adapter for UACP Guardian runtime enforcement.

The governed-tool handlers and their JSON schemas are now runtime-neutral and
live in uacp-core (``governed_handlers`` + ``tool_specs``). This adapter is the
Hermes-specific binding layer: it owns the policy singleton, the phase-config
cache, the pre/post tool-call hooks, and the filesystem-guard wiring, and it
registers the neutral tool specs into the Hermes plugin context. The handler
objects are imported (and re-exported) from the neutral layer so existing tests
that reference them on this module — including identity assertions — keep
working.
"""

from __future__ import annotations

import sys
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

# Add uacp-state/scripts to path so we can import state handlers.
_STATE_SCRIPTS = Path(__file__).resolve().parents[4] / "skills" / "uacp-state" / "scripts"
if str(_STATE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_STATE_SCRIPTS))

# Add uacp-core/scripts to path so we can import the neutral handler/registry.
_CORE_SCRIPTS = Path(__file__).resolve().parents[4] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

# Governed-tool handlers + the per-process attestation state are now neutral
# (uacp-core). Re-export the handler symbols so callers/tests that reference
# them as `uacp_guardian._handle_*` (including handler-identity assertions)
# keep working — the registered handler IS this same imported object.
from governed_handlers import (  # noqa: F401  (re-exported for tests)
    _CONTAINED_SHELL_ATTESTATIONS,
    _handle_uacp_artifact_write,
    _handle_uacp_config_write,
    _handle_uacp_contained_shell,
    _handle_uacp_doc_write,
    _handle_uacp_heartgate_check,
    _handle_uacp_oracle_query,
    _handle_uacp_sandbox_check,
    _validate_contained_shell_attestation,
)
from tool_specs import hermes_schema, tool_specs

# State handlers stay sourced from uacp-state; re-exported here for tests.
from state import (  # noqa: F401  (re-exported for tests)
    _handle_uacp_state_write,
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_registry_update,
    _handle_uacp_escalation_event,
)


_POLICY: GuardianPolicy | None = None
_POLICY_ERROR: str = ""
_PHASE_CONFIG: dict[str, Any] | None = None
# _CONTAINED_SHELL_ATTESTATIONS now lives in governed_handlers (neutral) and is
# imported above; the adapter's pre_tool_call hook validates against that single
# per-process cache via the imported _validate_contained_shell_attestation.


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
        from engines.io import load_phase_transitions
        loaded = load_phase_transitions(_policy().uacp_root)
        if loaded.error is not None or not isinstance(loaded.value, dict):
            _PHASE_CONFIG = {}
        else:
            _PHASE_CONFIG = loaded.value
    except Exception:
        _PHASE_CONFIG = {}
    return _PHASE_CONFIG

# Self-attesting tools are declared in `config/uacp.toml [guardian]` under
# `self_attesting_tools.names` (moved out of adapter code in Phase 1 / pc_1 to
# remove the hidden authority list flagged by the Phase 0 Codex review;
# migrated from legacy guardian-policy.yaml to uacp.toml in config-collapse Slice 3).
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
        `self_attesting_tools` list — see config/uacp.toml [guardian]).
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
        # Resolve the policy version from the same root the attestation was
        # minted under (uacp_contained_shell loads policy from args["workspace"]).
        # Using _policy() here (the env-rooted singleton) would reject a valid
        # attestation whenever the workspace root's schema_version differs from
        # the env root's — a fail-closed mint/validate mismatch. Match the mint.
        policy_version = str(GuardianPolicy.load(args.get("workspace")).version)
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


def register(ctx) -> None:
    """Register the Guardian hooks and the 11 governed tools into Hermes.

    The tools are sourced from the runtime-neutral ``tool_specs()`` registry;
    each spec's schema is reproduced in the exact wrapped Hermes wire form via
    ``hermes_schema(spec)``, and the registered handler IS the same callable
    object exported from the neutral layer (handler identity preserved).
    """
    ctx.register_hook("pre_tool_call", on_pre_tool_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    for spec in tool_specs():
        ctx.register_tool(
            name=spec.name,
            toolset=spec.toolset,
            schema=hermes_schema(spec),
            handler=spec.handler,
            description=spec.description,
        )


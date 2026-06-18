"""Runtime-neutral PreToolUse hook kernel.

Shared, framework-free logic behind the Claude Code / Kimi Code Guardian
PreToolUse companion (``runtime-adapters/hooks/guardian_pretooluse.py``) and the
Hermes ``uacp_guardian`` adapter. Imports only from ``core``/``config`` — never a
host runtime — exactly like ``governed_handlers.py``.

Two responsibilities:

1. :func:`normalize_tool_name` — rewrite a host runtime's native tool name into a
   KERNEL tool name the Guardian classifier already understands. Host runtimes
   name their tools ``Read``/``Bash``/``Edit``/… and namespace MCP tools as
   ``mcp__<server>__<tool>`` (Claude Code) or ``mcp_<server>_<tool>`` (Hermes).
   The raw kernel knows none of those, so without normalization every host read
   tool would fall through to ``external.unknown_mutator`` (protected) and be
   blocked during an active run.

2. :func:`evaluate_pre_tool_call` — the shared pre-tool-call decision: normalize,
   compute filesystem-guard verification, build the event, evaluate against the
   Guardian, write the audit record when required, and return the decision.

This module is defense-in-depth atop the authoritative MCP governed handlers; it
never opens a governed writer on its own.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from core import (
    Guardian,
    GuardianDecision,
    GuardianPolicy,
    make_event,
    write_audit_record,
)

# Claude Code MCP tool naming: ``mcp__<server>__<tool>`` with an optional
# ``plugin_<x>_`` prefix on the server segment (plugin-provided MCP servers).
_CC_MCP_RE = re.compile(r"^mcp__(?:plugin_[^_]+_)?(?P<server>[^_]+)__(?P<tool>.+)$")
# Hermes MCP tool naming: ``mcp_<server>_<tool>``.
_HERMES_MCP_RE = re.compile(r"^mcp_(?P<server>[^_]+)_(?P<tool>.+)$")


def _kernel_tool_classification(classification_map: Mapping[str, Any]) -> Mapping[str, Any]:
    tc = classification_map.get("tool_classification") if classification_map else None
    return tc if isinstance(tc, Mapping) else {}


def normalize_tool_name(raw: str, profile: str, classification_map: Mapping[str, Any]) -> str:
    """Normalize a host tool name to a kernel tool name.

    Stage 1 — MCP de-namespacing. Strip Claude Code ``mcp__(plugin_<x>_)?<server>__<tool>``
    and Hermes ``mcp_<server>_<tool>`` wrappers. If the recovered tool is a
    ``uacp_*`` tool the kernel classification knows, return the bare ``uacp_*``
    name. Otherwise leave the name namespaced so it classifies as
    ``runtime.extension`` (the unknown-MCP default).

    Stage 2 — host map. Map via ``[guardian.host_tool_classification.<profile>]``;
    an unmapped name is returned unchanged.

    ``classification_map`` is the ``[guardian]`` dict (it carries both
    ``tool_classification`` and ``host_tool_classification``).
    """
    if not raw:
        return raw

    # Stage 1: MCP de-namespacing.
    if raw.startswith("mcp_"):
        match = _CC_MCP_RE.match(raw) or _HERMES_MCP_RE.match(raw)
        if match:
            tool = match.group("tool")
            kernel_tc = _kernel_tool_classification(classification_map)
            if tool.startswith("uacp_") and tool in kernel_tc:
                return tool
        # Non-UACP MCP tool (or unparseable mcp_ name): leave namespaced so the
        # kernel classifies it as runtime.extension.
        return raw

    # Stage 2: host map for the profile.
    host_map = {}
    if classification_map:
        htc = classification_map.get("host_tool_classification")
        if isinstance(htc, Mapping):
            profile_map = htc.get(profile)
            if isinstance(profile_map, Mapping):
                host_map = profile_map
    mapped = host_map.get(raw)
    if isinstance(mapped, str) and mapped:
        return mapped
    return raw


def evaluate_pre_tool_call(
    *,
    tool_name: str,
    args: Mapping[str, Any] | None,
    runtime: str,
    adapter: str,
    session_id: str = "",
    task_id: str = "",
    tool_call_id: str = "",
    policy: GuardianPolicy,
    phase_config: Mapping[str, Any] | None,
    self_attesting: frozenset[str] | set[str],
    profile: str,
    classification_map: Mapping[str, Any],
    normalize: bool = True,
    tool_provider: str = "",
    verify_attestation: Callable[[str, Mapping[str, Any] | None], bool] | None = None,
) -> GuardianDecision:
    """Shared pre-tool-call evaluation.

    Normalizes the host tool name (when ``normalize`` is True — the hook path),
    computes ``filesystem_guard_verified``, builds the Guardian event (carrying
    ``runtime``/``adapter`` for the audit record), evaluates it against
    ``Guardian(policy, phase_config)``, writes the audit record when the decision
    requires it, and returns the decision.

    ``filesystem_guard_verified`` is True when the (normalized) name is in
    ``self_attesting``; else if ``verify_attestation`` is provided, its result;
    else False. This mirrors the Hermes adapter's ``_filesystem_guard_verified``.

    The Hermes adapter passes ``normalize=False`` plus its own ``tool_provider``
    so its established classification (incl. mcp_/plugin provenance) is preserved
    byte-for-byte; the hook shim leaves ``normalize=True`` so host tool names are
    rewritten to kernel names before classify() runs.
    """
    args = args or {}
    if normalize:
        resolved = normalize_tool_name(tool_name, profile, classification_map)
    else:
        resolved = tool_name

    if resolved in self_attesting:
        fs_verified = True
    elif verify_attestation is not None:
        fs_verified = bool(verify_attestation(resolved, args))
    else:
        fs_verified = False

    event = make_event(
        tool_name=resolved,
        args=args,
        event_type="pre_tool_call",
        tool_provider=tool_provider,
        task_id=task_id,
        session_id=session_id,
        tool_call_id=tool_call_id,
        filesystem_guard_verified=fs_verified,
        runtime=runtime,
        adapter=adapter,
    )
    decision = Guardian(policy, phase_config=dict(phase_config or {})).evaluate(event)
    if decision.audit_required:
        write_audit_record(decision.to_audit_record(event))
    return decision

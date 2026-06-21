"""Guardian event construction.

Moved verbatim out of ``core.py`` (Phase A1 of the core decomposition,
design/graph-engine node 31). ``make_event`` builds a ``GuardianEvent`` from a
tool call, filling UACP context from explicit args then the environment;
``infer_tool_provider`` derives a broad provider category without importing a
host runtime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from .models import GuardianEvent


def infer_tool_provider(tool_name: str, explicit_provider: str = "") -> str:
    """Infer a broad provider category without importing a host runtime.

    Runtime adapters may pass a precise ``explicit_provider`` after consulting
    their own tool registries. The neutral kernel intentionally avoids importing
    Hermes modules so it can be reused by non-Hermes adapters.
    """
    if tool_name.startswith("mcp_"):
        return "mcp"
    if explicit_provider and explicit_provider != "core":
        return explicit_provider
    return "core"


def make_event(
    *,
    tool_name: str,
    args: Mapping[str, Any] | None = None,
    event_type: str = "pre_tool_call",
    tool_provider: str = "",
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    filesystem_guard_verified: bool = False,
    runtime: str = "hermes",
    adapter: str = "uacp_guardian",
) -> GuardianEvent:
    tool_args = dict(args or {})
    provider = infer_tool_provider(tool_name, tool_provider)
    return GuardianEvent(
        runtime=runtime,
        adapter=adapter,
        event_type=event_type,
        tool_provider=provider,
        tool_name=tool_name,
        tool_args=tool_args,
        task_id=task_id,
        session_id=session_id,
        tool_call_id=tool_call_id,
        workspace=str(tool_args.get("workspace") or os.getenv("UACP_WORKSPACE") or os.getcwd()),
        uacp_run_id=str(tool_args.get("uacp_run_id") or os.getenv("UACP_RUN_ID") or ""),
        uacp_phase=str(tool_args.get("uacp_phase") or os.getenv("UACP_PHASE") or ""),
        policy_version=str(
            tool_args.get("policy_version") or os.getenv("UACP_GUARDIAN_POLICY_VERSION") or ""
        ),
        declared_authority=str(
            tool_args.get("declared_authority")
            or tool_args.get("authority_artifact")
            or os.getenv("UACP_DECLARED_AUTHORITY")
            or ""
        ),
        declared_side_effects=(
            tool_args.get("declared_side_effects")
            if "declared_side_effects" in tool_args
            else os.getenv("UACP_DECLARED_SIDE_EFFECTS", "")
        ),
        kanban_task_id=str(
            tool_args.get("kanban_task_id") or os.getenv("HERMES_KANBAN_TASK") or ""
        ),
        kanban_run_id=str(
            tool_args.get("kanban_run_id") or os.getenv("HERMES_KANBAN_RUN_ID") or ""
        ),
        filesystem_guard_verified=filesystem_guard_verified,
    )

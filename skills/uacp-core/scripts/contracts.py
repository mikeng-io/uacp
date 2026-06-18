"""Runtime-neutral validation contracts for UACP governed-tool handlers.

These are PURE validators shared across the governed-tool handlers in
``state.py`` (uacp-state) and ``governed_handlers.py`` (uacp-core). They were
originally defined in ``skills/uacp-state/scripts/state.py``; they live here in
uacp-core so the neutral ``governed_handlers`` module can consume them without
uacp-core importing from uacp-state (which would reverse the layer boundary —
state depends on core, never the other way around).

No framework-specific imports; no policy or filesystem side effects.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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

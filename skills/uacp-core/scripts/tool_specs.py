"""Runtime-neutral registry of UACP governed tools.

Single source of truth for the 11 governed tools. Both the Hermes adapter
(today) and a future MCP server consume ``tool_specs()`` rather than each
re-declaring tool names, schemas, and handler bindings — true DRY.

Each :class:`ToolSpec` carries:
  * ``name`` — the governed-tool name.
  * ``description`` — short human description (matches the Hermes
    ``register_tool(..., description=...)`` argument, NOT the JSON-schema
    ``description``).
  * ``input_schema`` — the BARE JSON-schema dict (the ``parameters`` object,
    i.e. ``{"type": "object", "properties": {...}, "required": [...]}``), not
    wrapped in a name/description envelope.
  * ``handler`` — the imported callable, signature ``(args: dict, **_) -> str``.
  * ``toolset`` — registration toolset (currently all ``"uacp_guardian"``).
  * ``read_only`` — True for read-only tools (oracle/heartgate/sandbox checks),
    False for writers (including uacp_contained_shell, which mints state).

The 4 state handlers are pulled from ``state`` (uacp-state); the 7 others from
``governed_handlers`` (uacp-core). The 11 input schemas below are the canonical
copies — the Hermes ``register()`` reproduces its exact wire form via
``hermes_schema()``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# uacp-state/scripts must be importable for the 4 state handlers.
_STATE_SCRIPTS = Path(__file__).resolve().parents[2] / "uacp-state" / "scripts"
if str(_STATE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_STATE_SCRIPTS))

from governed_handlers import (  # noqa: E402  (import follows sys.path setup)
    _handle_uacp_artifact_write,
    _handle_uacp_config_write,
    _handle_uacp_contained_shell,
    _handle_uacp_doc_write,
    _handle_uacp_heartgate_check,
    _handle_uacp_oracle_query,
    _handle_uacp_sandbox_check,
    _oracle_query_schema,
    _write_tool_schema,
)
from state import (  # noqa: E402  (import follows sys.path setup)
    _handle_uacp_escalation_event,
    _handle_uacp_gate_ledger_append,
    _handle_uacp_run_registry_update,
    _handle_uacp_state_write,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]
    toolset: str = "uacp_guardian"
    read_only: bool = False
    # The JSON-schema-level description (the ``description`` inside the wrapped
    # Hermes schema). It differs from ``description`` (the short register_tool
    # label) for every governed tool, so it is carried explicitly to reproduce
    # the exact wire form. Defaults to ``description`` when unset.
    schema_description: str = ""

    def __post_init__(self) -> None:
        if not self.schema_description:
            object.__setattr__(self, "schema_description", self.description)


def hermes_schema(spec: ToolSpec) -> dict[str, Any]:
    """Reproduce the exact wrapped schema form the Hermes adapter registers.

    Hermes wraps the bare JSON schema as
    ``{"name": ..., "description": ..., "parameters": <input_schema>}`` where
    the wrapped ``description`` is the JSON-schema-level description
    (``spec.schema_description``), distinct from ``spec.description`` (the
    short register_tool label).
    """
    return {
        "name": spec.name,
        "description": spec.schema_description,
        "parameters": spec.input_schema,
    }


# Shared "common write args" schema body, reproduced verbatim from the Hermes
# adapter's inline schemas for uacp_state_write / uacp_artifact_write.
def _common_write_schema() -> dict[str, Any]:
    return {
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
    }


def tool_specs() -> list[ToolSpec]:
    """Return the 11 governed-tool specs (single source of truth)."""
    return [
        ToolSpec(
            name="uacp_state_write",
            description="Governed UACP state writer",
            schema_description="Write UACP runtime state through the governed state mutation boundary.",
            input_schema=_common_write_schema(),
            handler=_handle_uacp_state_write,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_run_registry_update",
            description="Phase 3.2 exclusive registry mutator",
            schema_description="Phase 3.2 narrow writer for state/run-registry.yaml (uacp-state exclusive). Supports op=register|deregister with a structured entry.",
            input_schema={
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
            handler=_handle_uacp_run_registry_update,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_escalation_event",
            description="Phase 4.4 escalation-event writer",
            schema_description="Phase 4.4 — emit an operator-facing escalation record to state/escalations/{run_id}.jsonl. Stub for autonomous-mode operator-notify; push-notify is Phase 5.",
            input_schema={
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
            handler=_handle_uacp_escalation_event,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_artifact_write",
            description="Governed UACP artifact writer",
            schema_description="Write non-state UACP artifacts under approved artifact directories.",
            input_schema=_common_write_schema(),
            handler=_handle_uacp_artifact_write,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_doc_write",
            description="Governed UACP docs writer",
            schema_description="Write canonical UACP Markdown docs under docs/ through the governed docs boundary.",
            input_schema=_write_tool_schema(
                "uacp_doc_write",
                "Write canonical UACP Markdown docs under docs/ through the governed docs boundary.",
            )["parameters"],
            handler=_handle_uacp_doc_write,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_config_write",
            description="Governed UACP config writer",
            schema_description="Write canonical UACP YAML config under config/ through the governed config boundary.",
            input_schema=_write_tool_schema(
                "uacp_config_write",
                "Write canonical UACP YAML config under config/ through the governed config boundary.",
            )["parameters"],
            handler=_handle_uacp_config_write,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_sandbox_check",
            description="UACP filesystem containment evidence checker",
            schema_description="Verify filesystem containment evidence for UACP-bound shell/code execution surfaces.",
            input_schema={
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
            handler=_handle_uacp_sandbox_check,
            read_only=True,
        ),
        ToolSpec(
            name="uacp_contained_shell",
            description="UACP contained shell execution surface",
            schema_description="Execute a bounded shell command inside verified bwrap read-only-root containment.",
            input_schema={
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
            handler=_handle_uacp_contained_shell,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_gate_ledger_append",
            description="UACP gate ledger append-only writer",
            schema_description="Append a single JSONL record to the run's gate ledger (append-only).",
            input_schema={
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
            handler=_handle_uacp_gate_ledger_append,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_heartgate_check",
            description="UACP Heartgate transition checker",
            schema_description="Validate a UACP phase-transition artifact through Heartgate.",
            input_schema={
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
            handler=_handle_uacp_heartgate_check,
            read_only=True,
        ),
        ToolSpec(
            name="uacp_oracle_query",
            description="UACP Oracle read-only retrieval aggregator",
            schema_description=_oracle_query_schema()["description"],
            input_schema=_oracle_query_schema()["parameters"],
            handler=_handle_uacp_oracle_query,
            read_only=True,
        ),
    ]

"""Runtime-neutral registry of UACP governed tools.

Single source of truth for the 12 governed tools. Both the Hermes adapter
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

The 4 state handlers are pulled from ``state`` (uacp-state); the 8 others from
``governed_handlers`` (uacp-core). The 12 input schemas below are the canonical
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
    _handle_uacp_entity_write,
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


# uacp_entity_write: the TYPED, auto-registering manifest write path. Instead of a raw
# target_path/content blob, it takes the entity `kind` + `fields` (+ optional per-kind `ctx`
# placeholders) and routes through engines.manifest.entity_writer.create_entity, which validates,
# watermarks, AND registers the artifact into the run manifest (so the graph_projection gate sees it).
def _entity_write_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "description": (
                    "The entity kind to write. Must be a RELATION-plane kind from the layout registry. "
                    "Lifecycle YAML kinds: uacp.triage, uacp.proposal, uacp.proposal_package_selection, "
                    "uacp.intent (Markdown), uacp.convergence_budget, uacp.plan_package_selection, "
                    "uacp.scope, uacp.phase_intent_verification_contract, uacp.execution_checkpoint, "
                    "uacp.investigation_entry, uacp.verification_package, uacp.verify_resolve_readiness, "
                    "uacp.evidence_disposition (Markdown), uacp.piv_assessment, uacp.resolve_package, "
                    "uacp.resolve_closure, uacp.lessons. "
                    "Generative-gate check kinds (frozen per run): uacp.check.field_present, "
                    "uacp.check.field_equals, uacp.check.edge_exists, uacp.check.artifact_integrity, "
                    "uacp.check.obligation_satisfied, uacp.check.symbol_resolves, uacp.check.behavioral. "
                    "STATE-plane kinds (run_manifest, run_registry, current_state) are rejected — use the state writers."
                ),
            },
            "fields": {"type": "object"},
            "ctx": {
                "type": "object",
                "description": (
                    "Per-kind path placeholders. Required for multi-instance kinds: "
                    "uacp.check.* requires {\"seq\": \"N\"} (1-based counter per check); "
                    "uacp.execution_checkpoint and uacp.investigation_entry likewise require {\"seq\": \"N\"}. "
                    "Omitting a required placeholder is an error."
                ),
            },
            "reason": {"type": "string"},
            "authority_artifact": {"type": "string"},
            "workspace": {"type": "string"},
            "uacp_run_id": {"type": "string"},
            "uacp_phase": {"type": "string"},
            "policy_version": {"type": "string"},
            "declared_side_effects": {"type": "string"},
        },
        "required": [
            "kind",
            "fields",
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
    """Return the 12 governed-tool specs (single source of truth)."""
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
                    "op": {
                        "type": "string",
                        "enum": ["register", "deregister"],
                        "description": "'register' adds an active_runs[] entry; 'deregister' removes it by run_id.",
                    },
                    "entry": {
                        "type": "object",
                        "description": (
                            "For register: must include run_id (string, must equal caller uacp_run_id), "
                            "phase (string), write_paths (list of UACP-root-relative strings the run may write), "
                            "scope_artifact_path (string), started_at (ISO timestamp). "
                            "For deregister: only run_id is required."
                        ),
                    },
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
                    "mode": {
                        "type": "string",
                        "enum": ["manual", "semi_auto", "supervised_auto", "full_auto"],
                        "description": "Required — must match state.yaml#escalations.record_schema",
                    },
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
            name="uacp_entity_write",
            description="Governed UACP entity writer (typed, validated, auto-registering)",
            schema_description=(
                "Write a typed UACP manifest entity by kind+fields: validates-on-write, watermarks, "
                "and registers it into the run manifest (the graph-projection write path)."
            ),
            input_schema=_entity_write_schema(),
            handler=_handle_uacp_entity_write,
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
                    "command": {
                        "type": "string",
                        "description": (
                            "Shell string (passed to 'sh -lc') executed inside bwrap read-only-root "
                            "containment. The workspace dir is the only writable bind-mount; the root "
                            "filesystem is read-only. PATH is scrubbed to /usr/bin:/bin."
                        ),
                    },
                    "workspace": {
                        "type": "string",
                        "description": (
                            "The execution workspace — bind-mounted writable and used as the command's "
                            "working directory (the container --chdir's here). Required (or supply it via "
                            "the workdir/cwd aliases below)."
                        ),
                    },
                    "workdir": {
                        "type": "string",
                        "description": (
                            "Alias for workspace, used only when workspace is absent (precedence: "
                            "workspace > workdir > cwd). It does NOT select a subdirectory."
                        ),
                    },
                    "cwd": {
                        "type": "string",
                        "description": (
                            "Alias for workspace, used only when workspace and workdir are both absent. "
                            "It does NOT change the directory to a workspace subdirectory — the command "
                            "always runs at the workspace root."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds (default 60; bwrap probe capped at 20s).",
                    },
                    "attestation_id": {
                        "type": "string",
                        "description": (
                            "Optional prior uacp_sandbox_check attestation ID to reuse. "
                            "If absent a fresh containment probe is run. Expires with policy_version."
                        ),
                    },
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
                    "gate": {
                        "type": "string",
                        "description": (
                            "The gate name this record belongs to (e.g. 'PLAN_VALIDATION', "
                            "'VERIFY_EVIDENCE', 'TRIAGE_COMPLETE'). Free-form string stamped onto "
                            "each record; the Heartgate validator matches against this name."
                        ),
                    },
                    "record": {
                        "type": "object",
                        "description": (
                            "A JSON-serializable dict to append as one JSONL line. "
                            "The writer auto-stamps 'gate', 'run_id', and 'ts' if absent. "
                            "Must not contain embedded newlines; must be ≤3584 bytes UTF-8 "
                            "(PIPE_BUF atomicity bound)."
                        ),
                    },
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
                    "transition_path": {
                        "type": "string",
                        "description": (
                            "UACP-root-relative path to the phase-transition YAML artifact to validate. "
                            "Must be a .yaml/.yml file under one of: state/, verification/, executions/, "
                            "plans/, proposals/, resolutions/, or knowledge/. "
                            "Example: 'state/runs/r-20260628.yaml'."
                        ),
                    },
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

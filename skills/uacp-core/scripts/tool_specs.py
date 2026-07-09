"""Runtime-neutral registry of UACP governed tools.

Single source of truth for the 16 governed tools. Both the Hermes adapter
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

The 8 state handlers are pulled from ``state`` (uacp-state); the 8 others from
``governed_handlers`` (uacp-core). The 16 input schemas below are the canonical
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
    _handle_uacp_run_abort,
    _handle_uacp_run_finalize,
    _handle_uacp_run_init,
    _handle_uacp_run_register_artifact,
    _handle_uacp_run_registry_update,
    _handle_uacp_run_transition,
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
                    "uacp.check.* (all sub-kinds), uacp.execution_checkpoint, and uacp.investigation_entry "
                    'each require {"seq": "N"} (1-based counter); '
                    'uacp.evidence_disposition requires {"cluster": "<id>", "half": "<verified-facts|assumptions>"} '
                    "(template verification/{run_id}-{cluster}-{half}.md). "
                    "Omitting a required placeholder is an error that names the missing key."
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
    """Return the governed-tool specs (single source of truth)."""
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
                            "scope_artifact_path (string), started_at (epoch seconds, integer). "
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
        # -------------------------------------------------------------------
        # Run lifecycle tools (Phase 8): governed wrappers for the state
        # machine's handle_init / handle_transition / handle_register_artifact
        # / handle_finalize functions.  Each adds UACP context enforcement
        # (reason + authority_artifact + standard context fields) before
        # delegating to the neutral state machine.
        # -------------------------------------------------------------------
        ToolSpec(
            name="uacp_run_init",
            description="Governed run lifecycle: init",
            schema_description=(
                "Initialize a new run manifest under state/runs/{run_id}.yaml. "
                "Enforces UACP context fields and requires reason + authority_artifact. "
                "Optionally sets initial_phase (triage|brainstorm), track, workspace metadata, "
                "and goal-chaining fields (goal_id, inherits_from)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": (
                            "Authority source for the run (e.g. 'operator-request', 'proposal-artifact'). "
                            "Stored verbatim in the manifest's authority.source field."
                        ),
                    },
                    "initial_phase": {
                        "type": "string",
                        "enum": ["triage", "brainstorm"],
                        "description": (
                            "Starting phase for the run (default: 'triage'). "
                            "A run starting at 'brainstorm' must exit to 'triage' before any further work; "
                            "brainstorm → triage is its only valid transition."
                        ),
                    },
                    "track": {
                        "type": "string",
                        "enum": ["standard", "goal-driven"],
                        "description": (
                            "Lifecycle track (default: 'standard'). "
                            "Goal-driven runs carry a persistent goal_id and support "
                            "goal-chaining via inherits_from."
                        ),
                    },
                    "goal_id": {
                        "type": "string",
                        "description": (
                            "Persistent goal identifier for goal-driven runs. "
                            "When provided, must be registered in the run registry with the "
                            "matching manifest goal_id (the manifest is authoritative)."
                        ),
                    },
                    "inherits_from": {
                        "type": "string",
                        "description": (
                            "Parent run_id to inherit prior-phase artifacts from (goal-chaining). "
                            "The parent manifest's triage/proposal/plan artifacts are copied into "
                            "inherited_artifacts. The parent manifest must exist; fail-closed on missing parent."
                        ),
                    },
                    "reworks": {
                        "type": "string",
                        "description": (
                            "Parent run_id this run REWORKS (#109) — the standard-track findings->fix "
                            "loop. Per ADR-0016 P2 this is a NEW FORWARD RUN (not a verify->execute "
                            "back-edge): the rework run RE-AUTHORS its own upstream and drives the "
                            "lifecycle forward normally. Three things are RECORDED on the rework manifest "
                            "(readable via uacp_run_read): a provenance link (reworks), references to the "
                            "parent's VERIFY findings (carried_findings — the defects the rework should "
                            "address), and an incremented visible rework_depth. NOTE: this slice serializes "
                            "these as manifest state; a gate ENFORCING that the rework addresses the "
                            "carried findings is a follow-up. Standard-track parent + child only; mutually "
                            "exclusive with goal_id and inherits_from; fail-closed on a missing/unsafe parent."
                        ),
                    },
                    "workspace_kind": {
                        "type": "string",
                        "description": "Workspace kind (default: 'worktree').",
                    },
                    "workspace_path": {
                        "type": "string",
                        "description": "Path of the workspace (branch or worktree root).",
                    },
                    "workspace_branch": {
                        "type": "string",
                        "description": "Branch name for the workspace.",
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
                    "source",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
            handler=_handle_uacp_run_init,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_run_transition",
            description="Governed run lifecycle: phase transition",
            schema_description=(
                "Execute a locked phase transition for the active run. "
                "Enforces UACP context fields and requires reason + authority_artifact + from_phase + to_phase. "
                "The state machine validates the canonical phase graph, checks manifest.current_phase matches "
                "from_phase, and runs phase-exit structural gates (brainstorm admission contract, graph "
                "invariants, proposal coverage, execute evidence preconditions) before advancing."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "from_phase": {
                        "type": "string",
                        "description": (
                            "Current phase the run must be in. "
                            "Validated against manifest.current_phase — fails if they do not match."
                        ),
                    },
                    "to_phase": {
                        "type": "string",
                        "description": (
                            "Target phase. Must be an allowed transition from from_phase "
                            "per the canonical phase graph (config/phase-transitions.yaml). "
                            "The lifecycle phase name 'resolve' is accepted as an alias for the "
                            "terminal 'resolved' status the projection collapses it into (#114), so "
                            "'verify -> resolve' works; it is recorded canonically as VERIFY->RESOLVED. "
                            "Phase-exit structural gates (forced brainstorm admission contract, graph "
                            "invariants, forced execute evidence, forced proposal coverage) run BEFORE "
                            "the transition is committed."
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
                    "from_phase",
                    "to_phase",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
            handler=_handle_uacp_run_transition,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_run_register_artifact",
            description="Governed run lifecycle: register artifact",
            schema_description=(
                "Link a phase artifact path into the run manifest's artifacts map "
                "(manifest.artifacts[artifact_type] = path). "
                "Enforces UACP context fields and requires reason + authority_artifact + artifact_type + path. "
                "The path must resolve inside the governed workspace (.uacp/)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "artifact_type": {
                        "type": "string",
                        "description": (
                            "The artifact map key (e.g. 'triage', 'proposal', 'plan', "
                            "'execution_checkpoint', 'verification'). "
                            "Stored verbatim as the key in manifest.artifacts."
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "UACP-root-relative path to the artifact file (e.g. 'proposals/r-001-proposal.yaml'). "
                            "Must resolve inside the governed workspace (.uacp/); "
                            "paths escaping the workspace are rejected."
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
                    "artifact_type",
                    "path",
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
            handler=_handle_uacp_run_register_artifact,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_run_finalize",
            description="Governed run lifecycle: finalize",
            schema_description=(
                "Finalize a run from verify to resolved, gated by the Heartgate closure sweep. "
                "Enforces UACP context fields and requires reason + authority_artifact. "
                "The state machine tentatively stamps the run resolved/finalized, runs the full "
                "Heartgate closure sweep (all computed engines), and reverts on block — "
                "the governing gate is not bypassed."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "authority_artifact": {"type": "string"},
                    "workspace": {"type": "string"},
                    "uacp_run_id": {"type": "string"},
                    "uacp_phase": {"type": "string"},
                    "policy_version": {"type": "string"},
                    "declared_side_effects": {"type": "string"},
                },
                "required": [
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
            handler=_handle_uacp_run_finalize,
            read_only=False,
        ),
        ToolSpec(
            name="uacp_run_abort",
            description="Governed run lifecycle: abort (off-ramp)",
            schema_description=(
                "Early-terminate an ACTIVE run from any phase (incl. brainstorm) — the "
                "lifecycle off-ramp primitive. Enforces UACP context fields and requires "
                "reason + authority_artifact. Records an ABORT gate-ledger entry, frees the "
                "run's registry write_paths, releases the active-run pointer, and stamps an "
                "abort disposition on the manifest. Refused for a resolved/aborted run. Abort "
                "is a state-machine primitive, not a phase edge (no Heartgate transition "
                "artifact)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "disposition": {
                        "type": "string",
                        "enum": ["abandoned", "superseded", "direct", "blocked"],
                        "description": (
                            "Reason-class of the termination (default 'abandoned'). "
                            "'superseded' = replaced by another run; 'direct'/'blocked' record a "
                            "terminal-direct / blocked closure without a separate mechanism."
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
                    "reason",
                    "authority_artifact",
                    "workspace",
                    "uacp_run_id",
                    "uacp_phase",
                    "policy_version",
                    "declared_side_effects",
                ],
            },
            handler=_handle_uacp_run_abort,
            read_only=False,
        ),
    ]

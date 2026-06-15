"""Read-model for the active-run pointer at ``state/current.yaml``.

Written by the kernel (see ``state_machine.handle_init``) as
``{active_run_id, active_run_manifest}``. Permissive on read: extra keys
tolerated, both fields optional so a partially-written pointer still loads.

Codified from ``config/state.yaml current_pointer_schema`` (Slice 4a Task 3).
The 8 YAML-declared required fields are enumerated in
``CURRENT_POINTER_REQUIRED_FIELDS``; the model keeps all fields optional so
a partially-written pointer still loads and the validator enforces presence
explicitly.

``uacp_mode`` is an optional Phase 4.1 stub (manual|semi_auto|supervised_auto|
full_auto). No kernel reader consumes it in Phase 4; Phase 5 adds the first
kernel reader (Heartgate mode-gating).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# uacp_mode Literal  (from current_pointer_schema.fields.uacp_mode.values)
# ---------------------------------------------------------------------------

UacpMode = Literal["manual", "semi_auto", "supervised_auto", "full_auto"]

# ---------------------------------------------------------------------------
# MutationPolicy Literal  (from current_pointer_schema.fields.mutation_policy.values)
# ---------------------------------------------------------------------------

MutationPolicy = Literal["bootstrap_direct_edit", "uacp_state_required"]

# ---------------------------------------------------------------------------
# CURRENT_POINTER_REQUIRED_FIELDS — the 8 required fields from state.yaml
# (NOT including 'kind' which is the top-level doc field checked separately)
# ---------------------------------------------------------------------------

CURRENT_POINTER_REQUIRED_FIELDS: tuple[str, ...] = (
    "active_run_id",
    "active_run_manifest",
    "mutation_policy",
    "current_transition_artifact",
    "kanban_binding_artifact",
    "kanban_board_slug",
    "bootstrap_closed",
    "governed_mutation_active",
)


class CurrentPointer(BaseModel):
    """The ``state/current.yaml`` pointer to the active run.

    All fields are optional at the model level so a partially-written pointer
    still loads cleanly. The validator (validate_current_state) enforces
    the required-field set via CURRENT_POINTER_REQUIRED_FIELDS.
    """

    model_config = ConfigDict(extra="allow")

    # Core identity fields (always present in a complete pointer)
    active_run_id: str | None = None
    active_run_manifest: str | None = None

    # Expanded fields from current_pointer_schema (Slice 4a Task 3)
    mutation_policy: MutationPolicy | None = None
    current_transition_artifact: str | None = None
    kanban_binding_artifact: str | None = None
    kanban_board_slug: str | None = None
    bootstrap_closed: bool | None = None
    governed_mutation_active: bool | None = None

    # Phase 4.1 stub — operating mode for the active run
    uacp_mode: UacpMode | None = None

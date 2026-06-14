"""Read-model for the active-run pointer at ``state/current.yaml``.

Written by the kernel (see ``state_machine.handle_init``) as
``{active_run_id, active_run_manifest}``. Permissive on read: extra keys
tolerated, both fields optional so a partially-written pointer still loads.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CurrentPointer(BaseModel):
    """The ``state/current.yaml`` pointer to the active run."""

    model_config = ConfigDict(extra="allow")

    active_run_id: str | None = None
    active_run_manifest: str | None = None

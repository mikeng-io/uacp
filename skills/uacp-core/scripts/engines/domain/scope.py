"""Read-model for the ``uacp.scope`` artifact (``plans/{run_id}-scope.yaml``).

Grounded in ``config/artifact-schemas.yaml`` ``scope.required_fields``:
``run_id``, ``write_paths``, ``blast_radius``, ``rollback_path``. All fields are
optional here because this is a READ model used by the coherence engine on
possibly-malformed artifacts — presence/shape is the engine's concern, not the
model's. Extra keys (read_paths, forbidden_paths, ...) are tolerated.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class Scope(BaseModel):
    """The bounded blast radius declared for a run's EXECUTE phase."""

    model_config = ConfigDict(extra="allow")

    run_id: str | None = None
    write_paths: Any = None
    blast_radius: str | None = None
    rollback_path: str | None = None

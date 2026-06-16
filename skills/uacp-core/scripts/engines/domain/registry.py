"""Read-model for ``state/run-registry.yaml``.

Grounded in ``config/artifact-schemas.yaml`` ``run_registry``: a top-level
``active_runs`` list whose entries carry ``run_id``, ``phase``, ``write_paths``,
``scope_artifact_path`` and ``started_at``. Permissive read models — the
coherence engine (C6) only needs ``run_id`` + ``write_paths`` — extras tolerated.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunRegistryEntry(BaseModel):
    """One ``active_runs`` entry in the run registry."""

    model_config = ConfigDict(extra="allow")

    run_id: str | None = None
    phase: str | None = None
    write_paths: Any = None
    scope_artifact_path: str | None = None
    started_at: int | None = None
    # Goal-chaining (Task 3): links this run into a persistent goal's run-chain.
    # None for standard runs. Declared (rather than relying on extra="allow")
    # so the field is typed and discoverable.
    goal_id: str | None = None


class RunRegistry(BaseModel):
    """The ``state/run-registry.yaml`` document."""

    model_config = ConfigDict(extra="allow")

    schema_version: str | None = None
    active_runs: list[RunRegistryEntry] = Field(default_factory=list)

"""Read-model for a deferred item.

UACP does not declare a single canonical ``DeferredItem`` schema; the concept
appears in several loosely-typed places:

* ``config/state.yaml`` ``deferred_items`` — item_type ``map`` with observed
  keys ``id`` and ``reason``.
* ``config/artifact-schemas.yaml`` ``assumptions_dispositions.deferred`` —
  ``requires: [owner, next_phase_obligation]``.
* ``config/evidence-clusters.yaml`` — deferred items should carry
  ``owner`` / ``residual_risk`` / ``next_phase_acceptance``.

This model unions the firmly-named fields across those declarations and allows
extra keys, since no single declaration is authoritative. (The coherence engine
does not consume this model today; it is provided as the typed read-model for
deferral data so future engines have one place to bind it.)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DeferredItem(BaseModel):
    """A piece of deferred work / risk carried forward to a later phase."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    owner: str | None = None
    reason: str | None = None
    residual_risk: str | None = None
    next_phase_obligation: str | None = None
    next_phase_acceptance: str | None = None

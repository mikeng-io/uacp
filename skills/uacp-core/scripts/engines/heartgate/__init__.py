"""The Heartgate phase-transition gate package (Phase A3 extraction).

Public door (node 32 §1/§3): re-import the public names + declare ``__all__``.
The private helpers ``_is_safe_run_id`` / ``_truthy`` / ``_load_artifact_schemas``
are NOT part of the public surface; ``core.py`` re-exports them directly from
``.heartgate`` for their external importers (``state.py`` and the hermes guardian
kernel shim), pending their promotion to domain helpers.
"""

from __future__ import annotations

from .heartgate import Heartgate
from .models import HeartgateDecision, HeartgateError

__all__ = [
    "Heartgate",
    "HeartgateDecision",
    "HeartgateError",
]

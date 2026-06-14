"""Computed Heartgate engines.

A small package that gives every deterministic UACP validator ONE shared
:class:`~engines.base.Violation` type and ONE registry (``ENGINES``). Engines
are read-only, never raise, and return a list of violations (empty == clean).

Importing this package registers all bundled engines into ``ENGINES`` so that
:func:`engines.base.run_all_engines` can sweep them.
"""

from __future__ import annotations

# Importing the engine modules registers them into ENGINES as a side effect.
from . import (
    coherence,  # noqa: F401
    deferral_completeness,  # noqa: F401
    evidence_completeness,  # noqa: F401
    ledger_integrity,  # noqa: F401
    scope_conformance,  # noqa: F401
)
from .base import ENGINES, Engine, Violation, run_all_engines

__all__ = ["ENGINES", "Engine", "Violation", "run_all_engines"]

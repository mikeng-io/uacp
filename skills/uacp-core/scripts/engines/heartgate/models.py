"""Heartgate value types (Phase A3 extraction from ``core.py``).

Pure data for the phase-transition gate: the error raised on load failure and
the decision record the gate returns. Extracted to ``engines/heartgate/`` per
design/graph-engine nodes 31/32; ``core.py`` re-exports both names so existing
``from core import HeartgateError, HeartgateDecision`` importers are unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class HeartgateError(RuntimeError):
    pass


@dataclass(frozen=True)
class HeartgateDecision:
    decision: str
    reason: str
    blockers: list[str] = field(default_factory=list[str])
    warnings: list[str] = field(default_factory=list[str])
    # Structured findings (register move M4 / D-09), ADDITIVE alongside the
    # flattened ``blockers``/``warnings`` string lists which many consumers + the
    # MCP boundary still read. Each entry is a ``Violation.as_finding()`` dict
    # ({code, severity, message, detail, path}) — the same single serializer every
    # boundary shares, so ``detail`` reaches programmatic consumers instead of
    # being destroyed by the ``f"{code}: {message}"`` flattening.
    findings: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])

    @property
    def blocks_transition(self) -> bool:
        return self.decision == "block"

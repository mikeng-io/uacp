"""Per-phase retrieval mode gating table for the UACP Oracle engine.

PHASE_TIERS maps each UACP lifecycle phase to its retrieval mode:
  NONE      — no retrieval for this phase (return floor packets only)
  WRITEBACK — retrieval is available but write-back is gated
  FULL      — full retrieval + semantic search
  ADVISORY  — retrieval enabled but results are advisory, non-blocking
"""

from __future__ import annotations

from enum import StrEnum


class OracleMode(StrEnum):
    NONE = "none"
    WRITEBACK = "writeback"
    FULL = "full"
    ADVISORY = "advisory"


PHASE_TIERS: dict[str, OracleMode] = {
    "brainstorm": OracleMode.ADVISORY,
    "triage": OracleMode.ADVISORY,
    "propose": OracleMode.FULL,
    "plan": OracleMode.FULL,
    "execute": OracleMode.NONE,
    "verify": OracleMode.FULL,
    "resolve": OracleMode.WRITEBACK,
}


def mode_for_phase(phase: str) -> OracleMode:
    """Return the OracleMode for a given phase, defaulting to NONE for unknown phases."""
    return PHASE_TIERS.get(phase, OracleMode.NONE)

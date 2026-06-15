"""Read-model for a single gate-ledger record.

The gate ledger lives at ``state/gate-ledger/<run_id>.jsonl`` — one JSON object
per line. The kernel's append handler (uacp-state) stamps an envelope onto every
record: ``gate``, ``run_id`` and ``ts`` are always present; the caller-supplied
``record`` payload (e.g. ``result``, ``policy_version``, ...) is merged in at the
top level. The schema is deliberately loose, so this model is permissive: only
the envelope fields are typed, and any additional keys are preserved.

Codified from ``config/state.yaml gate_ledger.record_schema`` (Slice 4a Task 3).
Optional ``phase``, ``result``, and ``reviewer`` fields added with Literal types
matching the YAML enum values.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Enums (from gate_ledger.record_schema.enum_values)
# ---------------------------------------------------------------------------

LedgerResult = Literal["pass", "warn", "block"]

LedgerReviewer = Literal["model", "codex", "council", "operator"]


class LedgerEntry(BaseModel):
    """One gate-ledger JSONL record (envelope-typed, extra keys allowed).

    Required envelope fields (gate, run_id, ts) are declared as optional at
    the model level for permissive loading; the uacp-state handler stamps
    them before writing.

    Optional schema fields added in Slice 4a Task 3:
      phase     — lifecycle phase at gate evaluation time
      result    — enum: pass|warn|block
      reviewer  — enum: model|codex|council|operator
    """

    model_config = ConfigDict(extra="allow")

    # Envelope fields (always stamped by the append handler)
    gate: str | None = None
    run_id: str | None = None
    ts: int | None = None
    record: Any = None

    # Optional schema fields (from gate_ledger.record_schema)
    phase: str | None = None
    result: LedgerResult | None = None
    reviewer: LedgerReviewer | None = None

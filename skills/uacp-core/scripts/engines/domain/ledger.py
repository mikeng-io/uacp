"""Read-model for a single gate-ledger record.

The gate ledger lives at ``state/gate-ledger/<run_id>.jsonl`` — one JSON object
per line. The kernel's append handler (uacp-state) stamps an envelope onto every
record: ``gate``, ``run_id`` and ``ts`` are always present; the caller-supplied
``record`` payload (e.g. ``result``, ``policy_version``, ...) is merged in at the
top level. The schema is deliberately loose, so this model is permissive: only
the envelope fields are typed, and any additional keys are preserved.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class LedgerEntry(BaseModel):
    """One gate-ledger JSONL record (envelope-typed, extra keys allowed)."""

    model_config = ConfigDict(extra="allow")

    gate: str | None = None
    run_id: str | None = None
    ts: int | None = None
    record: Any = None

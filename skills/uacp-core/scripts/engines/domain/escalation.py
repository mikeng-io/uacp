"""Read-model for escalation records at ``state/escalations/{run_id}.jsonl``.

Codified from ``config/state.yaml escalations.record_schema`` (Slice 4a Task 3).
Each escalation is written by ``uacp_escalation_event`` in
``skills/uacp-state/scripts/state.py``.

Enums:
  EscalationMode     — manual|semi_auto|supervised_auto|full_auto
  EscalationSeverity — info|warn|block
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Enums (from escalations.record_schema.fields.mode.values and severity.values)
# ---------------------------------------------------------------------------

EscalationMode = Literal["manual", "semi_auto", "supervised_auto", "full_auto"]

EscalationSeverity = Literal["info", "warn", "block"]


class EscalationRecord(BaseModel):
    """One escalation JSONL record (state/escalations/{run_id}.jsonl).

    Required fields mirror escalations.record_schema.required_fields from
    config/state.yaml. Optional ``details`` field carries extra context.
    """

    model_config = ConfigDict(extra="allow")

    # Required fields
    run_id: str
    phase: str
    mode: EscalationMode
    trigger: str
    severity: EscalationSeverity
    reason: str
    authority_artifact: str
    ts: int

    # Optional field
    details: dict[str, Any] | None = None

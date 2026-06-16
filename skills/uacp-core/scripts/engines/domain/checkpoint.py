"""Read-model for an in-EXECUTE checkpoint manifest entry (goal-driven track).

ADR-0016 (the goal-driven track) records each EXECUTE iteration as a
*checkpoint*: a disposable probe toward a persistent goal. The manifest is a
gate-ledger-backed, append-only record — NOT an honor system. Per the
"structural claim => evidence coupling" enforcement finding, a checkpoint's
``evidence`` must reference a real, governed-root-contained artifact (not a
prose sentence, not a missing path, not a path that escapes the root); Heartgate
runs a no-self-attestation check on it exactly as it does for other gate-ledger
evidence (see ``Heartgate._validate_checkpoint_entry`` in ``core.py``).

PURE layer: Pydantic model only, ZERO filesystem I/O. The structural
existence/containment check on ``evidence`` lives in Heartgate, which owns the
governed-root path helpers. This model only validates the record *shape*.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CheckpointEntry(BaseModel):
    """One checkpoint manifest record (gate-ledger ``gate: "CHECKPOINT"``).

    Schema mirrors ADR-0016's "what changed / why / evidence / verdict /
    invariant" manifest. ``evidence`` is a governed-root-relative artifact path
    whose existence + containment is enforced structurally by Heartgate — this
    model only requires it be a non-empty string.

    ``verdict`` is the disposition of the probe:
      keep      — the checkpoint advances the goal; carry it forward.
      roll_back — discard this probe; relaunch from a prior checkpoint
                  (``rolled_back_to`` records which one).
      restart   — discard and relaunch the run under the held goal.
    """

    model_config = ConfigDict(extra="forbid")

    checkpoint_id: str
    run_id: str
    goal_id: str
    phase: str  # expected "execute"
    what_changed: str
    why: str
    evidence: str  # governed-root-relative artifact path that MUST exist
    verdict: Literal["keep", "roll_back", "restart"]
    invariant: str
    rolled_back_to: str | None = None

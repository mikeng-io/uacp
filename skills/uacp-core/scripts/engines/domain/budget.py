"""Read-model for a goal-driven run's convergence budget (ADR-0016, R2).

A goal-driven run iterates by taking checkpoints toward a persistent goal.
"Operator sign-off" is the *interactive* exit — but an autonomous run
(``claude -p``, cron) has no operator to sign off, so without a declared,
enforced bound it loops forever. ADR-0016 decision R2 makes a convergence
budget REQUIRED on the goal-driven PROPOSE artifact and enforces its
``max_checkpoints`` cap at Heartgate.

PURE layer: Pydantic model only, ZERO filesystem I/O. Heartgate owns the disk
read (it loads the PROPOSE budget artifact and the per-goal checkpoint count);
this model only validates the *shape* of the declared budget.

Shape:
  max_checkpoints  — REQUIRED, int > 0. The enforced bound: once the goal's
                     CHECKPOINT count (across its whole run-chain) reaches this,
                     a further ``keep``/continue checkpoint is blocked (the run
                     must converge or escalate).
  max_spend        — OPTIONAL, declare-only for now (not enforced this task).
  max_wall_clock   — OPTIONAL, declare-only for now (not enforced this task).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConvergenceBudget(BaseModel):
    """The convergence bound declared on a goal-driven PROPOSE artifact.

    ``max_checkpoints`` is the only ENFORCED knob this task: it must be a
    positive integer. ``max_spend`` / ``max_wall_clock`` are declare-only
    (accepted and carried, but not yet enforced) — they exist so the budget
    artifact can record the operator's full intent without a later schema break.
    """

    model_config = ConfigDict(extra="forbid")

    max_checkpoints: int = Field(gt=0)
    max_spend: float | None = None
    max_wall_clock: str | None = None

"""The N-replicate pipeline (40-benchmark's statistics law).

A single agent run is one Bernoulli draw -- an anecdote, not a score. So a cell result is **N
replicates**, run SERIALLY (the host GPU is one serialized resource -- 40's wall-clock budget),
each producing one JSONL record, aggregated into outcome counts and wall-clock mean/stdev.

This is S1's deliverable: the data-handling reality (and the wall-clock bill) is confronted here,
against the cheap smoke tier, *before* anything is scored. There is **no scoring** in this module
-- outcomes only (``completed`` / ``timeout`` / ``error``); oracles and verdicts come later (S3+).

stdlib only.
"""

from __future__ import annotations

import json
import math
import os
import statistics
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from acp_client import OUTCOME_COMPLETED, OUTCOME_ERROR, OUTCOME_TIMEOUT
from cells import Cell
from runner import RunResult, Task, run_cell

# The closed outcome vocabulary a replicate may report.
OUTCOMES = (OUTCOME_COMPLETED, OUTCOME_TIMEOUT, OUTCOME_ERROR)

RunFn = Callable[[Cell, Task, Path], RunResult]


@dataclass
class Aggregate:
    """Cell x task summary over N replicates. Outcome counts + wall-clock stats; never a score."""

    cell: str
    task: str
    model_id: str
    n: int
    outcomes: dict[str, int]
    wall_clock: dict[str, float]
    # Paths are RELATIVE to the aggregate's own directory (the output root): a committed or
    # copied ledger must locate its evidence from wherever it lives, never via the original
    # operator's absolute worktree paths.
    replicates_path: str
    aggregate_path: str


# Two-sided 95% Student-t critical values by degrees of freedom (df 1..30); ~normal beyond.
_T95 = (
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
)  # fmt: skip


def _wall_clock_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0, "ci95_half_width": 0.0}
    # Sample stdev requires >= 2 points; a single replicate has no dispersion.
    stdev = statistics.stdev(values) if len(values) >= 2 else 0.0
    # 40-benchmark: scores are reported as mean +/- a confidence interval, never a point.
    n = len(values)
    if n >= 2 and stdev > 0.0:
        t = _T95[min(n - 1, len(_T95)) - 1]
        ci95 = t * stdev / math.sqrt(n)
    else:
        ci95 = 0.0
    return {
        "mean": round(statistics.mean(values), 3),
        "stdev": round(stdev, 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "ci95_half_width": round(ci95, 3),
    }


def _record(result: RunResult, replicate: int, output_root: Path) -> dict:
    return {
        "cell": result.cell,
        "task": result.task,
        "model_id": result.model_id,
        "replicate": replicate,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "outcome": result.outcome,
        "wall_clock_s": result.wall_clock_s,
        "exit_code": result.exit_code,
        "stop_reason": result.stop_reason,
        "artifact_dir": os.path.relpath(result.artifact_dir, output_root),
    }


def run_replicates(
    cell: Cell,
    task: Task,
    n: int,
    output_root: str | Path,
    *,
    run_fn: RunFn = run_cell,
) -> Aggregate:
    """Run ``cell`` x ``task`` ``n`` times serially; write per-replicate JSONL + aggregate JSON."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    replicates_path = output_root / "replicates.jsonl"
    aggregate_path = output_root / "aggregate.json"

    outcome_counts = {outcome: 0 for outcome in OUTCOMES}
    wall_clocks: list[float] = []
    model_id = cell.model_id

    with open(replicates_path, "w", encoding="utf-8") as jsonl:
        for i in range(n):
            rep_dir = output_root / f"rep-{i:03d}"
            result = run_fn(cell, task, rep_dir)
            # Normalize ONCE, before anything is serialized: an out-of-vocabulary outcome is
            # counted as `error` AND written as `error` in the JSONL — the per-replicate ledger
            # and the aggregate must never disagree about the same replicate. The raw value is
            # preserved in the record (`raw_outcome`) so the anomaly stays auditable.
            outcome = result.outcome if result.outcome in outcome_counts else OUTCOME_ERROR
            record = _record(result, i, output_root)
            if outcome != result.outcome:
                record["raw_outcome"] = result.outcome
                record["outcome"] = outcome
            jsonl.write(json.dumps(record) + "\n")
            jsonl.flush()
            outcome_counts[outcome] += 1
            wall_clocks.append(result.wall_clock_s)
            model_id = result.model_id or model_id

    aggregate = Aggregate(
        cell=cell.name,
        task=task.name,
        model_id=model_id,
        n=n,
        outcomes=outcome_counts,
        wall_clock=_wall_clock_stats(wall_clocks),
        replicates_path=replicates_path.name,
        aggregate_path=aggregate_path.name,
    )
    aggregate_path.write_text(json.dumps(asdict(aggregate), indent=2), encoding="utf-8")
    return aggregate

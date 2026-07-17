"""Replicate JSONL + aggregate correctness (incl. stdev) via an injected fake run_fn (no docker)."""

from __future__ import annotations

import json
import math
import statistics

import pytest
from cells import hermes_bare
from replicates import run_replicates
from runner import RunResult, Task


def _fake_run_factory(plan):
    """plan: list of (outcome, wall_clock_s). Returns a run_fn that yields them in order."""
    calls = {"i": 0}

    def run_fn(cell, task, out_dir):
        outcome, wc = plan[calls["i"]]
        calls["i"] += 1
        return RunResult(
            cell=cell.name,
            task=task.name,
            model_id=cell.model_id,
            outcome=outcome,
            started_at="t0",
            ended_at="t1",
            wall_clock_s=wc,
            artifact_dir=str(out_dir),
            exit_code=0,
        )

    return run_fn


def test_jsonl_and_aggregate_counts_and_stats(tmp_path):
    cell = hermes_bare()
    task = Task(name="probe", prompt="do nothing")
    plan = [
        ("completed", 1.0),
        ("completed", 2.0),
        ("timeout", 3.0),
        ("error", 4.0),
        ("completed", 5.0),
    ]
    agg = run_replicates(cell, task, 5, tmp_path, run_fn=_fake_run_factory(plan))

    # JSONL: one record per replicate, ordered.
    lines = (tmp_path / "replicates.jsonl").read_text().splitlines()
    assert len(lines) == 5
    records = [json.loads(x) for x in lines]
    assert [r["replicate"] for r in records] == [0, 1, 2, 3, 4]
    assert [r["outcome"] for r in records] == [
        "completed",
        "completed",
        "timeout",
        "error",
        "completed",
    ]
    assert records[0]["model_id"] == "qwen3.5:4b"

    # Aggregate outcome counts.
    assert agg.n == 5
    assert agg.outcomes == {"completed": 3, "timeout": 1, "error": 1}

    # Wall-clock stats derived from the same values statistics would produce.
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert agg.wall_clock["mean"] == round(statistics.mean(values), 3)
    assert agg.wall_clock["stdev"] == round(statistics.stdev(values), 3)
    assert agg.wall_clock["min"] == 1.0
    assert agg.wall_clock["max"] == 5.0
    # 95% CI half-width: t(df=4)=2.776, stdev/sqrt(5) -- the 40-benchmark "mean +/- CI" law.
    expected_ci = 2.776 * statistics.stdev(values) / math.sqrt(5)
    assert agg.wall_clock["ci95_half_width"] == round(expected_ci, 3)

    # Aggregate JSON on disk matches.
    on_disk = json.loads((tmp_path / "aggregate.json").read_text())
    assert on_disk["outcomes"] == {"completed": 3, "timeout": 1, "error": 1}
    assert on_disk["wall_clock"]["stdev"] == agg.wall_clock["stdev"]

    # Ledger portability: every serialized path is RELATIVE to the output root, so a committed
    # or copied ledger can locate its evidence anywhere (never the operator's absolute paths).
    assert on_disk["replicates_path"] == "replicates.jsonl"
    assert on_disk["aggregate_path"] == "aggregate.json"
    assert [r["artifact_dir"] for r in records] == [f"rep-{i:03d}" for i in range(5)]
    assert not any(r["artifact_dir"].startswith("/") for r in records)


def test_single_replicate_has_zero_stdev(tmp_path):
    cell = hermes_bare()
    task = Task(name="probe", prompt="x")
    agg = run_replicates(cell, task, 1, tmp_path, run_fn=_fake_run_factory([("completed", 2.5)]))
    assert agg.n == 1
    assert agg.outcomes == {"completed": 1, "timeout": 0, "error": 0}
    assert agg.wall_clock["stdev"] == 0.0
    assert agg.wall_clock["mean"] == 2.5
    assert agg.wall_clock["ci95_half_width"] == 0.0


def test_unknown_outcome_counts_as_error(tmp_path):
    cell = hermes_bare()
    task = Task(name="probe", prompt="x")
    agg = run_replicates(cell, task, 1, tmp_path, run_fn=_fake_run_factory([("weird", 1.0)]))
    assert agg.outcomes == {"completed": 0, "timeout": 0, "error": 1}


def test_zero_replicates_refused(tmp_path):
    cell = hermes_bare()
    task = Task(name="probe", prompt="x")
    with pytest.raises(ValueError, match="n must be"):
        run_replicates(cell, task, 0, tmp_path, run_fn=_fake_run_factory([]))

#!/usr/bin/env python3
"""S1 smoke run: an entry-gated cell driven through the N-replicate pipeline on a trivial task.

The task ("create hello.txt containing exactly 'hello proving ground'") gives the trail a real tool
action (a file written in the mounted workspace, visible in the exported git status/tree). N
defaults to 5 -- 40-benchmark's smoke floor. This is a PIPELINE check, not a scored cell: outcomes
only (completed / timeout / error), no oracle judgment.

Emits: records/S1-smoke-summary.md + the per-replicate JSONL and aggregate JSON under the out dir.

Usage:  python3 scripts/smoke.py [-n 5] [--out DIR] [--model qwen3.5:4b] [--timeout 240]
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from cells import SMOKE_MODEL_ID, hermes_bare  # noqa: E402
from replicates import Aggregate, run_replicates  # noqa: E402
from runner import Task  # noqa: E402

RECORD = PKG / "records" / "S1-smoke-summary.md"
HELLO_CONTENT = "hello proving ground"
SMOKE_PROMPT = (
    f"Create a file named hello.txt in the current directory containing exactly "
    f"'{HELLO_CONTENT}' (no trailing newline, no extra text). Then stop."
)


def smoke_task() -> Task:
    return Task(name="hello-file", prompt=SMOKE_PROMPT)


def write_record(agg: Aggregate, n: int, timeout: float, out_dir: Path) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    wc = agg.wall_clock
    lines = [
        "# S1 Smoke Summary — hermes-bare pipeline check",
        "",
        f"- Generated: {datetime.now(UTC).isoformat()}",
        f"- Cell: `{agg.cell}`  Task: `{agg.task}`  Model: `{agg.model_id}`",
        f"- Replicates (N): {n}  Per-replicate timeout: {timeout:.0f}s",
        f"- Output: `{out_dir}`",
        "",
        "This is a pipeline check against the cheap smoke tier — outcomes only, no scoring "
        "(oracles arrive at S3+). It confronts the data-handling reality and the wall-clock bill "
        "before any scored sweep exists (40-benchmark's statistics law, built at S1).",
        "",
        "## Outcomes",
        "",
        "| outcome | count |",
        "|---|---|",
    ]
    for outcome, count in agg.outcomes.items():
        lines.append(f"| {outcome} | {count} |")
    lines += [
        "",
        "## Wall-clock (seconds)",
        "",
        "| mean | stdev | min | max | ci95 half-width |",
        "|---|---|---|---|---|",
        f"| {wc['mean']} | {wc['stdev']} | {wc['min']} | {wc['max']} | {wc['ci95_half_width']} |",
        "",
        f"Per-replicate records: `{agg.replicates_path}`",
        "",
        f"Aggregate JSON: `{agg.aggregate_path}`",
        "",
    ]
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="S1 smoke run")
    parser.add_argument("-n", "--replicates", type=int, default=5)
    parser.add_argument("--out", default=str(PKG / "records" / "smoke-out"))
    parser.add_argument("--model", default=SMOKE_MODEL_ID)
    parser.add_argument("--timeout", type=float, default=240.0)
    args = parser.parse_args()

    cell = hermes_bare(model_id=args.model)
    task = smoke_task()
    out_dir = Path(args.out)

    def run_fn(c, t, d):
        from runner import run_cell

        return run_cell(c, t, d, timeout=args.timeout)

    agg = run_replicates(cell, task, args.replicates, out_dir, run_fn=run_fn)
    write_record(agg, args.replicates, args.timeout, out_dir)

    print(f"\nSmoke: N={args.replicates} outcomes={agg.outcomes} wall_clock={agg.wall_clock}")
    print(f"Record: {RECORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

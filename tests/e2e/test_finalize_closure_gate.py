"""E2E: prove the RESOLVE closure sweep is wired onto the LIVE finalize path.

The strongest verification UACP owns — Heartgate.validate_closure -> run_all_engines
(the full engine sweep) — historically had ZERO runtime callers: it ran only when
a test called it directly, while state_machine.handle_finalize stamped a run
'resolved' WITHOUT running it. That is the macro #503-class fail-open ("the best
check is never run on the live path").

These tests drive a genuinely closeable run to resolved (lessons authored) but let
the TEST call handle_finalize, then assert:

  * a closeable run finalizes (the sweep runs AND passes — finalize still works);
  * a run with ONE corrupted engine input (non-monotonic gate ledger) is BLOCKED
    by handle_finalize itself, the engine code surfaces, and finalized_at is
    reverted to None (the run is left un-finalized, to be fixed and retried).

The teeth test FAILS before the wiring (handle_finalize returns ok, ignoring the
corruption) and passes after — non-vacuous proof the sweep fires at finalize.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine

from tests.e2e.test_coherence import (
    _load_manifest_raw,
    drive_happy_path,
)


def _finalize(root: Path, run_id: str) -> dict:
    return json.loads(state_machine.handle_finalize({"workspace": str(root), "run_id": run_id}))


def _make_ledger_non_monotonic(root: Path, run_id: str) -> None:
    """Rewrite the run's gate ledger so timestamps strictly decrease.

    This is exactly the corruption ledger_integrity (LI_TIMESTAMP_NON_MONOTONIC)
    detects — proven in test_heartgate_closure — used here to give handle_finalize's
    closure sweep something real to catch.
    """
    ledger_path = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text().strip().splitlines()]
    assert len(records) >= 2, "need >=2 ledger records to make ts non-monotonic"
    for i, rec in enumerate(records):
        rec["ts"] = 1000 - i * 10
    ledger_path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


# ----------------------------------------------------------------- positive path
def test_finalize_succeeds_on_closeable_run(temp_uacp_root: Path, valid_run_id: str):
    # Driven to resolved (lessons authored) but NOT finalized yet.
    drive_happy_path(temp_uacp_root, valid_run_id, finalize=False)
    pre = _load_manifest_raw(temp_uacp_root, valid_run_id)
    assert pre["current_phase"] == "resolved"
    assert pre.get("finalized_at") is None, "precondition: not finalized yet"

    out = _finalize(temp_uacp_root, valid_run_id)
    assert out.get("ok") is True, out
    assert out["status"] == "resolved"

    post = _load_manifest_raw(temp_uacp_root, valid_run_id)
    assert post.get("finalized_at") is not None, "closeable run must finalize"


# --------------------------------------------------------------------- the teeth
def test_finalize_blocked_by_closure_sweep_on_corrupt_ledger(
    temp_uacp_root: Path, valid_run_id: str
):
    drive_happy_path(temp_uacp_root, valid_run_id, finalize=False)
    # Corrupt EXACTLY one engine input AFTER the run is otherwise closeable.
    _make_ledger_non_monotonic(temp_uacp_root, valid_run_id)

    out = _finalize(temp_uacp_root, valid_run_id)

    # handle_finalize itself must run the sweep and refuse to finalize.
    assert "error" in out, f"expected finalize to be blocked, got: {out}"
    blockers = " ".join(out.get("blockers") or [])
    assert "LI_TIMESTAMP_NON_MONOTONIC" in blockers, out

    # And it must have reverted: the run is NOT finalized.
    post = _load_manifest_raw(temp_uacp_root, valid_run_id)
    assert post.get("finalized_at") is None, "blocked finalize must not leave a finalized run"

"""TDD tests for handle_abort — the #107 lifecycle off-ramp primitive.

Abort early-terminates an ACTIVE run from any phase: it stamps an abort
disposition on the manifest, appends an ABORT gate-ledger record, frees the run's
registry write_paths, and releases the active-run pointer (with provenance). It is
refused for a non-active run, and an aborted run can no longer transition.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from state_machine import (
    AbortRecord,
    handle_abort,
    handle_init,
    handle_transition,
)


def _init(root: Path, run_id: str = "uacp-abort-001") -> str:
    out = json.loads(
        handle_init({"workspace": str(root), "run_id": run_id, "source": "operator-request"})
    )
    assert out.get("ok") is True, out
    return run_id


def _manifest(root: Path, run_id: str) -> dict:
    return yaml.safe_load(
        (root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text(encoding="utf-8")
    )


def _ledger_gates(root: Path, run_id: str) -> list[str]:
    p = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln)["gate"] for ln in p.read_text().splitlines() if ln.strip()]


def _seed_registry(root: Path, run_id: str, write_paths: list[str]) -> None:
    reg = root / ".uacp" / "state" / "run-registry.yaml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "active_runs": [
                    {
                        "run_id": run_id,
                        "phase": "execute",
                        "write_paths": write_paths,
                        "scope_artifact_path": f"plans/{run_id}-scope.yaml",
                        "started_at": 0,
                    }
                ],
            },
            sort_keys=False,
        )
    )


# --------------------------------------------------------------------------- schema
class TestAbortRecordSchema:
    def test_valid_dispositions_accepted(self):
        for d in ("abandoned", "superseded", "direct", "blocked"):
            rec = AbortRecord(reason="x", phase_at_abort="execute", disposition=d)
            assert rec.disposition == d

    def test_invalid_disposition_rejected(self):
        with pytest.raises(ValueError):
            AbortRecord(reason="x", phase_at_abort="execute", disposition="nonsense")

    def test_disposition_defaults_to_abandoned(self):
        rec = AbortRecord(reason="x", phase_at_abort="execute")
        assert rec.disposition == "abandoned"


# --------------------------------------------------------------------------- effects
def test_abort_stamps_manifest_and_ledger(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    out = json.loads(
        handle_abort(
            {
                "workspace": str(root),
                "run_id": run_id,
                "reason": "superseded by a newer run",
                "disposition": "superseded",
            }
        )
    )
    assert out.get("ok") is True, out
    assert out["status"] == "aborted"
    assert out["phase_at_abort"] == "triage"
    assert out["disposition"] == "superseded"

    m = _manifest(root, run_id)
    assert m["status"] == "aborted"
    # current_phase is preserved at the abort point (NOT moved to a terminal phase),
    # so the run can never pass handle_finalize's terminal-phase check.
    assert m["current_phase"] == "triage"
    assert m["abort"]["reason"] == "superseded by a newer run"
    assert m["abort"]["phase_at_abort"] == "triage"
    assert m["abort"]["disposition"] == "superseded"
    assert m["abort"]["aborted_at"]
    events = [h["event"] for h in m["state_history"]]
    assert "run_abort" in events

    assert "ABORT" in _ledger_gates(root, run_id)


def test_abort_default_disposition_is_abandoned(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    out = json.loads(
        handle_abort({"workspace": str(root), "run_id": run_id, "reason": "operator cancel"})
    )
    assert out.get("ok") is True, out
    assert out["disposition"] == "abandoned"
    assert _manifest(root, run_id)["abort"]["disposition"] == "abandoned"


def test_abort_reachable_from_a_later_phase(temp_uacp_root: Path):
    """Abort works from ≥2 distinct phases — drive to execute, then abort there."""
    root = temp_uacp_root
    run_id = _init(root)
    for frm, to in (("triage", "propose"), ("propose", "plan"), ("plan", "execute")):
        tr = json.loads(
            handle_transition(
                {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to}
            )
        )
        assert tr.get("ok") is True, tr
    out = json.loads(
        handle_abort(
            {
                "workspace": str(root),
                "run_id": run_id,
                "reason": "blocked mid-execute",
                "disposition": "blocked",
            }
        )
    )
    assert out.get("ok") is True, out
    assert out["phase_at_abort"] == "execute"
    assert _manifest(root, run_id)["abort"]["phase_at_abort"] == "execute"


def test_abort_frees_registry_write_paths(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    _seed_registry(root, run_id, ["executions/shared.txt"])
    reg = root / ".uacp" / "state" / "run-registry.yaml"

    # Non-vacuity: the entry (and its write_paths) is present BEFORE abort.
    before = yaml.safe_load(reg.read_text())["active_runs"]
    assert any(e["run_id"] == run_id for e in before)

    out = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "cancel"}))
    assert out.get("ok") is True, out

    after = yaml.safe_load(reg.read_text())["active_runs"]
    assert not any(e["run_id"] == run_id for e in after), (
        "aborted run must be deregistered so its write_paths are freed"
    )


def test_abort_releases_pointer_with_provenance(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)  # handle_init points current.yaml at this run
    current = root / ".uacp" / "state" / "current.yaml"
    assert yaml.safe_load(current.read_text())["active_run_id"] == run_id

    out = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "cancel"}))
    assert out.get("ok") is True, out

    cur = yaml.safe_load(current.read_text())
    assert cur["active_run_id"] is None
    assert cur["released_by"] == f"{run_id}@abort"


def test_abort_does_not_release_a_pointer_naming_another_run(temp_uacp_root: Path):
    root = temp_uacp_root
    run_a = _init(root, "uacp-abort-A")
    # Pointer names run A. Create run B without disturbing the pointer.
    run_b = _init(root, "uacp-abort-B")
    current = root / ".uacp" / "state" / "current.yaml"
    assert yaml.safe_load(current.read_text())["active_run_id"] == run_a

    out = json.loads(handle_abort({"workspace": str(root), "run_id": run_b, "reason": "cancel B"}))
    assert out.get("ok") is True, out
    # The pointer still names A — aborting B must not clear a pointer it does not own.
    assert yaml.safe_load(current.read_text())["active_run_id"] == run_a


# --------------------------------------------------------------------------- guards
def test_aborted_run_cannot_transition(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    handle_abort({"workspace": str(root), "run_id": run_id, "reason": "cancel"})
    tr = json.loads(
        handle_transition(
            {
                "workspace": str(root),
                "run_id": run_id,
                "from_phase": "triage",
                "to_phase": "propose",
            }
        )
    )
    assert "error" in tr
    assert "not active" in tr["error"]
    # Non-vacuity: the same transition succeeds on an equivalent NON-aborted run.
    other = _init(root, "uacp-abort-live")
    ok = json.loads(
        handle_transition(
            {"workspace": str(root), "run_id": other, "from_phase": "triage", "to_phase": "propose"}
        )
    )
    assert ok.get("ok") is True, ok


def test_abort_of_aborted_run_is_refused(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    first = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "cancel"}))
    assert first.get("ok") is True, first
    second = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "again"}))
    assert "error" in second
    assert "not active" in second["error"]
    # And the first abort's single ABORT ledger record is not duplicated.
    assert _ledger_gates(root, run_id).count("ABORT") == 1


def test_abort_of_resolved_run_is_refused(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    mpath = root / ".uacp" / "state" / "runs" / f"{run_id}.yaml"
    data = yaml.safe_load(mpath.read_text())
    data["status"] = "resolved"
    data["current_phase"] = "resolved"
    mpath.write_text(yaml.safe_dump(data))
    out = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "cancel"}))
    assert "error" in out
    assert "not active" in out["error"]


def test_abort_requires_reason(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    out = json.loads(handle_abort({"workspace": str(root), "run_id": run_id, "reason": "  "}))
    assert "error" in out
    assert "reason is required" in out["error"]


def test_abort_rejects_invalid_disposition(temp_uacp_root: Path):
    root = temp_uacp_root
    run_id = _init(root)
    out = json.loads(
        handle_abort(
            {"workspace": str(root), "run_id": run_id, "reason": "x", "disposition": "bogus"}
        )
    )
    assert "error" in out
    assert "invalid disposition" in out["error"]
    # The run is untouched — still active.
    assert _manifest(root, run_id)["status"] == "active"


def test_abort_refuses_unsafe_run_id(temp_uacp_root: Path):
    out = json.loads(
        handle_abort({"workspace": str(temp_uacp_root), "run_id": "../escape", "reason": "x"})
    )
    assert "error" in out
    assert "unsafe run_id" in out["error"]

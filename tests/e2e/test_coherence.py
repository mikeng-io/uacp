"""E2E coherence tests: prove validate_run_coherence returns ZERO violations on
a genuinely complete run, and that each kind of corruption is CAUGHT (teeth).

The positive test drives a real INIT -> ... -> FINALIZE run through the actual
Guardian / Heartgate / state machine / governed writers (same path as
test_full_lifecycle), then registers the run-id-bearing artifacts (scope,
lessons) the validator cross-checks. Each teeth test starts from that good run,
corrupts EXACTLY one thing, and asserts the specific violation code fires while
the good run did NOT fire it.
"""

from __future__ import annotations

import json
from pathlib import Path

import state_machine
import yaml
from core import Heartgate
from engines.base import Violation
from engines.coherence import validate_run_coherence
from state import _handle_uacp_gate_ledger_append

from tests.e2e.driver import Driver
from tests.e2e.test_full_lifecycle import _SEEDERS, PHASES


def drive_happy_path(root: Path, run_id: str, *, finalize: bool = True) -> None:
    """Drive a full INIT -> ... -> FINALIZE run through the real kernel.

    Reuses the seeders and phase list from test_full_lifecycle so the happy path
    stays in lockstep with the canonical lifecycle test (no duplicated gate
    knowledge). The run's lessons (closure) artifact is authored + registered
    during RESOLVE *before* finalize, so the closure sweep now wired into
    ``handle_finalize`` sees a genuinely closeable run.

    With ``finalize=False`` the run is driven through the verify -> resolved
    transition (lessons authored) but ``handle_finalize`` is NOT called — leaving
    a resolved-but-not-finalized run for tests that drive finalize themselves.
    On return (finalize=True) the run is resolved + finalized with a complete
    manifest, gate ledger, and current.yaml pointer.
    """
    d = Driver(root, run_id)
    heartgate = Heartgate.load(str(root))

    init = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_init(a),
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"},
        phase="triage",
    )
    assert init.get("ok") is True, init

    for frm, to in PHASES:
        ledger = d.call(
            "uacp_gate_ledger_append",
            _handle_uacp_gate_ledger_append,
            {
                "uacp_run_id": run_id,
                "uacp_phase": frm,
                "workspace": str(root),
                "policy_version": "0.1",
                "declared_side_effects": [],
                "gate": f"{frm.upper()}->{to.upper()}",
                "record": {"result": "pass"},
                "authority_artifact": "plans/test.yaml",
            },
            phase=frm,
        )
        assert ledger.get("ok") is True, ledger

        if seeder := _SEEDERS.get((frm, to)):
            seeder(root, run_id)

        hg = heartgate.validate_transition(
            {
                "from_phase": frm,
                "to_phase": to,
                "run_id": run_id,
                "artifact_path": "plans/test.yaml",
            }
        )
        assert hg.decision == "pass", f"Heartgate blocked legit {frm}->{to}: {hg.blockers}"

        tr = d.call(
            "uacp_state_write",
            lambda a: state_machine.handle_transition(a),
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": to},
            phase=frm,
        )
        assert tr.get("ok") is True, tr

    # RESOLVE: author + register the lessons (closure) artifact BEFORE finalize so
    # the closure sweep wired into handle_finalize sees a closeable run (C4).
    _author_and_register_lessons(root, run_id)

    if not finalize:
        return

    fin = d.call(
        "uacp_state_write",
        lambda a: state_machine.handle_finalize(a),
        {"workspace": str(root), "run_id": run_id},
        phase="verify",
    )
    assert fin.get("ok") is True and fin["status"] == "resolved", fin


def _author_and_register_lessons(root: Path, run_id: str) -> None:
    """Author + register the lessons (closure) artifact for a resolved run.

    Shared by drive_happy_path (RESOLVE step) and seed_coherent_run so the
    closure C4 check (resolved run must reference a 'lessons' artifact) is
    satisfied in exactly one place.
    """
    lessons_rel = f"resolutions/{run_id}-lessons.yaml"
    (root / ".uacp" / "resolutions").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / lessons_rel).write_text(
        yaml.safe_dump(
            {
                "kind": "uacp.lessons",
                "run_id": run_id,
                "lessons": [
                    {
                        "id": "L1",
                        "category": "process",
                        "finding": "Coherent e2e run.",
                        "recommendation": "None.",
                        "applies_to_future_runs": False,
                    }
                ],
            },
            sort_keys=False,
        )
    )
    _register_artifact(root, run_id, "lessons", lessons_rel)


def _register_artifact(root: Path, run_id: str, atype: str, rel: str) -> None:
    """Register an artifact into the manifest via the real state machine."""
    out = json.loads(
        state_machine.handle_register_artifact(
            {"workspace": str(root), "run_id": run_id, "artifact_type": atype, "path": rel}
        )
    )
    assert out.get("ok") is True, out


def seed_coherent_run(root: Path, run_id: str) -> None:
    """Drive a happy-path run AND register the run-id-bearing artifacts the
    coherence validator cross-checks (scope from the plan seeder already exists;
    lessons is authored + registered for the resolved-closure check, C4/C6)."""
    drive_happy_path(root, run_id)

    # The plan seeder already wrote plans/{run_id}-scope.yaml with run_id +
    # write_paths == []. Register it so C1/C5/C6 see it.
    scope_rel = f"plans/{run_id}-scope.yaml"
    _register_artifact(root, run_id, "scope", scope_rel)

    # The lessons (closure) artifact is authored + registered by drive_happy_path
    # during RESOLVE; re-author here is idempotent (kept explicit for clarity).
    _author_and_register_lessons(root, run_id)

    # Align the run-registry write_paths with scope.write_paths ([]) so C6 is a
    # clean pass. The plan seeder leaves active_runs == []; register this run.
    registry_path = root / ".uacp" / "state" / "run-registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1",
                "active_runs": [
                    {
                        "run_id": run_id,
                        "phase": "resolved",
                        "write_paths": [],
                        "scope_artifact_path": scope_rel,
                        "started_at": 0,
                    }
                ],
            },
            sort_keys=False,
        )
    )


def _manifest_path(root: Path, run_id: str) -> Path:
    return root / ".uacp" / "state" / "runs" / f"{run_id}.yaml"


def _load_manifest_raw(root: Path, run_id: str) -> dict:
    return yaml.safe_load(_manifest_path(root, run_id).read_text())


def _write_manifest_raw(root: Path, run_id: str, data: dict) -> None:
    _manifest_path(root, run_id).write_text(yaml.safe_dump(data, sort_keys=False))


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


# ---------------------------------------------------------------- positive test
def test_coherent_run_has_zero_violations(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    violations = validate_run_coherence(temp_uacp_root, valid_run_id)
    assert violations == [], (
        f"expected zero violations, got: {[(v.code, v.message) for v in violations]}"
    )
    # Engine reports the shared Violation type, not a private dataclass.
    assert all(isinstance(v, Violation) for v in violations)


# ------------------------------------------------------------------- C1 (teeth)
def test_c1_run_id_mismatch_in_manifest(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "C1_RUN_ID_MISMATCH" not in _codes(validate_run_coherence(temp_uacp_root, valid_run_id))

    data = _load_manifest_raw(temp_uacp_root, valid_run_id)
    data["run_id"] = "uacp-test-IMPOSTER"
    _write_manifest_raw(temp_uacp_root, valid_run_id, data)

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C1_RUN_ID_MISMATCH" in codes, codes


def test_c1_run_id_mismatch_in_artifact(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "C1_RUN_ID_MISMATCH" not in _codes(validate_run_coherence(temp_uacp_root, valid_run_id))

    # Corrupt the run_id inside the lessons artifact only.
    lessons_path = temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml"
    body = yaml.safe_load(lessons_path.read_text())
    body["run_id"] = "some-other-run"
    lessons_path.write_text(yaml.safe_dump(body, sort_keys=False))

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C1_RUN_ID_MISMATCH" in codes, codes


# ------------------------------------------------------------------- C2 (teeth)
def test_c2_deleted_ledger_line_orphans_history(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert not (
        _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
        & {
            "C2_HISTORY_WITHOUT_LEDGER",
            "C2_LEDGER_WITHOUT_HISTORY",
        }
    )

    ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
    lines = ledger_path.read_text().strip().splitlines()
    ledger_path.write_text("\n".join(lines[:-1]) + "\n")  # drop one gate

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C2_HISTORY_WITHOUT_LEDGER" in codes, codes


def test_c2_spurious_ledger_line_orphans_ledger(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    ledger_path = temp_uacp_root / ".uacp" / "state" / "gate-ledger" / f"{valid_run_id}.jsonl"
    # Append a phase-transition gate that has no matching history edge.
    spurious = json.dumps(
        {"gate": "VERIFY->RESOLVED", "run_id": valid_run_id, "ts": 0, "result": "pass"}
    )
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(spurious + "\n")

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C2_LEDGER_WITHOUT_HISTORY" in codes, codes


# ------------------------------------------------------------------- C3 (teeth)
def test_c3_illegal_edge_in_history(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert not (
        _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
        & {
            "C3_PHASE_PATH_ILLEGAL_EDGE",
            "C3_PHASE_PATH_GAP",
        }
    )

    data = _load_manifest_raw(temp_uacp_root, valid_run_id)
    # Replace the first transition's destination with an illegal jump.
    for entry in data["state_history"]:
        if entry.get("event") == "phase_transition":
            entry["to_phase"] = "execute"  # triage -> execute is illegal
            break
    _write_manifest_raw(temp_uacp_root, valid_run_id, data)

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C3_PHASE_PATH_ILLEGAL_EDGE" in codes, codes


# ------------------------------------------------------------------- C4 (teeth)
def test_c4_resolved_but_finalized_at_blank(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "C4_FINALIZED_AT_MISSING" not in _codes(
        validate_run_coherence(temp_uacp_root, valid_run_id)
    )

    data = _load_manifest_raw(temp_uacp_root, valid_run_id)
    data["finalized_at"] = None  # resolved but not finalized
    _write_manifest_raw(temp_uacp_root, valid_run_id, data)

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C4_FINALIZED_AT_MISSING" in codes, codes


def test_c4_resolved_but_closure_artifact_removed(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    # Remove the lessons artifact from disk.
    (temp_uacp_root / ".uacp" / "resolutions" / f"{valid_run_id}-lessons.yaml").unlink()

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C4_CLOSURE_ARTIFACT_MISSING" in codes, codes


# ------------------------------------------------------------------- C5 (teeth)
def test_c5_artifact_points_at_nonexistent_path(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "C5_ARTIFACT_MISSING" not in _codes(validate_run_coherence(temp_uacp_root, valid_run_id))

    data = _load_manifest_raw(temp_uacp_root, valid_run_id)
    data.setdefault("artifacts", {})["scope"] = f"plans/{valid_run_id}-DOES-NOT-EXIST.yaml"
    _write_manifest_raw(temp_uacp_root, valid_run_id, data)

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C5_ARTIFACT_MISSING" in codes, codes


# ------------------------------------------------------------------- C6 (teeth)
def test_c6_scope_and_registry_write_paths_disagree(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "C6_WRITE_PATHS_DISAGREE" not in _codes(
        validate_run_coherence(temp_uacp_root, valid_run_id)
    )

    # Mutate the scope artifact's write_paths so it no longer matches the registry.
    scope_path = temp_uacp_root / ".uacp" / "plans" / f"{valid_run_id}-scope.yaml"
    body = yaml.safe_load(scope_path.read_text())
    body["write_paths"] = ["docs/something-else/"]
    scope_path.write_text(yaml.safe_dump(body, sort_keys=False))

    codes = _codes(validate_run_coherence(temp_uacp_root, valid_run_id))
    assert "C6_WRITE_PATHS_DISAGREE" in codes, codes


# --------------------------------------------------------- defensive: never raises
def test_validator_never_raises_on_missing_run(temp_uacp_root: Path):
    out = validate_run_coherence(temp_uacp_root, "no-such-run")
    assert isinstance(out, list) and out  # a violation, not an exception
    assert out[0].code.startswith("C0_")


def test_validator_never_raises_on_garbled_manifest(temp_uacp_root: Path, valid_run_id: str):
    mpath = _manifest_path(temp_uacp_root, valid_run_id)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text("this: : : not valid yaml: [")
    out = validate_run_coherence(temp_uacp_root, valid_run_id)
    assert isinstance(out, list) and out  # violation, not exception

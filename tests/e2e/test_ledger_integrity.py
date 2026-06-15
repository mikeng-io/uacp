"""E2E ledger-integrity tests: prove ``ledger_integrity.validate`` returns ZERO
violations on a genuinely complete run's real gate ledger, and that each kind of
ledger corruption is CAUGHT (teeth).

The positive test reuses ``seed_coherent_run`` from ``test_coherence`` — which
drives a real INIT -> ... -> FINALIZE run through the actual Guardian /
Heartgate / state machine / governed writers — so the happy-path gate-ledger is
the kernel's real output, not a hand-rolled fixture. Each teeth test starts from
that good ledger, corrupts EXACTLY one thing, and asserts the specific LI_ code
fires while the good ledger did NOT fire it.
"""

from __future__ import annotations

import json
from pathlib import Path

from engines.base import Violation
from engines.ledger_integrity import validate

from tests.e2e.test_coherence import seed_coherent_run


def _ledger_path(root: Path, run_id: str) -> Path:
    return root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"


def _read_lines(root: Path, run_id: str) -> list[str]:
    return _ledger_path(root, run_id).read_text().strip().splitlines()


def _write_lines(root: Path, run_id: str, lines: list[str]) -> None:
    _ledger_path(root, run_id).write_text("\n".join(lines) + "\n")


def _codes(violations) -> set[str]:
    return {v.code for v in violations}


# ---------------------------------------------------------------- positive test
def test_good_ledger_has_zero_violations(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    violations = validate(temp_uacp_root, valid_run_id)
    assert violations == [], (
        f"expected zero violations, got: {[(v.code, v.message) for v in violations]}"
    )
    # Engine reports the shared Violation type, not a private dataclass.
    assert all(isinstance(v, Violation) for v in violations)


# ------------------------------------------- LI_TIMESTAMP_NON_MONOTONIC (teeth)
def test_non_monotonic_ts_is_caught(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "LI_TIMESTAMP_NON_MONOTONIC" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Rewrite the LAST line's ts to be earlier than the first record's ts.
    lines = _read_lines(temp_uacp_root, valid_run_id)
    first = json.loads(lines[0])
    last = json.loads(lines[-1])
    last["ts"] = int(first["ts"]) - 1000  # go backwards in time
    lines[-1] = json.dumps(last, sort_keys=True)
    _write_lines(temp_uacp_root, valid_run_id, lines)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "LI_TIMESTAMP_NON_MONOTONIC" in codes, codes


# --------------------------------------------------- LI_LINE_MALFORMED (teeth)
def test_malformed_line_is_caught(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "LI_LINE_MALFORMED" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Append a line that is not valid JSON.
    with _ledger_path(temp_uacp_root, valid_run_id).open("a", encoding="utf-8") as fh:
        fh.write("this is not json {[\n")

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "LI_LINE_MALFORMED" in codes, codes


# ------------------------------------------------ LI_RUN_ID_INCONSISTENT (teeth)
def test_inconsistent_run_id_is_caught(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "LI_RUN_ID_INCONSISTENT" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Rewrite one record's run_id to a foreign value.
    lines = _read_lines(temp_uacp_root, valid_run_id)
    rec = json.loads(lines[0])
    rec["run_id"] = "uacp-test-IMPOSTER"
    lines[0] = json.dumps(rec, sort_keys=True)
    _write_lines(temp_uacp_root, valid_run_id, lines)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "LI_RUN_ID_INCONSISTENT" in codes, codes


# --------------------------------------------------- LI_DUPLICATE_GATE (teeth)
def test_duplicate_gate_is_caught(temp_uacp_root: Path, valid_run_id: str):
    seed_coherent_run(temp_uacp_root, valid_run_id)
    assert "LI_DUPLICATE_GATE" not in _codes(validate(temp_uacp_root, valid_run_id))

    # Duplicate an existing phase-transition line (same FROM->TO gate twice).
    lines = _read_lines(temp_uacp_root, valid_run_id)
    lines.append(lines[0])  # repeat the first transition gate verbatim
    _write_lines(temp_uacp_root, valid_run_id, lines)

    codes = _codes(validate(temp_uacp_root, valid_run_id))
    assert "LI_DUPLICATE_GATE" in codes, codes


# --------------------------------------------------------- defensive: no raises
def test_validator_never_raises_on_missing_ledger(temp_uacp_root: Path):
    # No run has been driven, so no ledger exists. An absent ledger is a no-op,
    # NOT a violation (a run with no transitions yet legitimately has none).
    out = validate(temp_uacp_root, "no-such-run")
    assert out == [], out


def test_validator_never_raises_on_garbled_ledger(temp_uacp_root: Path, valid_run_id: str):
    # A ledger full of garbage must produce violations, never an exception.
    path = _ledger_path(temp_uacp_root, valid_run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json\n{also not}\n[]\n")
    out = validate(temp_uacp_root, valid_run_id)
    assert isinstance(out, list) and out  # violations, not an exception
    assert "LI_LINE_MALFORMED" in _codes(out)

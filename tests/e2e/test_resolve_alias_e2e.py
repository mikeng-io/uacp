"""E2E (#114): an agent driving the DOC vocabulary `verify -> resolve` reaches
`resolved` end-to-end under PRODUCTION gate defaults.

The production-drivability keystone drives the canonical `verify -> resolved`. This
mirrors it but issues the FINAL transition with the lifecycle phase name `resolve`
(what every doc/skill/config `allowed_transitions` says) — proving the #114 alias holds
through the whole real production gate stack, and that the run still finalizes to
`resolved` with a coherent VERIFY->RESOLVED ledger.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import state_machine
import yaml

from tests.e2e.driver import Driver
from tests.e2e.test_adaptive_evidence_gate_uacp import REAL_CONFIG, REAL_VALIDATOR
from tests.e2e.test_full_lifecycle import _SEEDERS, PHASES
from tests.e2e.test_lifecycle_production_drivability import (
    _author_lessons,
    _seed_triage_artifact,
    _watermark_registered_artifacts,
)

RUN_ID = "uacp-resolve-alias-001"


@pytest.fixture
def prod_uacp_root() -> Generator[Path]:
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-resolvealias-"))
    original_cwd = os.getcwd()
    base = test_dir / ".uacp"
    for sub in (
        "state/runs",
        "state/gate-ledger",
        "state/escalations",
        "plans",
        "proposals",
        "executions",
        "resolutions",
        "verification",
        "knowledge",
    ):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (test_dir / "docs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REAL_CONFIG, test_dir / "config")
    (test_dir / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_VALIDATOR, test_dir / "scripts" / "validate_uacp_artifacts.py")
    os.chdir(test_dir)
    old = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = str(test_dir)
    try:
        yield test_dir
    finally:
        if old is None:
            os.environ.pop("UACP_ROOT", None)
        else:
            os.environ["UACP_ROOT"] = old
        os.chdir(original_cwd)
        shutil.rmtree(test_dir, ignore_errors=True)


def test_agent_drives_verify_to_resolve_and_finalizes(prod_uacp_root: Path) -> None:
    root, run_id = prod_uacp_root, RUN_ID
    driver = Driver(root, run_id)

    init = driver.call(
        "uacp_state_write",
        state_machine.handle_init,
        {"workspace": str(root), "run_id": run_id, "source": "operator-request"},
        phase="triage",
    )
    assert init.get("ok") is True, init
    _seed_triage_artifact(root, run_id)

    for frm, to in PHASES:
        if seeder := _SEEDERS.get((frm, to)):
            seeder(root, run_id)
        # THE #114 CHANGE: issue the final hop with the DOC phase name 'resolve'
        # instead of the projected status 'resolved' — an agent following the docs.
        requested_to = "resolve" if (frm, to) == ("verify", "resolved") else to
        tr = driver.call(
            "uacp_state_write",
            state_machine.handle_transition,
            {"workspace": str(root), "run_id": run_id, "from_phase": frm, "to_phase": requested_to},
            phase=frm,
        )
        assert tr.get("ok") is True, f"governed {frm}->{requested_to} blocked: {tr}"
        if (frm, to) == ("verify", "resolved"):
            # The alias canonicalized 'resolve' to 'resolved' in the result.
            assert tr["to_phase"] == "resolved", tr

    _author_lessons(root, run_id)
    _watermark_registered_artifacts(root, run_id)
    fin = driver.call(
        "uacp_state_write",
        state_machine.handle_finalize,
        {"workspace": str(root), "run_id": run_id},
        phase="verify",
    )
    assert fin.get("ok") is True, f"finalize BLOCKED: {fin}"
    assert fin.get("status") == "resolved", fin
    assert fin.get("closure") in {"pass", "warn"}, fin

    # The run reached the canonical terminal via the doc-vocabulary path, and the
    # ledger records the canonical VERIFY->RESOLVED (no 'resolve' schism leaked in).
    m = yaml.safe_load((root / ".uacp" / "state" / "runs" / f"{run_id}.yaml").read_text())
    assert m["current_phase"] == "resolved"
    assert ("verify", "resolved") in [(h["from_phase"], h["to_phase"]) for h in m["state_history"]]
    ledger_path = root / ".uacp" / "state" / "gate-ledger" / f"{run_id}.jsonl"
    gates = [
        json.loads(ln)["gate"] for ln in ledger_path.read_text().splitlines() if ln.strip()
    ]
    assert "VERIFY->RESOLVED" in gates
    # No un-canonicalized 'VERIFY->RESOLVE' gate leaked into the ledger.
    assert "VERIFY->RESOLVE" not in gates

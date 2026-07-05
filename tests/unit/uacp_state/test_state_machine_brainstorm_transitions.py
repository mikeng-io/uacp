"""State-machine transition tests for the brainstorm phase (T9)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

_STATE_DIR = Path(__file__).resolve().parents[3] / "skills" / "uacp-state" / "scripts"
if str(_STATE_DIR) not in sys.path:
    sys.path.insert(0, str(_STATE_DIR))

from state_machine import VALID_TRANSITIONS, handle_init, handle_transition


def _valid_scope_package_fields() -> dict[str, Any]:
    """The admission-contract shape the brainstorm exit gate measures (phase-7 doc /
    schema.py uacp.brainstorm_scope_package)."""
    return {
        "kind": "uacp.brainstorm_scope_package",
        "title": "Bounded scope for the run",
        "description": "A concise, gate-admissible scope crossing brainstorm->triage.",
        "in_scope": ["the one bounded thing"],
        "declared_side_effects": [],
        "authority": {"source": "User request via uacp-brainstorm"},
        "routing_advisory": "standard",
    }


def _seed_scope_package(ws: Path, run_id: str, **overrides: Any) -> Path:
    """Write a brainstorm scope package the exit-invariant glob matches:
    .uacp/brainstorm/<run_id>/07-scope-package.yaml. Field overrides (or a sentinel
    ``__delete__`` value) let a test express each malformed-field case."""
    fields = _valid_scope_package_fields()
    for key, val in overrides.items():
        if val == "__delete__":
            fields.pop(key, None)
        else:
            fields[key] = val
    pkg_dir = ws / ".uacp" / "brainstorm" / run_id
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_path = pkg_dir / "07-scope-package.yaml"
    pkg_path.write_text(yaml.safe_dump(fields, sort_keys=False), encoding="utf-8")
    return pkg_path


@pytest.fixture()
def bs_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized at brainstorm.

    Writes a minimal config/phase-transitions.yaml so the forced brainstorm-exit gate
    (which loads Heartgate to measure the scope package) can run. Omitting the ``stages``
    key makes the loader inject the codified default grammar — the same approach the
    brainstorm-entry e2e uses. The forced gate itself reads no ``stages`` config; it only
    needs Heartgate to construct (a missing config is correctly fail-closed elsewhere)."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    (ws / "config").mkdir()
    (ws / "config" / "phase-transitions.yaml").write_text(
        "ppv_rule:\n  ledger_required: false\n", encoding="utf-8"
    )
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "bs-trans-001",
        "source": "operator-request",
        "initial_phase": "brainstorm",
    }))
    assert result.get("ok"), result
    return ws


@pytest.fixture()
def triage_workspace(tmp_path: Path) -> Path:
    """Workspace with a run initialized directly at triage (existing behavior)."""
    ws = tmp_path
    (ws / ".uacp").mkdir()
    result = json.loads(handle_init({
        "workspace": str(ws),
        "run_id": "triage-direct-001",
        "source": "operator-request",
    }))
    assert result.get("ok"), result
    return ws


# --- VALID_TRANSITIONS graph assertions ---

def test_valid_transitions_includes_brainstorm_to_triage() -> None:
    assert "brainstorm" in VALID_TRANSITIONS
    assert "triage" in VALID_TRANSITIONS["brainstorm"]


def test_valid_transitions_triage_still_accepts_propose() -> None:
    """triage->propose must still work (existing edge unbroken)."""
    assert "propose" in VALID_TRANSITIONS.get("triage", set())


# --- handle_transition tests ---

def test_brainstorm_to_triage_allowed(bs_workspace: Path) -> None:
    """brainstorm->triage advances when a valid scope package satisfies the forced
    exit gate (the admission contract code measures at the membrane)."""
    _seed_scope_package(bs_workspace, "bs-trans-001")
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"
    assert result["from_phase"] == "brainstorm"
    assert result["to_phase"] == "triage"


# --- forced brainstorm exit gate (the boundary contract, enforced by code) ---

def test_brainstorm_to_triage_blocked_when_scope_package_missing(bs_workspace: Path) -> None:
    """The forced exit gate blocks the live transition when no scope package exists.

    Before this gate, handle_transition advanced brainstorm->triage with no scope
    package at all — the admission contract was only enforced on the agent-invoked
    validate_transition path, which uacp_run_transition bypasses.
    """
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert not result.get("ok"), f"expected block, got: {result}"
    assert any("07-scope-package" in b or "scope" in b.lower() for b in result.get("blockers", [])), (
        f"expected a scope-package blocker, got: {result}"
    )
    # The phase must NOT have advanced.
    manifest = yaml.safe_load(
        (bs_workspace / ".uacp" / "state" / "runs" / "bs-trans-001.yaml").read_text()
    )
    assert manifest["current_phase"] == "brainstorm"


@pytest.mark.parametrize(
    ("field", "bad_value", "needle"),
    [
        ("title", "", "title"),
        ("title", "   ", "title"),
        ("title", "__delete__", "title"),
        ("description", "", "description"),
        ("description", "__delete__", "description"),
        ("in_scope", [], "in_scope"),
        ("in_scope", "__delete__", "in_scope"),
        ("declared_side_effects", "__delete__", "declared_side_effects"),
        ("declared_side_effects", None, "declared_side_effects"),
        ("kind", "uacp.triage", "kind"),
        ("kind", "__delete__", "kind"),
        ("authority", {"source": ""}, "authority"),
        ("authority", {}, "authority"),
        ("authority", "__delete__", "authority"),
        ("routing_advisory", "block_or_clarify", "routing_advisory"),
        ("routing_advisory", "__delete__", "routing_advisory"),
    ],
)
def test_brainstorm_to_triage_blocked_on_malformed_field(
    bs_workspace: Path, field: str, bad_value: Any, needle: str
) -> None:
    """Each admission-contract field is real-field validated, not glob-existence only."""
    _seed_scope_package(bs_workspace, "bs-trans-001", **{field: bad_value})
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert not result.get("ok"), f"expected block for {field}={bad_value!r}, got: {result}"
    assert any(needle in b for b in result.get("blockers", [])), (
        f"expected a blocker mentioning {needle!r} for {field}={bad_value!r}, got: {result}"
    )


def test_brainstorm_to_triage_blocked_when_scope_package_unparseable(bs_workspace: Path) -> None:
    """Fail-closed: an unparseable scope package blocks (not a silent pass)."""
    pkg_dir = bs_workspace / ".uacp" / "brainstorm" / "bs-trans-001"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "07-scope-package.yaml").write_text("kind: [unterminated\n", encoding="utf-8")
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "triage",
    }))
    assert not result.get("ok"), f"expected block on unparseable package, got: {result}"


def test_triage_still_accepts_none_entry(triage_workspace: Path) -> None:
    """Direct triage entry (without brainstorm) must still be possible."""
    # A run started at triage should be able to advance to propose.
    result = json.loads(handle_transition({
        "workspace": str(triage_workspace),
        "run_id": "triage-direct-001",
        "from_phase": "triage",
        "to_phase": "propose",
    }))
    assert result.get("ok"), f"expected ok, got: {result}"


# NOTE: test_brainstorm_to_terminal is intentionally omitted from this slice.
# state_machine_projection() drops every ->terminal edge, so brainstorm->terminal
# is not in VALID_TRANSITIONS and handle_transition will refuse it. The explore-and-bail
# path (brainstorm->abort) is a tracked follow-up needing the aborted-status path designed.
# Add a test here when that slice ships.


def test_brainstorm_to_plan_blocked(bs_workspace: Path) -> None:
    """brainstorm->plan must be refused (phase-skipping)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "plan",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")


def test_brainstorm_to_propose_blocked(bs_workspace: Path) -> None:
    """brainstorm->propose must be refused (must flow through triage first)."""
    result = json.loads(handle_transition({
        "workspace": str(bs_workspace),
        "run_id": "bs-trans-001",
        "from_phase": "brainstorm",
        "to_phase": "propose",
    }))
    assert not result.get("ok")
    assert "not allowed" in result.get("error", "")

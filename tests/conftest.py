"""Pytest configuration and shared fixtures for UACP tests."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Ensure uacp-core and uacp-state scripts are importable
UACP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(UACP_ROOT / "skills" / "uacp-core" / "scripts"))
sys.path.insert(0, str(UACP_ROOT / "skills" / "uacp-state" / "scripts"))
sys.path.insert(0, str(UACP_ROOT / "runtime-adapters" / "hermes" / "plugins" / "uacp_guardian"))


@pytest.fixture
def temp_uacp_root() -> Generator[Path, None, None]:
    """Create a temporary UACP_ROOT directory with standard structure."""
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-test-"))
    original_cwd = os.getcwd()

    # Create standard UACP directories
    (test_dir / "state" / "runs").mkdir(parents=True)
    (test_dir / "state" / "gate-ledger").mkdir(parents=True)
    (test_dir / "state" / "escalations").mkdir(parents=True)
    (test_dir / "plans").mkdir(parents=True)
    (test_dir / "proposals").mkdir(parents=True)
    (test_dir / ".outputs").mkdir(parents=True)
    (test_dir / "verification").mkdir(parents=True)
    (test_dir / "config").mkdir(parents=True)
    (test_dir / "docs").mkdir(parents=True)

    # Create minimal guardian policy
    policy_path = test_dir / "config" / "guardian-policy.yaml"
    policy_path.write_text("""
schema_version: "0.1"
protected_categories:
  state.uacp:
    allowed_tools:
      - uacp_state_write
      - uacp_gate_ledger_append
      - uacp_run_registry_update
      - uacp_escalation_event
  docs.uacp: {}
  config.uacp: {}
  artifact.uacp: {}
tool_classification:
  uacp_state_write: state.uacp
  uacp_gate_ledger_append: state.uacp
  uacp_run_registry_update: state.uacp
  uacp_escalation_event: state.uacp
self_attesting_tools:
  names:
    - uacp_state_write
    - uacp_gate_ledger_append
    - uacp_run_registry_update
    - uacp_escalation_event
""")

    # Create minimal phase-transitions config
    phase_path = test_dir / "config" / "phase-transitions.yaml"
    phase_path.write_text("""
stages:
  triage:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to:
      - propose
  propose:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to:
      - plan
  plan:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to:
      - execute
  execute:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to:
      - verify
  verify:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to:
      - resolved
  resolved:
    allowed_tools:
      - read_file
      - write_file
      - uacp_state_write
      - uacp_gate_ledger_append
    exits_to: []
""")

    os.chdir(test_dir)
    old_uacp_root = os.environ.get("UACP_ROOT")
    os.environ["UACP_ROOT"] = str(test_dir)
    yield test_dir

    if old_uacp_root is None:
        os.environ.pop("UACP_ROOT", None)
    else:
        os.environ["UACP_ROOT"] = old_uacp_root
    os.chdir(original_cwd)
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def valid_run_id() -> str:
    """A valid run identifier for tests."""
    return "uacp-test-001"


@pytest.fixture
def another_run_id() -> str:
    """Another valid run identifier for tests."""
    return "uacp-test-002"

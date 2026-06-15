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


@pytest.fixture(autouse=True)
def _clear_uacp_config_cache():
    """Reset config.py's per-root cache around every test (override hygiene)."""
    try:
        from config import clear_config_cache
    except Exception:
        yield
        return
    clear_config_cache()
    yield
    clear_config_cache()


@pytest.fixture
def temp_uacp_root() -> Generator[Path, None, None]:
    """Create a temporary UACP_ROOT directory with standard structure."""
    test_dir = Path(tempfile.mkdtemp(prefix="uacp-test-"))
    original_cwd = os.getcwd()

    # Create standard UACP directories under the .uacp/ governed namespace.
    base = test_dir / ".uacp"
    (base / "state" / "runs").mkdir(parents=True)
    (base / "state" / "gate-ledger").mkdir(parents=True)
    (base / "state" / "escalations").mkdir(parents=True)
    (base / "plans").mkdir(parents=True)
    (base / "proposals").mkdir(parents=True)
    (base / "executions").mkdir(parents=True)
    (base / "resolutions").mkdir(parents=True)  # replaces flat .outputs/
    (base / "verification").mkdir(parents=True)
    (base / "knowledge").mkdir(parents=True)
    # config/ stays at project root this slice.
    (test_dir / "config").mkdir(parents=True)
    (test_dir / "docs").mkdir(parents=True)

    # NOTE: no per-test config/guardian-policy.yaml is written. As of Slice 3
    # GuardianPolicy.load sources the policy from config/uacp.toml [guardian]
    # via config.py (the repo-default, deep-merged with an optional
    # <root>/.uacp/config.toml override) — the legacy guardian-policy.yaml is no
    # longer read. Tests get the full repo-default policy; a test needing a
    # custom policy writes a [guardian] table into <root>/.uacp/config.toml.

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

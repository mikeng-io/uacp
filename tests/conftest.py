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
# Slice 4b T4c-1 opt-out stub — PRESERVES PRIOR TEST LAXITY.
# Before T4c-1 this synthetic config OMITTED heartgate_coherence_required_when,
# so the coherence-requirement gate was OFF in tests (the reader did
# `rule = self.config.get(...) or {}; if not rule: return`). After T4c-1 an
# ABSENT block becomes the CODE DEFAULT (ON: fires on execute->verify and
# verify->resolved with the production selectors), which would newly demand a
# `heartgate_coherence` field on the lifecycle/coherence e2e transitions and
# break them. Providing an explicit empty mapping is honored as "rule present
# but empty" -> `if not rule: return` -> gate stays OFF, exactly as before.
# Production (config/phase-transitions.yaml) ships NO block and so gets the
# enforce-by-default code default; only this test fixture opts out.
heartgate_coherence_required_when: {}
# Slice 4b T4c-2 opt-out stub — PRESERVES PRIOR TEST LAXITY.
# Before T4c-2 this synthetic config OMITTED plan_validation_gate, so the gate
# was OFF in tests (the reader did `rule = self.config.get(...) or {}; if not
# rule.get("required_ledger_gate_for_transition"): return`). After T4c-2 an
# ABSENT block becomes the CODE DEFAULT (ON: fires on plan->execute, demanding a
# PLAN_VALIDATION pass record in the gate ledger), which test_full_lifecycle does
# NOT seed -> plan->execute would block. An explicit empty mapping is read as
# "block present" and carries no required_ledger_gate_for_transition, so the
# reader's `if not required_for: return` keeps the gate OFF, exactly as before.
plan_validation_gate: {}
# Slice 4b T4c-2 opt-out stub — PRESERVES PRIOR TEST LAXITY.
# Before T4c-2 this synthetic config OMITTED ppv_rule, so the gate was OFF in
# tests (the reader did `ppv_rule = self.config.get(...) or {}; if not
# ppv_rule.get("ledger_required"): return`). After T4c-2 an ABSENT block becomes
# the CODE DEFAULT (ON: ledger_required true -> EVERY transition demands a PPV
# pass record in the gate ledger), which no test seeds -> all transition tests
# would block. Providing the block present with ledger_required false is read as
# the loaded value, so `not ppv_rule.get("ledger_required")` keeps the gate OFF,
# exactly as before. Production ships NO block and gets the enforce-by-default
# code default; only this test fixture opts out.
ppv_rule:
  ledger_required: false
# Slice 5 W2 opt-out stub (closes T4d-2) — PRESERVES PRIOR TEST LAXITY.
# Enforcement of artifact_schema.required_fields now falls back to the codified
# code default (the ~15 uacp.phase_transition required_fields) on KEY ABSENCE, not
# block absence (Slice 5 BLOCKER fix). The 4-field transition artifacts built by
# test_full_lifecycle / test_transition_matrix do NOT carry those fields, so the
# code default would block every transition. This stub opts OUT by providing the
# required_fields KEY PRESENT with an explicit empty list: Heartgate.__init__ reads
# `isinstance(schema, Mapping) and "required_fields" in schema` -> True -> uses the
# loaded `[]` -> check stays OFF, exactly as before. KEY semantics:
#   * KEY PRESENT (even `[]`) -> use the loaded value (explicit empty == deliberate
#     opt-out -> OFF). <-- this fixture, and any project disabling the gate.
#   * KEY ABSENT -> use the enforce-by-default code default (ON). <-- production
#     (config/phase-transitions.yaml), which ships the block but NOT the key.
# The unconsumed schema doctrine (fields/terminal_kind) is NOT needed here — the
# validator's terminal_kind check is gated on a `values` key which, absent here,
# sources from the code default; no test exercises validate_council_synthesis, so
# no council_synthesis_schema stub is required.
artifact_schema:
  required_fields: []
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

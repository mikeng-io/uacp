"""Production-equivalence pins for codified artifact-schema grammar (Slice 5 W2).

Closes the deferred T4d-2. The LAST three consumed bits of
config/phase-transitions.yaml were moved out of YAML into code
(engines/domain/phase_transitions.py):

  * artifact_schema.required_fields              -> PHASE_TRANSITION_REQUIRED_FIELDS
  * artifact_schema.fields.terminal_kind.values  -> PHASE_TRANSITION_TERMINAL_KIND_VALUES
  * council_synthesis_schema.required_fields     -> COUNCIL_SYNTHESIS_REQUIRED_FIELDS

These tests PIN the code defaults to the EXACT values that were in the
production YAML before the W2 slim (captured from
``git show f64e8ad:config/phase-transitions.yaml``), guaranteeing
behavior-preservation. Any divergence == a silent production change.

They also prove enforcement FIRES when the block is ABSENT (the production state
after the slim), for BOTH consumers:
  * Heartgate(config) with no artifact_schema block -> self.required_fields is the
    code default -> validate_transition BLOCKS on missing required fields.
  * the offline validator's validate_phase_transition / validate_council_synthesis
    with an empty config -> code-default required_fields enforced + the terminal_kind
    enum enforced.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from core import Heartgate
from engines.domain.phase_transitions import (
    COUNCIL_SYNTHESIS_REQUIRED_FIELDS,
    PHASE_TRANSITION_REQUIRED_FIELDS,
    PHASE_TRANSITION_TERMINAL_KIND_VALUES,
    council_synthesis_required_fields,
    phase_transition_required_fields,
    phase_transition_terminal_kind_values,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Pre-slim production literals (from f64e8ad:config/phase-transitions.yaml).
# These literals INTENTIONALLY DUPLICATE the values in
# engines/domain/phase_transitions.py. Since the production phase-transitions.yaml
# no longer holds these bits, this copy is the independent drift witness that
# proves the code default did not silently change. Do NOT "DRY this up" by
# importing from the module — that would destroy the tripwire (the test would
# then compare the module to itself).
# ---------------------------------------------------------------------------

_PROD_PHASE_TRANSITION_REQUIRED_FIELDS = [
    "transition_id",
    "run_id",
    "from_phase",
    "to_phase",
    "decision",
    "invariant_summary",
    "cluster_summary",
    "blockers",
    "warnings",
    "deferred_items",
    "authority",
    "artifact_paths",
    "phase_local_granularity",
    "composite_granularity",
    "human_involvement",
]

_PROD_TERMINAL_KIND_VALUES = [
    "none",
    "direct",
    "lightweight",
    "standard",
    "full_governance",
    "block_or_clarify",
]

_PROD_COUNCIL_SYNTHESIS_REQUIRED_FIELDS = [
    "council_id",
    "mode",
    "tier",
    "phase",
    "phase_local_granularity",
    "roles",
    "dispatch_surfaces",
    "findings",
    "verdict",
    "artifact_paths",
    "inspected_paths",
]


# ---------------------------------------------------------------------------
# Production-equivalence pins (field-by-field).
# ---------------------------------------------------------------------------


def test_phase_transition_required_fields_pin():
    assert PHASE_TRANSITION_REQUIRED_FIELDS == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS
    # accessor returns a value-equal but fresh copy (caller cannot mutate default)
    got = phase_transition_required_fields()
    assert got == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS
    got.append("__mutation__")
    assert PHASE_TRANSITION_REQUIRED_FIELDS == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS


def test_terminal_kind_values_pin():
    assert PHASE_TRANSITION_TERMINAL_KIND_VALUES == _PROD_TERMINAL_KIND_VALUES
    got = phase_transition_terminal_kind_values()
    assert got == _PROD_TERMINAL_KIND_VALUES
    got.append("__mutation__")
    assert PHASE_TRANSITION_TERMINAL_KIND_VALUES == _PROD_TERMINAL_KIND_VALUES


def test_council_synthesis_required_fields_pin():
    assert COUNCIL_SYNTHESIS_REQUIRED_FIELDS == _PROD_COUNCIL_SYNTHESIS_REQUIRED_FIELDS
    got = council_synthesis_required_fields()
    assert got == _PROD_COUNCIL_SYNTHESIS_REQUIRED_FIELDS
    got.append("__mutation__")
    assert COUNCIL_SYNTHESIS_REQUIRED_FIELDS == _PROD_COUNCIL_SYNTHESIS_REQUIRED_FIELDS


def test_production_yaml_no_longer_carries_codified_bits():
    """The slim removed exactly the three consumed bits; doctrine stays."""
    text = (REPO_ROOT / "config" / "phase-transitions.yaml").read_text()
    # The codified bits are gone (replaced by breadcrumb comments). The breadcrumb
    # comment lines mention "required_fields:"/"values:" as prose, so assert the
    # ACTIVE keys (no leading "#") are absent under the schema blocks.
    active_lines = [
        ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")
    ]
    joined = "\n".join(active_lines)
    assert "required_fields:" not in joined, (
        "artifact_schema/council_synthesis required_fields must be codified, not in YAML"
    )
    # The breadcrumbs must point at the code symbols.
    assert "PHASE_TRANSITION_REQUIRED_FIELDS" in text
    assert "PHASE_TRANSITION_TERMINAL_KIND_VALUES" in text
    assert "COUNCIL_SYNTHESIS_REQUIRED_FIELDS" in text
    # Unconsumed doctrine STAYS (sample fields/conventions still present).
    assert "heartgate_council_extension:" in text
    assert "artifact_conventions:" in text


# ---------------------------------------------------------------------------
# Behavioral: enforcement FIRES on the production (absent-block) state.
# ---------------------------------------------------------------------------


def test_heartgate_required_fields_fire_when_block_absent():
    """A config with NO artifact_schema block -> code-default required_fields ON."""
    # Minimal stages so the constructor does not need a loaded stages block; the
    # point is artifact_schema is ABSENT.
    hg = Heartgate({"stages": {"plan": {"exits_to": ["execute"]}, "execute": {"exits_to": []}}})
    assert hg.required_fields == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS

    decision = hg.validate_transition(
        {"from_phase": "plan", "to_phase": "execute", "run_id": "20260616-pin-test"}
    )
    # The 3-field artifact omits ~12 codified required fields -> missing-field blockers.
    missing = [b for b in decision.blockers if b.startswith("missing required field:")]
    assert missing, f"expected missing-required-field blockers, got: {decision.blockers}"
    # Spot-check a representative codified field is enforced.
    assert any("invariant_summary" in b for b in missing)


def test_heartgate_required_fields_off_when_block_present_empty():
    """A loaded artifact_schema block with empty required_fields opts OFF (test laxity)."""
    hg = Heartgate(
        {
            "stages": {"plan": {"exits_to": ["execute"]}, "execute": {"exits_to": []}},
            "artifact_schema": {"required_fields": []},
        }
    )
    assert hg.required_fields == []


def _load_validator():
    """Load the offline validator module fresh (mirrors Heartgate's in-process exec)."""
    validator_path = REPO_ROOT / "scripts" / "validate_uacp_artifacts.py"
    spec = importlib.util.spec_from_file_location("uacp_validate_pin", validator_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validator_imports_engines_domain_cleanly():
    """Mode (a)/(c) proof: exec'd validator resolves engines.domain via process sys.path."""
    module = _load_validator()
    # The codified accessors are reachable from the freshly exec'd module.
    assert module.phase_transition_required_fields() == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS
    assert module.phase_transition_terminal_kind_values() == _PROD_TERMINAL_KIND_VALUES
    assert module.council_synthesis_required_fields() == _PROD_COUNCIL_SYNTHESIS_REQUIRED_FIELDS


def test_validator_phase_transition_fires_when_block_absent():
    """Empty config -> code-default required_fields + terminal_kind enum enforced."""
    module = _load_validator()
    issues: list[str] = []
    # decision/terminal deliberately invalid + most required fields missing.
    module.validate_phase_transition(
        Path("plans/x.yaml"),
        {"from_phase": "plan", "to_phase": "execute", "terminal_kind": "bogus_kind"},
        {},  # no artifact_schema block -> code default
        issues,
    )
    text = "\n".join(issues)
    assert "missing required" in text or "missing required field" in text.lower() or any(
        "transition_id" in i for i in issues
    ), f"expected missing-field issues, got: {issues}"
    # terminal_kind enum (codified) enforced: 'bogus_kind' not in the code default.
    assert any("terminal_kind" in i and "bogus_kind" in i for i in issues), (
        f"expected terminal_kind enum block, got: {issues}"
    )


def test_validator_council_synthesis_fires_when_block_absent():
    """Empty config -> code-default council_synthesis required_fields enforced."""
    module = _load_validator()
    issues: list[str] = []
    module.validate_council_synthesis(
        Path("verification/x.yaml"),
        {"council_id": "c1"},  # most required fields missing
        {},  # no council_synthesis_schema block -> code default
        issues,
    )
    assert issues, "expected missing-required-field issues for a sparse council synthesis"
    # A representative codified field is demanded.
    assert any("verdict" in i for i in issues), f"expected verdict to be required, got: {issues}"


# ---------------------------------------------------------------------------
# REGRESSION (Slice 5 BLOCKER): enforcement must FIRE against the REAL repo
# config, where the schema BLOCKS are PRESENT but the consumed KEYS were
# slimmed away. The pre-fix readers keyed on block presence and took the loaded
# branch -> `schema.get("required_fields") or []` -> [] -> enforcement silently
# OFF in production. The fix keys on KEY presence; these tests load the ACTUAL
# config/phase-transitions.yaml and pin enforcement ON. They FAIL on pre-fix
# code (count 0 / no blockers) and PASS after (count 15 / blockers fire).
# ---------------------------------------------------------------------------


def _real_phase_transitions_config() -> dict:
    text = (REPO_ROOT / "config" / "phase-transitions.yaml").read_text()
    cfg = yaml.safe_load(text)
    assert isinstance(cfg, dict)
    # Guard the precondition this regression pins: the schema BLOCKS are PRESENT
    # (unconsumed doctrine stays YAML) but the consumed KEYS were slimmed out.
    assert isinstance(cfg.get("artifact_schema"), dict), "artifact_schema block must stay in YAML"
    assert "required_fields" not in cfg["artifact_schema"], (
        "artifact_schema.required_fields KEY must be codified out of YAML"
    )
    tk = cfg["artifact_schema"].get("fields", {}).get("terminal_kind", {})
    assert "values" not in tk, "terminal_kind.values KEY must be codified out of YAML"
    assert isinstance(cfg.get("council_synthesis_schema"), dict), (
        "council_synthesis_schema block must stay in YAML"
    )
    assert "required_fields" not in cfg["council_synthesis_schema"], (
        "council_synthesis_schema.required_fields KEY must be codified out of YAML"
    )
    return cfg


def test_heartgate_real_config_required_fields_enforced():
    """Heartgate.load(REPO_ROOT) against the real config -> required_fields ON (15)."""
    hg = Heartgate.load(REPO_ROOT)
    # Pre-fix: block present + key absent -> loaded branch -> [] (enforcement OFF).
    # Post-fix: key absent -> code default -> the 15 codified fields.
    assert hg.required_fields == _PROD_PHASE_TRANSITION_REQUIRED_FIELDS
    assert hg.required_fields == phase_transition_required_fields()
    assert len(hg.required_fields) == 15


def test_validator_phase_transition_real_config_blocks_bogus():
    """validate_phase_transition against the REAL config blocks bad terminal_kind + missing fields."""
    module = _load_validator()
    cfg = _real_phase_transitions_config()
    issues: list[str] = []
    module.validate_phase_transition(
        Path("plans/x.yaml"),
        {"from_phase": "plan", "to_phase": "execute", "terminal_kind": "bogus_kind"},
        cfg,  # real config: schema block PRESENT, consumed keys ABSENT
        issues,
    )
    assert issues, "real config must enforce required fields + terminal_kind enum"
    # Missing required fields fire (code default, not the empty loaded value).
    assert any("transition_id" in i for i in issues), (
        f"expected missing required-field blockers, got: {issues}"
    )
    # terminal_kind enum (codified) enforced against the real config.
    assert any("terminal_kind" in i and "bogus_kind" in i for i in issues), (
        f"expected terminal_kind enum block, got: {issues}"
    )


def test_validator_council_synthesis_real_config_demands_required_fields():
    """validate_council_synthesis against the REAL config demands codified required_fields."""
    module = _load_validator()
    cfg = _real_phase_transitions_config()
    issues: list[str] = []
    module.validate_council_synthesis(
        Path("verification/x.yaml"),
        {"council_id": "c1"},  # most required fields missing
        cfg,  # real config: council_synthesis_schema block PRESENT, key ABSENT
        issues,
    )
    assert issues, "real config must enforce council_synthesis required fields"
    assert any("verdict" in i for i in issues), f"expected verdict to be required, got: {issues}"

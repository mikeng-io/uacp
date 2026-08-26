"""Tests for the council-synthesis reviewer-grounding validator (D-17).

A reviewer report declares ``read_only_enforcement`` and ``model_authorized`` as plain fields;
trusting them is self-attestation. These tests prove the validator grounds them:

* ``model_authorized`` grounds LIVE — re-derived via ``check_model_authorized.authorize`` against
  the canonical config (framework install allowlist + a consumer ``.uacp/config.toml`` override).
  A claimed ``true`` the gate rejects does not validate.
* ``read_only_enforcement`` is a STRUCTURAL check (screening #172): a ran inspect reviewer must
  declare a KNOWN mode (``tool-mode`` | ``worktree`` | ``container``) or report SKIPPED; ``none`` /
  unknown / non-string values block. The prior containment-EVIDENCE-file mechanism was removed
  (a shell script writing into ``.uacp/`` bypassed the governed writer).

Non-vacuity: every assertion pins the specific BLOCK message (or a clean accept, no false block).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import validate_uacp_artifacts as V  # noqa: E402

_UACP_TOML = """\
[bridges.defaults]
enforce_model_allowlist = true

[bridges.opencode]
allowed_models = ["mimo-v2.5"]
"""


def _root_with_config(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "uacp.toml").write_text(_UACP_TOML)
    return tmp_path


def _blocks(issues: list[str]) -> list[str]:
    return [i for i in issues if i.startswith("BLOCK")]


def _ground(obj: dict, root: Path) -> list[str]:
    issues: list[str] = []
    V.validate_council_reviewer_grounding(Path("council.yaml"), obj, issues, root=root)
    return issues


# --------------------------------------------------------------------------- read_only_enforcement

def test_inspect_reviewer_ran_uncontained_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "none",  # ran with no containment
                "model_authorized": True,
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("read-only" in b and "SKIPPED" in b for b in blocks), blocks


# --------------------------------------------------------------------------- model_authorized (live)


def _contained(rel: str, root: Path, session: str = "sess-1") -> None:
    # No-op after the M5 simplification (screening #172): read_only_enforcement is a structural
    # check and no containment_evidence file is required. Kept so the model_authorized tests below
    # read unchanged (their `containment_evidence` field is simply ignored now).
    return None


def test_model_authorized_true_but_gate_rejects_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _contained(rel, root)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                "containment_evidence": rel,
                "model_authorized": True,          # LIE
                "resolved_model": "minimax-m3",    # NOT in opencode.allowed_models
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("model_authorized=true" in b and "REJECTS" in b for b in blocks), blocks


def test_model_authorized_grounds_true_when_gate_authorizes(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _contained(rel, root)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                "containment_evidence": rel,
                "model_authorized": True,
                "resolved_model": "mimo-v2.5",  # the approved reviewer
            }
        ],
    }
    assert _blocks(_ground(obj, root)) == []


def test_completed_review_against_unauthorized_model_is_a_block_even_if_not_claimed(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _contained(rel, root)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                "containment_evidence": rel,
                "model_authorized": False,       # honest, but it still RAN
                "resolved_model": "minimax-m3",  # unauthorized
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("does NOT authorize" in b for b in blocks), blocks


def _reviewer(model: str, ro: str = "worktree") -> dict:
    return {
        "council_id": "c-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": ro,
                "model_authorized": True,
                "resolved_model": model,
            }
        ],
    }


def test_consumer_uacp_config_override_grounds_model_authorized(tmp_path: Path):
    # screening #172 P1: a CONSUMER project (UACP_ROOT is NOT the source checkout) has no
    # <root>/config/uacp.toml — it overrides the framework allowlist via <root>/.uacp/config.toml.
    # The gate must MERGE that override (a model present ONLY in it — non-vacuity: this fails if the
    # override path isn't actually read, which is how the earlier fail-open shipped).
    root = tmp_path
    (root / ".uacp").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / "config.toml").write_text(
        '[bridges.opencode]\nallowed_models = ["consumer-only-model"]\n'
    )
    assert _blocks(_ground(_reviewer("consumer-only-model"), root)) == []


def test_override_sibling_key_does_not_disable_enforcement(tmp_path: Path):
    # screening #172 P1 (the fail-OPEN the delta re-screen caught): a consumer override that sets a
    # SIBLING key under [bridges.defaults] and does NOT restate enforce_model_allowlist must not drop
    # the install's enforce=true (a shallow merge would → gate disabled → any model authorized).
    root = tmp_path
    (root / ".uacp").mkdir(parents=True, exist_ok=True)
    (root / ".uacp" / "config.toml").write_text('[bridges.defaults]\nreasoning_level = "high"\n')
    blocks = _blocks(_ground(_reviewer("definitely-not-an-authorized-model"), root))
    assert any("does NOT authorize" in b or "REJECTS" in b for b in blocks), blocks


# --------------------------------------------------------------------------- additive / no-op


def test_no_reviewer_reports_is_a_noop(tmp_path: Path):
    root = _root_with_config(tmp_path)
    obj = {"council_id": "legacy", "verdict": "pass", "inspected_paths": ["x"]}
    assert _ground(obj, root) == []


def test_skipped_reviewer_carries_no_claim(tmp_path: Path):
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "hermes",
                "capability_profile": "inspect",
                "status": "SKIPPED",
                "skip_reason": "no authorized model",
                # declares nothing groundable; a reviewer that did not run has no claim
            }
        ],
    }
    assert _blocks(_ground(obj, root)) == []


# --------------------------------------------------------------------------- read_only structural


def test_read_only_worktree_passes_without_evidence(tmp_path: Path):
    # After the M5 simplification (screening #172): read_only_enforcement is a STRUCTURAL check —
    # a declared non-`none` enforcement passes with NO containment_evidence file (the fragile
    # evidence chain was removed); only a ran inspect reviewer with `none` enforcement blocks.
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "reviewer_reports": [
            {"bridge": "opencode", "capability_profile": "inspect", "status": "COMPLETED",
             "read_only_enforcement": "worktree", "model_authorized": True,
             "resolved_model": "mimo-v2.5"},
        ],
    }
    assert _blocks(_ground(obj, root)) == []


def test_ran_inspect_reviewer_without_enforcement_blocks(tmp_path: Path):
    # The retained structural teeth: an inspect reviewer that RAN with no read-only enforcement is a
    # containment breach (must be contained or report SKIPPED).
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "reviewer_reports": [
            {"bridge": "opencode", "capability_profile": "inspect", "status": "COMPLETED",
             "read_only_enforcement": "none", "model_authorized": True, "resolved_model": "mimo-v2.5"},
        ],
    }
    assert any("read-only" in b and "contained" in b for b in _blocks(_ground(obj, root)))


def test_unknown_read_only_mode_is_a_block(tmp_path: Path):
    # screening #172 P1: the structural check is now the only containment gate, so an unrecognized
    # or non-string read_only_enforcement (false, {}, "uncontained") must not pass.
    root = _root_with_config(tmp_path)
    for bad in ("uncontained", False, {}):
        obj = {
            "council_id": "c-1",
            "reviewer_reports": [
                {"bridge": "opencode", "capability_profile": "inspect", "status": "COMPLETED",
                 "read_only_enforcement": bad, "model_authorized": True, "resolved_model": "mimo-v2.5"},
            ],
        }
        assert any("unknown read_only_enforcement" in b for b in _blocks(_ground(obj, root))), bad

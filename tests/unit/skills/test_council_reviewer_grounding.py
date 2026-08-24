"""Tests for the council-synthesis reviewer-grounding validator (D-17).

The independence scripts — ``review_sandbox.sh`` (read-only sandbox provisioning) and
``check_model_authorized.py`` (the fail-closed model allowlist) — are real callable teeth that
until D-17 were invoked by NOTHING. A reviewer report declares ``read_only_enforcement`` and
``model_authorized`` as plain booleans; trusting them is self-attestation. These tests prove the
validator now keys each claim off the SCRIPTS' actual result:

* ``model_authorized`` grounds LIVE — re-derived via ``check_model_authorized.authorize`` against
  the run's own ``config/uacp.toml``. A claimed ``true`` the gate rejects does not validate.
* ``read_only_enforcement`` grounds on REQUIRED EVIDENCE — the run-bound ``review_sandbox.sh``
  provisioning record must resolve under UACP_ROOT, show success, and be session-bound.

Non-vacuity: every assertion pins the specific BLOCK message and that a well-formed, evidence-backed
report is accepted (no false-positive block).
"""

from __future__ import annotations

import subprocess
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


def test_read_only_claim_without_evidence_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                # NO containment_evidence — a self-declared boolean with no backing script evidence.
                "model_authorized": True,
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("containment_evidence" in b and "not proof" in b for b in blocks), blocks


def test_read_only_evidence_unresolved_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                "containment_evidence": "independence/sess-1/sandbox-provision.json",  # does not exist
                "model_authorized": True,
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("containment_evidence not found" in b for b in blocks), blocks


def _write_evidence(root: Path, rel: str, *, provisioned: bool, session: str | None) -> None:
    import json

    gov = V.base_dir(root)
    dst = gov / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    record: dict = {"tool": "review_sandbox.sh", "provisioned": provisioned}
    if session is not None:
        record["session"] = session
    dst.write_text(json.dumps(record))


def test_read_only_claim_with_resolving_run_bound_evidence_passes(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _write_evidence(root, rel, provisioned=True, session="sess-1")
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
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    assert _blocks(_ground(obj, root)) == []


def test_read_only_evidence_recording_failure_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _write_evidence(root, rel, provisioned=False, session="sess-1")  # provisioning FAILED
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
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("provisioned != true" in b for b in blocks), blocks


def test_read_only_evidence_bound_to_other_session_is_a_block(tmp_path: Path):
    root = _root_with_config(tmp_path)
    rel = "independence/other/sandbox-provision.json"
    _write_evidence(root, rel, provisioned=True, session="some-other-run")
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
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("run-bound" in b for b in blocks), blocks


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
    _write_evidence(root, rel, provisioned=True, session=session)


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


def test_model_authorized_cannot_be_re_derived_without_config_fails_closed(tmp_path: Path):
    # No config/uacp.toml under root -> the gate cannot be re-derived -> a claimed auth must not pass.
    root = tmp_path  # deliberately NO config
    obj = {
        "council_id": "c-1",
        "session_id": "sess-1",
        "reviewer_reports": [
            {
                "bridge": "opencode",
                "capability_profile": "inspect",
                "status": "COMPLETED",
                "read_only_enforcement": "worktree",
                "containment_evidence": "independence/sess-1/sandbox-provision.json",
                "model_authorized": True,
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("could not be re-derived" in b for b in blocks), blocks


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


# --------------------------------------------------------------------------- script produces evidence


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def test_review_sandbox_writes_run_bound_provisioning_evidence(tmp_path: Path):
    """review_sandbox.sh must now PRODUCE the evidence the validator requires (D-17)."""
    import json

    script = _REPO / "skills" / "uacp-council" / "scripts" / "review_sandbox.sh"
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "t@t.t", cwd=tmp_path)
    _git("config", "user.name", "t", cwd=tmp_path)
    (tmp_path / "f.txt").write_text("x\n")
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-qm", "init", cwd=tmp_path)

    ev = tmp_path / "evidence" / "prov.json"
    res = subprocess.run(
        ["bash", str(script), "provision", "sess-9", "HEAD", str(ev)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    # stdout is STILL only the sandbox path (callers capture $SANDBOX)
    assert Path(res.stdout.strip()).is_dir()
    assert ev.exists(), "provisioning evidence was not written"
    record = json.loads(ev.read_text())
    assert record["provisioned"] is True
    assert record["session"] == "sess-9"


def test_read_only_evidence_missing_session_is_a_block(tmp_path: Path):
    # Codex #172 P2: a provisioning record with NO `session` must fail like a mismatch — an unbound
    # record could otherwise be reused across councils despite the run-binding contract.
    root = _root_with_config(tmp_path)
    rel = "independence/sess-1/sandbox-provision.json"
    _write_evidence(root, rel, provisioned=True, session=None)  # NO session field
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
                "resolved_model": "mimo-v2.5",
            }
        ],
    }
    blocks = _blocks(_ground(obj, root))
    assert any("run-bound" in b and "no session" in b for b in blocks), blocks

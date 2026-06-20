"""Phase B increment 2b — the artifact-integrity engine (detection at the gate).

Compares each RECORDED artifact's current content hash to its watermark; a mismatch
is an out-of-band tamper (a write that did not go through the governed writer) and
blocks. Unrecorded artifacts are not verified (no baseline) — so the engine is a
no-op on runs that never used the governed writer, and only RECORDED artifacts are
trusted. Registered in ENGINES, so it runs at closure via run_all_engines.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

import json

from engines.artifact_integrity import validate_artifact_integrity
from engines.domain.artifact_hashes import load_hash_index, record_hash
from governed_handlers import _handle_uacp_artifact_write


def _seed(tmp_path: Path, rel: str, content: str, *, record: bool = True) -> Path:
    p = tmp_path / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    if record:
        record_hash(tmp_path, "r", rel, content)
    return p


def test_recorded_unchanged_artifact_is_clean(tmp_path):
    _seed(tmp_path, "plans/p.yaml", "body")
    assert validate_artifact_integrity(tmp_path, "r") == []


def test_tampered_artifact_is_blocked(tmp_path):
    p = _seed(tmp_path, "plans/p.yaml", "body")
    p.write_text("forged body", encoding="utf-8")  # out-of-band edit; recorded hash unchanged
    vs = validate_artifact_integrity(tmp_path, "r")
    assert any(v.code == "AI_TAMPERED" and v.severity == "block" for v in vs), vs
    assert any(v.detail.get("artifact") == "plans/p.yaml" for v in vs), vs
    # non-vacuity: restoring the original content clears the violation
    p.write_text("body", encoding="utf-8")
    assert validate_artifact_integrity(tmp_path, "r") == []


def test_recorded_but_deleted_file_is_blocked(tmp_path):
    p = _seed(tmp_path, "plans/p.yaml", "body")
    p.unlink()
    assert any(v.code == "AI_MISSING" for v in validate_artifact_integrity(tmp_path, "r"))


def test_unrecorded_artifact_is_not_verified(tmp_path):
    # written but never recorded through the governed writer -> no baseline -> skipped.
    _seed(tmp_path, "plans/p.yaml", "body", record=False)
    assert validate_artifact_integrity(tmp_path, "r") == []


def test_never_raises_on_missing_index(tmp_path):
    assert validate_artifact_integrity(tmp_path, "nope") == []


# --- writer integration (2c): the governed writer records the watermark --------
def _write_args(root, rel, content):
    return {
        "workspace": str(root),
        "target_path": rel,
        "content": content,
        "reason": "test write",
        "authority_artifact": "plans/auth.yaml",
        "uacp_run_id": "uacp-test-001",
        "uacp_phase": "execute",
        "policy_version": "0.1",
        "declared_side_effects": [],
    }


def test_governed_writer_records_hash_then_tamper_detected(temp_uacp_root):
    content = "kind: uacp.plan\nbody: original\n"
    res = json.loads(_handle_uacp_artifact_write(_write_args(temp_uacp_root, "plans/art.yaml", content)))
    assert res.get("ok") is True, res
    # the governed write recorded a watermark...
    assert load_hash_index(temp_uacp_root, "uacp-test-001").get("plans/art.yaml"), "no watermark recorded"
    # ...and is clean immediately after.
    assert validate_artifact_integrity(temp_uacp_root, "uacp-test-001") == []
    # An out-of-band edit (not through the writer) is detected.
    (temp_uacp_root / ".uacp" / "plans" / "art.yaml").write_text(
        "kind: uacp.plan\nbody: FORGED\n", encoding="utf-8")
    vs = validate_artifact_integrity(temp_uacp_root, "uacp-test-001")
    assert any(v.code == "AI_TAMPERED" and v.detail.get("artifact") == "plans/art.yaml" for v in vs), vs

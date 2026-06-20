"""Phase B hardening #6 — run artifact integrity at EVERY transition, not just
closure. Closes the swap-and-restore-around-the-gate timing gap: a recorded
artifact tampered out-of-band must block the next phase transition, not wait for
RESOLVE. Heartgate gains `_validate_artifact_integrity`, called from
validate_transition; it is a no-op on runs with no watermark index.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Heartgate
from engines.domain.artifact_hashes import record_hash


def _seed_recorded(root: Path, rel: str, content: str) -> Path:
    p = root / ".uacp" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    record_hash(root, "uacp-test-001", rel, content)
    return p


def test_transition_blocks_on_tampered_recorded_artifact(temp_uacp_root):
    art = _seed_recorded(temp_uacp_root, "plans/p.yaml", "kind: uacp.plan\n")
    art.write_text("kind: uacp.plan\nFORGED: true\n", encoding="utf-8")  # out-of-band tamper
    hg = Heartgate({}, uacp_root=temp_uacp_root)
    blockers: list = []
    hg._validate_artifact_integrity({"run_id": "uacp-test-001"}, blockers)
    assert any("AI_TAMPERED" in b for b in blockers), blockers


def test_transition_clean_when_recorded_artifact_intact(temp_uacp_root):
    # Non-vacuous: tamper -> blocks (above); intact -> no integrity blocker here.
    _seed_recorded(temp_uacp_root, "plans/p.yaml", "kind: uacp.plan\n")
    hg = Heartgate({}, uacp_root=temp_uacp_root)
    blockers: list = []
    hg._validate_artifact_integrity({"run_id": "uacp-test-001"}, blockers)
    assert blockers == [], blockers


def test_transition_integrity_noop_without_index(temp_uacp_root):
    # A run that never used the governed writer has no watermark index -> no-op.
    hg = Heartgate({}, uacp_root=temp_uacp_root)
    blockers: list = []
    hg._validate_artifact_integrity({"run_id": "uacp-test-001"}, blockers)
    assert blockers == [], blockers

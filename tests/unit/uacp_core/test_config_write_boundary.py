"""uacp_config_write must accept every path load_phase_transitions actually reads.

Regression for a P1 Codex caught on PR #195: the read side (loaders.load_phase_transitions)
was taught to resolve a project override at ``.uacp/config/phase-transitions.yaml``, but the
governed writer (uacp_config_write -> _validate_canonical_target) still only accepted bare
``config/**``. A write to ``.uacp/config/**`` reported success while the kernel silently kept
using its shipped default -- a write with no effect, exactly the class of defect the P1
criterion names (a silently wrong result a later gate would accept).
"""

from __future__ import annotations

import json
from pathlib import Path

from governed_handlers import _handle_uacp_config_write


def _args(root: Path, target_path: str) -> dict:
    return {
        "target_path": target_path,
        "content": "stages: {}\n",
        "reason": "test override",
        "authority_artifact": "plans/test.yaml",
        "workspace": str(root),
        "uacp_run_id": "r1",
        "uacp_phase": "execute",
        "policy_version": "0.1",
        "declared_side_effects": [],
    }


def test_accepts_the_project_override_location(temp_uacp_root: Path) -> None:
    """.uacp/config/** -- the location load_phase_transitions actually reads -- must
    succeed, not silently no-op behind a reported ok."""
    result = json.loads(
        _handle_uacp_config_write(_args(temp_uacp_root, ".uacp/config/phase-transitions.yaml"))
    )
    assert result.get("ok") is True, result
    written = temp_uacp_root / ".uacp" / "config" / "phase-transitions.yaml"
    assert written.read_text() == "stages: {}\n"


def test_still_accepts_the_bare_doctrine_location(temp_uacp_root: Path) -> None:
    """The original config/** boundary (this repo's own doctrine files) is unchanged."""
    (temp_uacp_root / "config").mkdir(parents=True, exist_ok=True)
    result = json.loads(
        _handle_uacp_config_write(_args(temp_uacp_root, "config/phase-transitions.yaml"))
    )
    assert result.get("ok") is True, result
    assert (temp_uacp_root / "config" / "phase-transitions.yaml").read_text() == "stages: {}\n"


def test_rejects_a_path_outside_either_boundary(temp_uacp_root: Path) -> None:
    result = json.loads(
        _handle_uacp_config_write(_args(temp_uacp_root, "docs/phase-transitions.yaml"))
    )
    assert "error" in result
    assert "config/" in result["error"] and ".uacp/config/" in result["error"]


def test_a_config_write_at_the_project_override_location_is_what_the_loader_reads(
    temp_uacp_root: Path,
) -> None:
    """End-to-end: a governed write to .uacp/config/ is the same file
    load_phase_transitions resolves as the project override."""
    from engines.io import load_phase_transitions

    result = json.loads(
        _handle_uacp_config_write(
            _args(
                temp_uacp_root,
                ".uacp/config/phase-transitions.yaml",
            )
            | {"content": "marker: from_governed_writer\nstages: {}\n"}
        )
    )
    assert result.get("ok") is True, result
    loaded = load_phase_transitions(temp_uacp_root)
    assert loaded.error is None
    assert loaded.value.get("marker") == "from_governed_writer"

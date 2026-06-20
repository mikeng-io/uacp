"""Phase B increment 1 — Guardian blocks RAW writes to governed UACP artifact paths.

D25: the governed writer (uacp_artifact_write) must be the ONLY path that writes a
governed artifact, so a forged derives_from can't be smuggled in via a native
Edit/Write. This wires the enforcement the policy ALREADY declares
(config/uacp.toml [guardian.protected_categories."artifact.uacp"], default block,
allowed_tools = [uacp_artifact_write]) but never implemented: a path-based rule
mirroring _is_direct_uacp_state_write, over the 8 governed artifact roots
(plans/proposals/executions/verification/resolutions/knowledge/lessons/brainstorm,
matching governed_handlers allowed_roots).
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Guardian, GuardianPolicy, make_event

_ARTIFACT_ROOTS = ("plans", "proposals", "executions", "verification",
                   "resolutions", "knowledge", "lessons", "brainstorm")


def _g(root: Path) -> Guardian:
    return Guardian(GuardianPolicy.load(str(root)))


def _evt(root: Path, tool_name: str, rel: str, *, under_uacp: bool = True):
    target = (root / ".uacp" / rel) if under_uacp else (root / rel)
    return make_event(
        tool_name=tool_name,
        args={
            "file_path": str(target),
            "uacp_run_id": "uacp-test-001",
            "uacp_phase": "execute",
            "workspace": str(root),
            "policy_version": "0.1",
            "authority_artifact": "plans/test.yaml",
            "declared_side_effects": [],
        },
        filesystem_guard_verified=True,  # pass containment so we reach the writer-choice logic
    )


def test_path_is_under_artifact_root(temp_uacp_root):
    g = _g(temp_uacp_root)
    base = temp_uacp_root / ".uacp"
    for root in _ARTIFACT_ROOTS:
        assert g._path_is_under_artifact_root(str(base / root / "x.yaml")) is True, root
    # state/ is its own protected category; a non-.uacp project file is outside.
    assert g._path_is_under_artifact_root(str(base / "state" / "x.yaml")) is False
    assert g._path_is_under_artifact_root(str(temp_uacp_root / "src" / "x.py")) is False


def test_native_write_to_artifact_path_is_blocked(temp_uacp_root):
    g = _g(temp_uacp_root)
    d = g.evaluate(_evt(temp_uacp_root, "write_file", "plans/forged.yaml"))
    assert d.decision == "block", d
    assert d.category == "artifact.uacp", d
    assert "uacp_artifact_write" in d.reason, d.reason


def test_native_write_blocked_for_each_artifact_root(temp_uacp_root):
    g = _g(temp_uacp_root)
    for root in _ARTIFACT_ROOTS:
        d = g.evaluate(_evt(temp_uacp_root, "write_file", f"{root}/x.yaml"))
        assert d.decision == "block" and d.category == "artifact.uacp", (root, d)


def test_uacp_artifact_write_to_artifact_path_is_allowed(temp_uacp_root):
    # Non-vacuity: the block is specific to NON-sanctioned tools. The governed
    # writer must still be allowed to write the same path.
    g = _g(temp_uacp_root)
    d = g.evaluate(_evt(temp_uacp_root, "uacp_artifact_write", "plans/legit.yaml"))
    assert d.decision != "block", d


def test_native_write_to_state_stays_state_category(temp_uacp_root):
    # A write under state/ is owned by the EARLIER state rule (state.uacp), not the
    # artifact rule — proves the two path rules are distinct, not overlapping.
    g = _g(temp_uacp_root)
    d = g.evaluate(_evt(temp_uacp_root, "write_file", "state/runs/x.yaml"))
    assert d.decision == "block" and d.category == "state.uacp", d


def test_ordinary_project_edit_not_blocked_by_artifact_rule(temp_uacp_root):
    # An edit to a non-governed project file must NOT be captured by artifact.uacp
    # (it falls through to the ordinary file.write surface).
    g = _g(temp_uacp_root)
    d = g.evaluate(_evt(temp_uacp_root, "write_file", "src/app.py", under_uacp=False))
    assert d.category != "artifact.uacp", d

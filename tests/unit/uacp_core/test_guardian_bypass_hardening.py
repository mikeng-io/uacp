"""Phase B increment 1b — close the adversarial-review bypasses of the governed-
path write block (prevention).

The original block (mirroring _is_direct_uacp_state_write) only fired for category
in {file.write, exec.shell, exec.code_with_tool_proxy} and only inspected 6 arg
keys. An adversarial review forged a full manifest by:
  - using an UNMAPPED tool (e.g. apply_patch -> external.unknown_mutator -> ALLOW),
  - or placing the path under an un-inspected arg key (destination/dest/...),
  - or writing the detection anchor state/hashes/ the same way,
  - or via provider=unknown whose directive leaked as a category.

These tests reproduce each bypass through the real Guardian and assert it is now a
hard BLOCK. They are paired with the existing allow-tests (sanctioned writer +
ordinary project edit) so the hardening is default-deny for mutation, not deny-all.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SCRIPTS = Path(__file__).resolve().parents[3] / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

from core import Guardian, GuardianPolicy, make_event


def _g(root: Path) -> Guardian:
    return Guardian(GuardianPolicy.load(str(root)))


def _ctx(root: Path, **extra):
    base = {
        "uacp_run_id": "uacp-test-001",
        "uacp_phase": "execute",
        "workspace": str(root),
        "policy_version": "0.1",
        "authority_artifact": "plans/test.yaml",
        "declared_side_effects": [],
    }
    base.update(extra)
    return base


def test_unmapped_mutator_tool_cannot_write_manifest(temp_uacp_root):
    # apply_patch is unmapped -> external.unknown_mutator. It must NOT be able to
    # write a manifest artifact (the headline forge).
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="apply_patch",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "plans" / "forged.yaml")),
                    filesystem_guard_verified=True)
    d = g.evaluate(ev)
    assert d.decision == "block", d


def test_unmapped_mutator_tool_cannot_write_state_run_manifest(temp_uacp_root):
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="apply_patch",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "state" / "runs" / "r.yaml")),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision == "block", g.evaluate(ev)


def test_unmapped_mutator_tool_cannot_write_hash_index(temp_uacp_root):
    # The detection anchor must be protected too, or tamper+rewrite defeats it.
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="apply_patch",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "state" / "hashes" / "r.json")),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision == "block", g.evaluate(ev)


def test_alternate_path_arg_key_cannot_evade_block(temp_uacp_root):
    # write_file (mapped -> file.write) with the path under an un-inspected key.
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="write_file",
                    args=_ctx(temp_uacp_root, destination=str(temp_uacp_root / ".uacp" / "plans" / "p.yaml"),
                              content="x"),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision == "block", g.evaluate(ev)


def test_unknown_provider_directive_not_treated_as_category(temp_uacp_root):
    # provider=unknown maps to a symbolic directive ("block_pending_heartgate"),
    # which must NOT leak through classify() as a category that defaults to allow.
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="apply_patch", tool_provider="unknown",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "plans" / "p.yaml")),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision == "block", g.evaluate(ev)


# --- default-deny, not deny-all: the legitimate paths must still work -----------
def test_sanctioned_writer_still_allowed(temp_uacp_root):
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="uacp_artifact_write",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "plans" / "ok.yaml")),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision != "block", g.evaluate(ev)


def test_reading_a_manifest_path_is_not_blocked(temp_uacp_root):
    # A read tool touching a governed path must NOT be blocked (mutation-scoped).
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="read_file",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / ".uacp" / "plans" / "p.yaml")))
    assert g.evaluate(ev).decision != "block", g.evaluate(ev)


def test_ordinary_project_edit_still_allowed(temp_uacp_root):
    g = _g(temp_uacp_root)
    ev = make_event(tool_name="write_file",
                    args=_ctx(temp_uacp_root, file_path=str(temp_uacp_root / "src" / "app.py"), content="x"),
                    filesystem_guard_verified=True)
    assert g.evaluate(ev).decision != "block", g.evaluate(ev)

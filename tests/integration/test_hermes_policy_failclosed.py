"""MAJOR 3 regression: the Hermes ``uacp_guardian`` adapter must FAIL CLOSED —
not raise — when the UACP root cannot be resolved.

``resolve_uacp_root`` is now fail-closed (raises ``UacpRootUnresolvedError`` when no
explicit root and neither ``UACP_ROOT`` nor ``HERMES_HOME`` is set). That call
sits inside ``GuardianPolicy.load`` OUTSIDE the policy-load ``try``, and
``UacpRootUnresolvedError`` is a *sibling* of ``GuardianPolicyError`` (both
``RuntimeError``). The adapter's pre-tool-call path caught only
``GuardianPolicyError``, so with no root env the exception propagated UNCAUGHT
past the clean ``_block_for_policy_error`` path.

These tests assert the adapter returns a clean BLOCK decision (defense-in-depth,
fail-closed) instead of raising.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Import the Hermes adapter as a package (relative imports) — mirror the path
# setup in test_tool_registry_parity.py.
_PLUGINS_DIR = _REPO_ROOT / "runtime-adapters" / "hermes" / "plugins"
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

import uacp_guardian  # noqa: E402


def _reset_adapter_policy() -> None:
    uacp_guardian._POLICY = None
    uacp_guardian._POLICY_ERROR = ""
    uacp_guardian._PHASE_CONFIG = None


def test_on_pre_tool_call_fail_closed_when_root_unresolved(monkeypatch):
    monkeypatch.delenv("UACP_ROOT", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    _reset_adapter_policy()
    try:
        # A mutating tool with no resolvable root: must NOT raise, must BLOCK.
        result = uacp_guardian.on_pre_tool_call(tool_name="write_file", args={"file_path": "/x"})
        assert result is not None, "expected a clean fail-closed block, got allow"
        assert result.get("action") == "block", result
    finally:
        _reset_adapter_policy()


def test_bare_read_still_allowed_when_root_unresolved(monkeypatch):
    """NON-VACUITY: the block is specific to mutators. A bare read with no run
    context still passes (mirrors _block_for_policy_error) — proving the block
    above is the policy-error path, not a blanket raise-or-block."""
    monkeypatch.delenv("UACP_ROOT", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("UACP_RUN_ID", raising=False)
    _reset_adapter_policy()
    try:
        result = uacp_guardian.on_pre_tool_call(tool_name="read_file", args={"file_path": "/x"})
        assert result is None, f"bare read must pass (None), got: {result!r}"
    finally:
        _reset_adapter_policy()

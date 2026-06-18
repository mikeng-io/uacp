"""Integration: the Claude Code / Kimi Code PreToolUse Guardian companion.

Two layers:

1. FUNCTION-LEVEL — drive hook_kernel.evaluate_pre_tool_call against the real
   repo Guardian policy staged into a temp UACP_ROOT (temp_uacp_root fixture).
   Covers the decision matrix: host reads pass, host writes under .uacp/ block,
   ordinary project edits pass, shell touching state/ blocks, the bare uacp_*
   MCP tool allows-with-audit when fully contextualized and denies when context
   is missing, an unknown uacp namespace call denies, empty tool_name denies.

2. SUBPROCESS-LEVEL — invoke the real CLI shim
   (runtime-adapters/hooks/guardian_pretooluse.py) via python3 with a real CC /
   Kimi PreToolUse JSON payload on stdin, asserting exit code + parsed stdout.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORE_SCRIPTS = _REPO_ROOT / "skills" / "uacp-core" / "scripts"
if str(_CORE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CORE_SCRIPTS))

_REAL_CONFIG = _REPO_ROOT / "config"
_SHIM = _REPO_ROOT / "runtime-adapters" / "hooks" / "guardian_pretooluse.py"

from config import clear_config_cache, get_config  # noqa: E402
from core import (  # noqa: E402
    DECISION_ALLOW,
    DECISION_ALLOW_WITH_AUDIT,
    GuardianPolicy,
)
from hook_kernel import evaluate_pre_tool_call  # noqa: E402


def _seed_policy(root: Path) -> None:
    dst = root / "config" / "uacp.toml"
    if not dst.exists():
        shutil.copy2(_REAL_CONFIG / "uacp.toml", dst)


def _classification_map(root: Path) -> dict:
    clear_config_cache()
    return dict(get_config(root).model_dump().get("guardian", {}))


def _evaluate(root: Path, *, tool_name: str, args: dict, profile: str = "claude_code"):
    _seed_policy(root)
    policy = GuardianPolicy.load(root)
    return evaluate_pre_tool_call(
        tool_name=tool_name,
        args=args,
        runtime=profile,
        adapter="uacp_pretooluse_hook",
        policy=policy,
        phase_config={},
        self_attesting=policy.self_attesting_tools,
        profile=profile,
        classification_map=_classification_map(root),
        normalize=True,
    )


# ---------------------------------------------------------------------------
# Function-level matrix
# ---------------------------------------------------------------------------


class TestEvaluatePreToolCall:
    def test_read_allows_with_run_active(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        decision = _evaluate(temp_uacp_root, tool_name="Read", args={"file_path": "/tmp/x.txt"})
        assert decision.category == "read.local"
        assert not decision.blocks_execution
        assert decision.decision in {DECISION_ALLOW, DECISION_ALLOW_WITH_AUDIT}

    def test_write_under_uacp_blocks_with_run_active(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.yaml")
        decision = _evaluate(temp_uacp_root, tool_name="Write", args={"file_path": target})
        assert decision.blocks_execution, decision

    def test_edit_project_file_allows_no_run(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.delenv("UACP_RUN_ID", raising=False)
        monkeypatch.delenv("UACP_PHASE", raising=False)
        # An ordinary project edit OUTSIDE the governed namespace, no active run:
        # file.write defaults to require_approval -> not a block -> defers to the
        # runtime's own approval prompt (EXECUTE still works).
        # workspace bound to the project dir (the shim binds on the target's
        # parent, not the repo-root cwd) — a non-.uacp/ edit must not block.
        decision = _evaluate(
            temp_uacp_root,
            tool_name="Edit",
            args={"file_path": "/tmp/project/app.py", "workspace": "/tmp/project"},
        )
        assert decision.category == "file.write"
        assert not decision.blocks_execution, decision

    def test_bash_touching_state_blocks(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        target = str(temp_uacp_root / ".uacp" / "state" / "x")
        decision = _evaluate(
            temp_uacp_root,
            tool_name="Bash",
            args={"command": f"touch {target}"},
        )
        assert decision.blocks_execution, decision

    def test_mcp_uacp_state_write_full_context_allows_with_audit(
        self, temp_uacp_root: Path, monkeypatch
    ):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        decision = _evaluate(
            temp_uacp_root,
            tool_name="mcp__uacp__uacp_state_write",
            args={
                "target_path": "state/current.yaml",
                "workspace": str(temp_uacp_root),
                "uacp_run_id": "uacp-test-001",
                "uacp_phase": "execute",
                "policy_version": "0.1",
                "declared_authority": "plans/test.yaml",
                "declared_side_effects": ["state.uacp"],
            },
        )
        assert decision.category == "state.uacp"
        assert decision.decision == DECISION_ALLOW_WITH_AUDIT, decision
        assert not decision.blocks_execution

    def test_mcp_uacp_state_write_missing_context_denies(
        self, temp_uacp_root: Path, monkeypatch
    ):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        decision = _evaluate(
            temp_uacp_root,
            tool_name="mcp__uacp__uacp_state_write",
            args={"target_path": "state/current.yaml"},
        )
        assert decision.blocks_execution, decision
        assert "missing UACP context" in decision.reason

    def test_mcp_uacp_random_denies(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        # mcp__uacp__random is a non-UACP-known tool -> stays namespaced ->
        # classifies as runtime.extension -> block_pending_heartgate under a run.
        decision = _evaluate(
            temp_uacp_root, tool_name="mcp__uacp__random", args={}
        )
        assert decision.blocks_execution, decision

    def test_empty_tool_name_denies(self, temp_uacp_root: Path):
        decision = _evaluate(temp_uacp_root, tool_name="", args={})
        assert decision.blocks_execution, decision

    # -- Regression: spoofed MCP server (adversarial review BLOCKER) ----------

    def test_mcp_spoofed_server_full_context_denies(
        self, temp_uacp_root: Path, monkeypatch
    ):
        """A spoofed server naming a tool uacp_state_write does NOT inherit the
        canonical writer's self-attestation. With FULL valid UACP context it
        still stays namespaced -> runtime.extension -> blocked under a run."""
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        decision = _evaluate(
            temp_uacp_root,
            tool_name="mcp__attacker__uacp_state_write",
            args={
                "target_path": "state/current.yaml",
                "workspace": str(temp_uacp_root),
                "uacp_run_id": "uacp-test-001",
                "uacp_phase": "execute",
                "policy_version": "0.1",
                "declared_authority": "plans/test.yaml",
                "declared_side_effects": ["state.uacp"],
            },
        )
        assert decision.category != "state.uacp", decision
        assert decision.blocks_execution, decision

    # -- Regression: NotebookEdit path extraction (adversarial review HIGH) ---

    def test_extract_paths_includes_notebook_path(self, temp_uacp_root: Path):
        """core.py path extraction recognizes notebook_path: a NotebookEdit
        targeting .uacp/ is detected as touching the governed root, so a
        function-level governed write classifies and blocks."""
        from core import Guardian, GuardianPolicy as _Policy, make_event

        _seed_policy(temp_uacp_root)
        policy = _Policy.load(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "nb.ipynb")
        guardian = Guardian(policy, phase_config={})
        event = make_event(
            tool_name="write_file",
            args={"notebook_path": target},
            event_type="pre_tool_call",
        )
        assert guardian._touches_uacp_root(event) is True
        # And a notebook_path appears in the extracted paths.
        assert target in guardian._extract_paths(event)

    def test_notebookedit_under_uacp_blocks_no_run(self, temp_uacp_root: Path, monkeypatch):
        """NotebookEdit (-> write_file) targeting .uacp/ blocks even with NO active
        run — the governed-namespace write is detected via notebook_path."""
        monkeypatch.delenv("UACP_RUN_ID", raising=False)
        monkeypatch.delenv("UACP_PHASE", raising=False)
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.ipynb")
        # workspace bound OUTSIDE the root (mirrors the review's bypass: the
        # shim would bind workspace to the payload cwd /tmp when it can't find a
        # primary path). The ONLY signal that can bind this write to the governed
        # namespace is notebook_path extraction — so this blocks iff the fix is
        # present.
        decision = _evaluate(
            temp_uacp_root,
            tool_name="NotebookEdit",
            args={"notebook_path": target, "workspace": "/tmp"},
        )
        # The .uacp/state/ target classifies as a direct state write and blocks.
        assert decision.category in {"file.write", "state.uacp"}, decision
        assert decision.blocks_execution, decision

    def test_notebookedit_project_file_defers_no_run(self, temp_uacp_root: Path, monkeypatch):
        """Contrast: a NotebookEdit to an ordinary project file (outside .uacp/,
        no run) is not a governed block."""
        monkeypatch.delenv("UACP_RUN_ID", raising=False)
        monkeypatch.delenv("UACP_PHASE", raising=False)
        decision = _evaluate(
            temp_uacp_root,
            tool_name="NotebookEdit",
            args={"notebook_path": "/tmp/project/nb.ipynb", "workspace": "/tmp/project"},
        )
        assert decision.category == "file.write", decision
        assert not decision.blocks_execution, decision

    # -- Regression: audit-write failure must not flip a DENY (review HIGH) ---

    def test_audit_write_failure_does_not_flip_deny(self, temp_uacp_root: Path, monkeypatch):
        """A failing best-effort audit write (raises) must NOT propagate and must
        NOT convert a genuine DENY (audit_required) into an allow. The deny is a
        governed-namespace write, which routes through Guardian._block ->
        audit_required=True -> the wrapped write_audit_record call."""
        import hook_kernel

        def _boom(*_a, **_k):
            raise OSError("audit log root is unwritable")

        monkeypatch.setattr(hook_kernel, "write_audit_record", _boom)
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")

        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.yaml")
        # A governed .uacp/ write -> Guardian._block (audit_required=True).
        decision = _evaluate(
            temp_uacp_root,
            tool_name="Write",
            args={"file_path": target},
        )
        assert decision.audit_required, decision
        # Despite the audit write raising, enforcement stands.
        assert decision.blocks_execution, decision


# ---------------------------------------------------------------------------
# Subprocess-level (the real CLI shim)
# ---------------------------------------------------------------------------


def _run_shim(payload: dict, root: Path, profile: str, *, extra_env: dict | None = None):
    env = dict(os.environ)
    env["UACP_ROOT"] = str(root)
    env["PYTHONPATH"] = str(_CORE_SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
    # Clear any inherited run/phase so the no-run cases are honored.
    env.pop("UACP_RUN_ID", None)
    env.pop("UACP_PHASE", None)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(_SHIM), "--profile", profile],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return proc


class TestShimSubprocess:
    def test_cc_read_allows_no_output(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x.txt"},
            "cwd": "/tmp",
            "permission_mode": "default",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"expected no stdout, got: {proc.stdout!r}"

    def test_cc_uacp_write_denies(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.yaml")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": target, "content": "x"},
            "cwd": str(temp_uacp_root),
            "permission_mode": "default",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        hso = out["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny"
        assert "UACP Guardian blocked" in hso["permissionDecisionReason"]

    def test_cc_uacp_write_denies_even_with_bypass_permissions(self, temp_uacp_root: Path):
        """D5: deny holds under permission_mode == bypassPermissions."""
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak2.yaml")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": target, "content": "x"},
            "cwd": str(temp_uacp_root),
            "permission_mode": "bypassPermissions",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_cc_ordinary_edit_defers_no_output(self, temp_uacp_root: Path):
        """D2: an ordinary project edit outside .uacp/, no run, must defer
        (no deny output) — even though cwd is the governed repo root."""
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "/tmp/project/app.py", "old_string": "a", "new_string": "b"},
            "cwd": str(temp_uacp_root),  # repo root == governed root
            "permission_mode": "default",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"ordinary edit must defer (no deny): {proc.stdout!r}"

    def test_kimi_read_allows_no_output(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x.txt"},
            "cwd": "/tmp",
        }
        proc = _run_shim(payload, temp_uacp_root, "kimi")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == ""

    def test_malformed_payload_fails_open(self, temp_uacp_root: Path):
        env = dict(os.environ)
        env["UACP_ROOT"] = str(temp_uacp_root)
        env["PYTHONPATH"] = str(_CORE_SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, str(_SHIM), "--profile", "claude"],
            input="this is not json{{{",
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"fail-open must emit no stdout: {proc.stdout!r}"

    def test_empty_tool_name_denies(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "",
            "tool_input": {},
            "cwd": "/tmp",
            "permission_mode": "default",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    # -- Regression: spoofed MCP server PoC (adversarial review BLOCKER) ------

    def _full_context_input(self, root: Path) -> dict:
        return {
            "target_path": "state/current.yaml",
            "workspace": str(root),
            "uacp_run_id": "uacp-test-001",
            "uacp_phase": "execute",
            "policy_version": "0.1",
            "declared_authority": "plans/test.yaml",
            "declared_side_effects": ["state.uacp"],
        }

    def test_cc_spoofed_mcp_server_denies(self, temp_uacp_root: Path):
        """Core PoC: a spoofed server (mcp__attacker__uacp_state_write) with
        FULL valid UACP context during an active run is DENIED — it does not
        inherit the canonical writer's self-attestation."""
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__attacker__uacp_state_write",
            "tool_input": self._full_context_input(temp_uacp_root),
            "cwd": str(temp_uacp_root),
            "permission_mode": "default",
        }
        proc = _run_shim(
            payload, temp_uacp_root, "claude",
            extra_env={"UACP_RUN_ID": "uacp-test-001", "UACP_PHASE": "execute"},
        )
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", proc.stdout

    def test_cc_canonical_mcp_server_allows(self, temp_uacp_root: Path):
        """Contrast: the canonical mcp__uacp__uacp_state_write with the same
        full context is ALLOWED (exit 0, no deny output)."""
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__uacp__uacp_state_write",
            "tool_input": self._full_context_input(temp_uacp_root),
            "cwd": str(temp_uacp_root),
            "permission_mode": "default",
        }
        proc = _run_shim(
            payload, temp_uacp_root, "claude",
            extra_env={"UACP_RUN_ID": "uacp-test-001", "UACP_PHASE": "execute"},
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"canonical writer must allow (no deny): {proc.stdout!r}"

    # -- Regression: NotebookEdit into .uacp/ (adversarial review HIGH) -------

    def test_cc_notebookedit_uacp_denies(self, temp_uacp_root: Path):
        """A NotebookEdit with notebook_path under .uacp/state/, no active run,
        cwd outside root (the exact bypass condition from the review) -> DENY.
        Without notebook_path extraction the shim would bind workspace to the
        payload cwd (outside root) and the write would slip through."""
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.ipynb")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "NotebookEdit",
            "tool_input": {"notebook_path": target, "new_source": "x"},
            "cwd": "/tmp",  # cwd outside the governed root
            "permission_mode": "default",
        }
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", proc.stdout

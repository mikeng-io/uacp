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

import importlib.util
import io
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


def _load_shim():
    """Import the CLI shim as a module so its narrow predicate can be driven
    in-process (the function-level path), not only as a subprocess."""
    spec = importlib.util.spec_from_file_location("guardian_pretooluse_under_test", _SHIM)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_shim = _load_shim()


def _call_shim_main(payload, *, argv=("--profile", "claude")):
    """Run the shim's main() in-process with ``payload`` on stdin.

    Returns (returncode, stdout_text). stderr is swallowed (warnings only).
    """
    old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = io.StringIO(json.dumps(payload) if not isinstance(payload, str) else payload)
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        rc = _shim.main(list(argv))
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr
    return rc, out


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

    def test_mcp_uacp_state_write_missing_context_denies(self, temp_uacp_root: Path, monkeypatch):
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
        decision = _evaluate(temp_uacp_root, tool_name="mcp__uacp__random", args={})
        assert decision.blocks_execution, decision

    def test_empty_tool_name_denies(self, temp_uacp_root: Path):
        decision = _evaluate(temp_uacp_root, tool_name="", args={})
        assert decision.blocks_execution, decision

    # -- Regression: spoofed MCP server (adversarial review BLOCKER) ----------

    def test_mcp_spoofed_server_full_context_denies(self, temp_uacp_root: Path, monkeypatch):
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

        def _boom(*args, **kwargs):
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
        reason = hso["permissionDecisionReason"]
        # Actionable: names the governed namespace AND a governed writer.
        assert "governed namespace" in reason
        assert "uacp_state_write" in reason or "uacp_entity_write" in reason

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
            "tool_input": {
                "file_path": "/tmp/project/app.py",
                "old_string": "a",
                "new_string": "b",
            },
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

    def test_empty_tool_name_allows(self, temp_uacp_root: Path):
        """Narrow scope: an empty tool name is not a raw host write into the
        governed namespace, so the .uacp/ guard allows it (exit 0, no stdout).
        (It cannot corrupt governed state; the accidental-corruption threat
        model does not cover it.)"""
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
        assert proc.stdout.strip() == "", f"empty tool must allow: {proc.stdout!r}"

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

    def test_cc_spoofed_mcp_server_allows_at_hook(self, temp_uacp_root: Path):
        """Narrowed scope: a spoofed MCP server (mcp__attacker__uacp_state_write)
        is a HOSTILE actor, not accidental corruption — out of the hook's threat
        model. The shim only guards raw HOST file tools (Write/Edit/...) into
        .uacp/; an arbitrary MCP tool is not one, so the shim allows it (exit 0,
        no stdout). Spoofed-server defense remains the MCP server's job and the
        kernel still refuses it on the Hermes path (see the function-level
        test_mcp_spoofed_server_full_context_denies)."""
        _seed_policy(temp_uacp_root)
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "mcp__attacker__uacp_state_write",
            "tool_input": self._full_context_input(temp_uacp_root),
            "cwd": str(temp_uacp_root),
            "permission_mode": "default",
        }
        proc = _run_shim(
            payload,
            temp_uacp_root,
            "claude",
            extra_env={"UACP_RUN_ID": "uacp-test-001", "UACP_PHASE": "execute"},
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"hook does not gate MCP tools: {proc.stdout!r}"

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
            payload,
            temp_uacp_root,
            "claude",
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


# ---------------------------------------------------------------------------
# Narrow-scope shim predicate (the hook-scope-down fix)
#
# The shim guards ONE thing: a raw HOST mutating file tool whose resolved target
# lands inside the governed ``.uacp/`` namespace. Everything else allows. These
# tests drive the shim directly (function-level via main(), plus subprocess where
# the suite already does) — they are the spec for the narrowed behavior.
# ---------------------------------------------------------------------------


def _cc_payload(tool_name: str, tool_input: dict, *, cwd: str = "/tmp") -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
        "cwd": cwd,
        "permission_mode": "default",
    }


class TestShimNarrowPredicateFunctionLevel:
    """Drive the shim's main() in-process. UACP_ROOT is set by temp_uacp_root,
    so the resolved project root is the temp project and its base is temp/.uacp/."""

    def test_write_under_uacp_denies_actionable(self, temp_uacp_root: Path):
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.yaml")
        rc, out = _call_shim_main(_cc_payload("Write", {"file_path": target}))
        assert rc == 0
        decision = json.loads(out)["hookSpecificOutput"]
        assert decision["permissionDecision"] == "deny", out
        reason = decision["permissionDecisionReason"]
        # Names the tool, the governed namespace, AND a concrete governed writer.
        assert "Write" in reason
        assert "governed namespace" in reason
        assert "uacp_state_write" in reason or "uacp_entity_write" in reason

    def test_edit_under_uacp_denies(self, temp_uacp_root: Path):
        target = str(temp_uacp_root / ".uacp" / "plans" / "p.yaml")
        rc, out = _call_shim_main(_cc_payload("Edit", {"file_path": target}))
        assert rc == 0
        assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny", out

    def test_edit_project_file_allows_no_run(self, monkeypatch):
        # Root-independent: an edit outside .uacp/ allows regardless of the root.
        monkeypatch.delenv("UACP_RUN_ID", raising=False)
        monkeypatch.delenv("UACP_PHASE", raising=False)
        rc, out = _call_shim_main(_cc_payload("Edit", {"file_path": "/tmp/project/app.py"}))
        assert rc == 0
        assert out.strip() == "", f"ordinary project edit must allow: {out!r}"

    def test_edit_project_file_allows_run_active(self, monkeypatch):
        # IDENTICAL to the no-run case: the narrow shim is run-state-independent.
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        rc, out = _call_shim_main(_cc_payload("Edit", {"file_path": "/tmp/project/app.py"}))
        assert rc == 0
        assert out.strip() == "", f"ordinary edit must allow even with a run active: {out!r}"

    def test_write_vs_allow_same_tool_differs_only_by_path(self, temp_uacp_root: Path):
        """NON-VACUITY: the same Write tool denies under .uacp/ and allows
        outside it — the target path is the sole discriminator, so the predicate
        cannot be a constant (a constant-deny or constant-allow flips one half)."""
        under = str(temp_uacp_root / ".uacp" / "state" / "x.yaml")
        outside = str(temp_uacp_root / "src" / "x.yaml")
        rc_d, out_d = _call_shim_main(_cc_payload("Write", {"file_path": under}))
        rc_a, out_a = _call_shim_main(_cc_payload("Write", {"file_path": outside}))
        assert rc_d == 0 and rc_a == 0
        assert json.loads(out_d)["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert out_a.strip() == "", f"project-tree write must allow: {out_a!r}"

    def test_bash_touching_state_allows(self, temp_uacp_root: Path):
        """The shim does NOT gate the shell — a Bash command mentioning .uacp/
        state/ still allows (command-string inspection is insufficient; real
        containment is the MCP writers + worktree, not this hook)."""
        target = str(temp_uacp_root / ".uacp" / "state" / "x")
        rc, out = _call_shim_main(_cc_payload("Bash", {"command": f"touch {target}"}))
        assert rc == 0
        assert out.strip() == "", f"bash must allow: {out!r}"

    def test_read_allows(self):
        rc, out = _call_shim_main(_cc_payload("Read", {"file_path": "/tmp/x.txt"}))
        assert rc == 0
        assert out.strip() == ""

    def test_root_level_file_write_allows(self, temp_uacp_root: Path):
        """REGRESSION (this is what bricked the session): a Write to a file at the
        repo ROOT (e.g. .mcp.json) is NOT under .uacp/ -> allow. There is no
        'root-touch' block anymore."""
        target = str(temp_uacp_root / ".mcp.json")
        rc, out = _call_shim_main(_cc_payload("Write", {"file_path": target}))
        assert rc == 0
        assert out.strip() == "", f"root-level file write must allow: {out!r}"

    def test_canonical_mcp_writer_allows(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_RUN_ID", "uacp-test-001")
        monkeypatch.setenv("UACP_PHASE", "execute")
        rc, out = _call_shim_main(
            _cc_payload(
                "mcp__uacp__uacp_state_write",
                {"target_path": "state/current.yaml"},
                cwd=str(temp_uacp_root),
            )
        )
        assert rc == 0
        assert out.strip() == "", f"governed MCP writer must allow: {out!r}"

    def test_malformed_stdin_fails_open(self):
        rc, out = _call_shim_main("this is not json{{{")
        assert rc == 0
        assert out.strip() == ""

    def test_internal_error_fails_open(self, temp_uacp_root: Path, monkeypatch):
        """An unexpected internal error fails OPEN (exit 0, no stdout)."""

        def _raise_boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(_shim, "_resolve_project_root", _raise_boom)
        target = str(temp_uacp_root / ".uacp" / "state" / "x.yaml")
        rc, out = _call_shim_main(_cc_payload("Write", {"file_path": target}))
        assert rc == 0
        assert out.strip() == "", f"internal error must fail open: {out!r}"


class TestShimRootResolution:
    """DEFECT A: resolve the PROJECT being worked in, never ~/.hermes/uacp."""

    def test_resolves_uacp_root_env_first(self, temp_uacp_root: Path, monkeypatch):
        monkeypatch.setenv("UACP_ROOT", str(temp_uacp_root))
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/somewhere/else")
        root = _shim._resolve_project_root({"cwd": "/tmp/other"})
        assert root == temp_uacp_root.resolve()

    def test_falls_back_to_claude_project_dir(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("UACP_ROOT", raising=False)
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        root = _shim._resolve_project_root({"cwd": "/tmp/other"})
        assert root == tmp_path.resolve()
        # And NOT ~/.hermes/uacp.
        assert root != (Path.home() / ".hermes" / "uacp").resolve()

    def test_falls_back_to_payload_cwd(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("UACP_ROOT", raising=False)
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        root = _shim._resolve_project_root({"cwd": str(tmp_path)})
        assert root == tmp_path.resolve()

    def test_wrong_root_regression_governs_the_project_not_hermes(
        self, tmp_path: Path, monkeypatch
    ):
        """DEFECT A end-to-end: UACP_ROOT and HERMES_HOME unset, CLAUDE_PROJECT_DIR
        points at a temp project. A raw Write into THAT project's .uacp/ is denied
        (the hook governs the project), and a write under a sibling ~/.hermes-style
        path is NOT governed (allowed) because it is not this project's root."""
        monkeypatch.delenv("UACP_ROOT", raising=False)
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.delenv("UACP_RUN_ID", raising=False)
        monkeypatch.delenv("UACP_PHASE", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

        in_project = str(tmp_path / ".uacp" / "state" / "x.yaml")
        rc_d, out_d = _call_shim_main(_cc_payload("Write", {"file_path": in_project}, cwd="/tmp"))
        assert rc_d == 0
        assert json.loads(out_d)["hookSpecificOutput"]["permissionDecision"] == "deny", out_d

        # A path under a DIFFERENT (hermes-like) tree is outside this project's
        # base -> allowed. Proves the hook governs CLAUDE_PROJECT_DIR, not hermes.
        elsewhere = str(tmp_path.parent / "hermes-home" / ".uacp" / "state" / "x.yaml")
        rc_a, out_a = _call_shim_main(_cc_payload("Write", {"file_path": elsewhere}, cwd="/tmp"))
        assert rc_a == 0
        assert out_a.strip() == "", f"a write outside the project base must allow: {out_a!r}"


class TestShimNarrowSubprocess:
    """Mirror the key cases through the real CLI subprocess shim."""

    def test_root_level_file_write_allows(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".mcp.json")
        payload = _cc_payload(
            "Write", {"file_path": target, "content": "{}"}, cwd=str(temp_uacp_root)
        )
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"root-level write must allow: {proc.stdout!r}"

    def test_bash_touching_state_allows(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "x")
        payload = _cc_payload("Bash", {"command": f"touch {target}"}, cwd=str(temp_uacp_root))
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "", f"bash must allow: {proc.stdout!r}"

    def test_write_under_uacp_denies(self, temp_uacp_root: Path):
        _seed_policy(temp_uacp_root)
        target = str(temp_uacp_root / ".uacp" / "state" / "sneak.yaml")
        payload = _cc_payload(
            "Write", {"file_path": target, "content": "x"}, cwd=str(temp_uacp_root)
        )
        proc = _run_shim(payload, temp_uacp_root, "claude")
        assert proc.returncode == 0, proc.stderr
        reason = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        assert "governed namespace" in reason
        assert "uacp_state_write" in reason or "uacp_entity_write" in reason

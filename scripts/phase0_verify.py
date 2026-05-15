#!/usr/bin/env python3
"""Phase 0 behavioural verification for the UACP Guardian patch plan.

Exercises three things in a temporary UACP root:

1. Bug 0.1 fix — the governed writer `uacp_doc_write` succeeds for a
   UACP-bound event, where previously it was blocked because
   `filesystem_guard_verified` was never set.

2. Bug 0.1 negative — the unmanaged `terminal` tool (classified as
   `exec.shell`) is still blocked when UACP-bound without an
   `attestation_id`.

3. Bug 0.2 fix — `policy.mode` is honoured.  In observe mode, the same
   UACP-bound `terminal` event that blocks in enforce mode is downgraded
   to `allow_with_audit`.  Missing-context defects continue to block in
   both modes (non-waivable).

Run from anywhere; the script is self-contained.  Exits 0 on full pass,
non-zero on any failure with a JSON report.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def _import_plugin():
    here = Path(__file__).resolve().parent.parent
    plugins_root = here / "runtime-adapters" / "hermes" / "plugins"
    sys.path.insert(0, str(plugins_root))
    import uacp_guardian as plugin
    from uacp_guardian.kernel import Guardian, GuardianPolicy, make_event
    return plugin, Guardian, GuardianPolicy, make_event


def _prepare_root(tmp: Path) -> None:
    here = Path(__file__).resolve().parent.parent
    for sub in ("config", "docs", "state/runs"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(here / "config/guardian-policy.yaml", tmp / "config/guardian-policy.yaml")
    shutil.copy2(here / "config/phase-transitions.yaml", tmp / "config/phase-transitions.yaml")


def _set_policy_mode(tmp: Path, mode: str) -> None:
    import yaml
    path = tmp / "config/guardian-policy.yaml"
    data = yaml.safe_load(path.read_text())
    data["mode"] = mode
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _reload_policy(plugin) -> None:
    plugin._POLICY = None
    plugin._POLICY_ERROR = ""


def _common_args(tmp: Path) -> dict:
    return {
        "workspace": str(tmp),
        "uacp_run_id": "phase0-verify",
        "uacp_phase": "execute",
        "policy_version": "0.1",
        "declared_side_effects": "phase0 verification writes",
        "authority_artifact": "verification/phase0-verify.yaml",
    }


def main() -> int:
    plugin, Guardian, GuardianPolicy, make_event = _import_plugin()
    report: dict = {"checks": []}

    saved_env = {k: os.environ.get(k) for k in ("UACP_ROOT", "UACP_GUARDIAN_MODE")}

    try:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            _prepare_root(tmp)
            os.environ["UACP_ROOT"] = str(tmp)
            os.environ.pop("UACP_GUARDIAN_MODE", None)

            # ---- Check 1: governed doc write succeeds when UACP-bound (Bug 0.1) ----
            _reload_policy(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="uacp_doc_write",
                args={**_common_args(tmp), "target_path": "docs/probe.md", "content": "# x\n"},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "uacp_doc_write",
                    {**_common_args(tmp), "target_path": "docs/probe.md"},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "doc_write_not_blocked_when_uacp_bound",
                "status": "pass" if not decision.blocks_execution else "fail",
                "decision": decision.decision,
                "category": decision.category,
                "reason": decision.reason,
            })

            # ---- Check 2: terminal still blocks when UACP-bound without attestation ----
            _reload_policy(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="terminal",
                args={**_common_args(tmp), "command": "echo hi"},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "terminal",
                    {**_common_args(tmp), "command": "echo hi"},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "terminal_blocked_without_attestation_in_enforce",
                "status": "pass" if decision.blocks_execution else "fail",
                "decision": decision.decision,
                "category": decision.category,
                "reason": decision.reason,
            })

            # ---- Check 3a: observe mode does NOT waive containment (non-waivable) ----
            _set_policy_mode(tmp, "observe")
            _reload_policy(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="terminal",
                args={**_common_args(tmp), "command": "echo hi"},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "terminal",
                    {**_common_args(tmp), "command": "echo hi"},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "observe_mode_preserves_containment_invariant",
                "status": "pass" if decision.blocks_execution else "fail",
                "decision": decision.decision,
                "policy_mode": policy.mode,
                "reason": decision.reason,
            })

            # ---- Check 3b: observe mode DOES downgrade policy-default block when containment is satisfied ----
            # Inject a synthetic valid attestation so containment is satisfied;
            # this exercises the policy-default observe downgrade path.
            import time as _time
            synthetic_id = "synthetic-phase0-attest"
            plugin._CONTAINED_SHELL_ATTESTATIONS[synthetic_id] = {
                "attestation_id": synthetic_id,
                "expires_at": _time.time() + 60,
                "policy_version": str(policy.version),
                "containment_verified": True,
            }
            event = make_event(
                tool_name="terminal",
                args={**_common_args(tmp), "command": "echo hi", "attestation_id": synthetic_id},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "terminal",
                    {**_common_args(tmp), "command": "echo hi", "attestation_id": synthetic_id},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "observe_mode_downgrades_policy_default_block",
                "status": "pass" if (not decision.blocks_execution and "observe mode" in decision.reason.lower()) else "fail",
                "decision": decision.decision,
                "policy_mode": policy.mode,
                "reason": decision.reason,
            })

            # ---- Check 3b: missing-context block is non-waivable in observe mode ----
            event = make_event(
                tool_name="uacp_doc_write",
                args={"target_path": "docs/x.md", "uacp_run_id": "phase0-verify"},  # missing other context
                filesystem_guard_verified=True,
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "missing_context_blocks_even_in_observe",
                "status": "pass" if decision.blocks_execution else "fail",
                "decision": decision.decision,
                "policy_mode": policy.mode,
                "reason": decision.reason,
            })

            # ---- Check 4: enforce mode still blocks (restore policy) ----
            _set_policy_mode(tmp, "enforce")
            _reload_policy(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="terminal",
                args={**_common_args(tmp), "command": "echo hi"},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "terminal",
                    {**_common_args(tmp), "command": "echo hi"},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "enforce_mode_keeps_terminal_block",
                "status": "pass" if decision.blocks_execution else "fail",
                "decision": decision.decision,
                "policy_mode": policy.mode,
                "reason": decision.reason,
            })

            # ---- Check 5a: uacp_config_write reaches new allowed-tools branch ----
            _set_policy_mode(tmp, "enforce")
            _reload_policy(plugin)
            policy = plugin._policy()
            event = make_event(
                tool_name="uacp_config_write",
                args={**_common_args(tmp), "target_path": "config/probe.yaml", "content": "a: 1\n"},
                filesystem_guard_verified=plugin._filesystem_guard_verified(
                    "uacp_config_write",
                    {**_common_args(tmp), "target_path": "config/probe.yaml"},
                ),
            )
            decision = Guardian(policy).evaluate(event)
            report["checks"].append({
                "name": "config_write_authorized_via_governed_tool_branch",
                "status": "pass" if (not decision.blocks_execution and decision.category == "config.uacp") else "fail",
                "decision": decision.decision,
                "category": decision.category,
                "reason": decision.reason,
            })

            # ---- Check 5b: 4 governed tools that were previously runtime.extension ----
            # SK-001 remediation: uacp_artifact_write, uacp_sandbox_check,
            # uacp_contained_shell, uacp_heartgate_check now classified.
            governed_tool_cases = [
                ("uacp_artifact_write", "artifact.uacp", {"target_path": "plans/probe.yaml", "content": "a: 1\n"}),
                ("uacp_sandbox_check",  "evidence.containment", {"execution_workspace": str(tmp.parent), "tool_surface": "exec.shell"}),
                ("uacp_contained_shell","exec.shell.contained", {"command": "echo hi", "workspace": str(tmp.parent)}),
                ("uacp_heartgate_check","lifecycle.transition", {"transition_path": "verification/probe.yaml"}),
            ]
            for tool_name, expected_category, tool_args in governed_tool_cases:
                event = make_event(
                    tool_name=tool_name,
                    args={**_common_args(tmp), **tool_args},
                    filesystem_guard_verified=plugin._filesystem_guard_verified(
                        tool_name,
                        {**_common_args(tmp), **tool_args},
                    ),
                )
                decision = Guardian(policy).evaluate(event)
                report["checks"].append({
                    "name": f"governed_tool_classified_and_allowed:{tool_name}",
                    "status": "pass" if (not decision.blocks_execution and decision.category == expected_category) else "fail",
                    "decision": decision.decision,
                    "category": decision.category,
                    "expected_category": expected_category,
                    "reason": decision.reason,
                })

            # ---- Check 6: _filesystem_guard_verified semantics ----
            verifier = plugin._filesystem_guard_verified
            report["checks"].append({
                "name": "self_attesting_tools_return_true",
                "status": "pass" if all(
                    verifier(t, {}) for t in ("uacp_doc_write", "uacp_config_write", "uacp_state_write",
                                              "uacp_artifact_write", "uacp_sandbox_check",
                                              "uacp_heartgate_check", "uacp_contained_shell")
                ) else "fail",
            })
            report["checks"].append({
                "name": "terminal_without_attestation_returns_false",
                "status": "pass" if verifier("terminal", {}) is False else "fail",
            })
            report["checks"].append({
                "name": "terminal_with_invalid_attestation_returns_false",
                "status": "pass" if verifier("terminal", {"attestation_id": "nonexistent"}) is False else "fail",
            })

    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    all_pass = all(c.get("status") == "pass" for c in report["checks"])
    report["status"] = "pass" if all_pass else "fail"
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

# Kimi + Codex Agent Council audit loop for UACP runtime-gate remediation

Use this reference when Mike asks for Kimi Code and Codex to perform full-perspective UACP reviews, especially after Heartgate/Guardian/runtime-gate patches.

## Trigger

- External audit of UACP lifecycle gates, Heartgate, Guardian, validator, or phase skills.
- User asks for both Kimi and Codex, or asks that the runtime use Agent Council.
- Prior auditor found docs/config/offline-validator coverage but runtime enforcement drift.

## Durable lessons

1. **Use command-level timeouts and background processes.** Long external audits should not block the operator channel. Use `timeout 45m ...` plus managed background execution and read reports after completion.
2. **Do not force Kimi `--model kimi` for coding audits.** In this session that routed to a membership-benefit check. Prefer the coding model route:

```bash
kimi --work-dir /home/norty/.hermes/uacp \
  --print --final-message-only --afk \
  --model kimi-code/kimi-for-coding \
  -p "$(cat /tmp/uacp-audit-prompt.txt)"
```

A no-model Kimi invocation can also work for a quick readiness probe:

```bash
kimi --work-dir /home/norty/.hermes/uacp --print --final-message-only --afk -p "Say READY only"
```

3. **Require Agent Council inside each external runtime.** The prompt should explicitly require at least these roles:
   - Lifecycle governance reviewer
   - Validator/runtime enforcement auditor
   - Heartgate/Guardian security reviewer
   - Adversarial false-pass reviewer
   - Operator-handoff / semantic-recovery reviewer

4. **Audit the patch just made, not stale HEAD.** Include current `HEAD`, commit SHA, and the findings being rechecked.
5. **Treat read-only prompts as advisory, not guaranteed.** Codex created untracked synthetic test files despite a read-only instruction. Always check `git status` after external audits and remove audit contamination before patching.
6. **Combine Kimi + Codex before remediation.** If both are running, wait for both before patching unless one times out or blocks; otherwise the second report may reveal a better systemic fix.

## Prompt skeleton

```text
You are [Kimi Code|Codex] acting as an independent external auditor for UACP lifecycle governance changes. READ-ONLY AUDIT ONLY. Do not modify files, do not commit, do not push, do not write artifacts.

MANDATORY INTERNAL METHOD: Use an Agent Council inside your runtime before giving the final answer. Simulate/instantiate at least these roles:
1. Lifecycle governance reviewer
2. Validator/runtime enforcement auditor
3. Heartgate/Guardian security reviewer
4. Adversarial false-pass reviewer
5. Operator-handoff / semantic-recovery reviewer

Repo: /home/norty/.hermes/uacp
Current HEAD: <sha>
Audit scope: verify whether <sha> closes findings from <prior sha/report>.

Required surfaces:
- runtime-adapters/hermes/plugins/uacp_guardian/kernel.py
- scripts/validate_uacp_artifacts.py
- verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
- verification/fixtures/heartgate-runtime/*.yaml
- docs/reference/lifecycle-trace-table.md
- active skill exports when relevant

Output:
- VERDICT: PASS / CONCERNS / FAIL
- Agent Council role verdicts
- Findings by BLOCKER/HIGH/MEDIUM/LOW with evidence path+line/function, required fix, regression fixture
- Explicitly state whether it is safe to proceed to dependent governed work.
```

## Remediation expectations after findings

If Kimi/Codex find runtime-depth gaps:

- Prefer sharing semantics with `scripts/validate_uacp_artifacts.py` instead of duplicating shallow Heartgate checks.
- Add a self-contained Heartgate runtime smoke harness that creates temporary gate-ledger records and cleans them afterward.
- Add positive and negative runtime fixtures for the exact false-pass class.
- Update docs/reference lifecycle trace if artifact contracts changed.
- Patch active skill-store exports separately when they are outside git; report that as local runtime sync, not a committed repo change.
- Run focused internal council after remediation; if CONCERNS remain, patch and rerun one focused follow-up before commit.

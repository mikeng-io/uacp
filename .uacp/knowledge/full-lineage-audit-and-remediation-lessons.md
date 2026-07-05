---
type: pattern
id: full-lineage-audit-and-remediation-lessons
title: Full-Lineage Audit and Remediation Lessons
description: Rules for auditing the full change lineage across multiple commits or phases rather than only the latest commit
tags: [audit, lineage, remediation, governance]
timestamp: 2026-06-17
---

# Full-Lineage Audit and Remediation Lessons

Reference for UACP governance work spanning multiple commits or lifecycle phases — when Mike asks for coherence, consistency, or full review rather than a point fix.

---

## Core rule: audit the full lineage, not only the latest commit

Do not scope external audits to only the latest remediation commit unless Mike explicitly requests that. For UACP governance and lifecycle changes, the correct audit unit is the **full lineage of related changes** and the end-to-end lifecycle coherence across PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE.

A narrow prompt like "verify whether commit X closes findings from commit Y" is useful as a follow-up check, but it is not a substitute for a full lifecycle audit.

---

## Trigger signals

Use full-lineage audit mode when:

- Mike says the audit must cover the entire lifecycle or change series, not just one commit.
- Mike asks Kimi/Codex to use their own Agent Councils, including devil's advocate roles.
- A patch touches any combination of docs, config, validator, runtime Guardian/Heartgate, active skill exports, state/current, fixtures, or semantic packages.
- Mike warns about documentation "fracture" or "scatter."

---

## Full-lineage audit prompt shape

Do not ask only whether the latest commit closed the latest finding. Ask whether the whole lifecycle coheres end-to-end.

Require the external runtime to audit at least these 10 surfaces:

1. PROPOSE semantic package gates.
2. PLAN package gates and Phase Intent Verification contract.
3. EXECUTE PIV evidence checkpoint and semantic execution package.
4. VERIFY truth gate, PIV assessment, self-approval guard, and resolve readiness.
5. RESOLVE closure gate, carry-forward of residual risks/deferred items, and state disposition.
6. Guardian protected path binding, including shell command text, workspace, cwd/workdir, and `$UACP_ROOT`.
7. Heartgate runtime parity with offline validator semantics.
8. Active Hermes skill exports and reference paths.
9. State source-of-truth (`state/current.yaml` vs `config/state.yaml`).
10. Existing real artifacts that could become stale or contradict the new contract.

Required prompt elements:

- Read-only audit.
- Repository ground truth over assistant summaries.
- Explicit internal Agent Council / multi-role reasoning.
- Devil's advocate / false-pass role.
- Full change-lineage scope, listing relevant commits when known.
- Surfaces across docs, config, validator, runtime, fixtures, active skill exports, state, and real artifacts.
- Explicit closure matrix by lifecycle phase and runtime/skill surfaces.
- Whether downstream governed work may safely depend on the result.

---

## Council roles

Both source documents listed 7 roles with no conflict — this is the single authoritative list:

1. Lifecycle governance reviewer.
2. Validator/runtime enforcement auditor.
3. Heartgate/Guardian security reviewer.
4. Adversarial devil's advocate / false-pass reviewer.
5. Operator-handoff / semantic-recovery reviewer.
6. Lifecycle consistency historian.
7. Dependency readiness reviewer.

---

## Systemic remediation classes

When audits find coherence gaps, patch the systemic surfaces — not one fixture. The following classes proved important:

- **Guardian path-source binding**: bind UACP paths from direct args, `workspace`, `cwd`, `workdir`, command strings, `$HOME`, and `$UACP_ROOT`. For protected shell checks, assert `Guardian.evaluate()` blocks, not merely that `is_uacp_bound()` returns true.
- **Accepted-exception artifact_path + cluster_id binding**: bind accepted exceptions by `(artifact_path, cluster_id)` and require run-bound evidence (`accepted_by`, owner, rationale, next-phase acceptance, and an existing run-bound evidence path). Do not allow accepted exceptions to cite arbitrary existing `verification/` or `.outputs/` files from another run.
- **PIV pass-evidence requirement**: PIV pass evidence must reference existing, run-bound artifacts. If a plan PIV exists, VERIFY must provide the PIV assessment.
- **VERIFY-vs-RESOLVE distinction**: VERIFY is truth; RESOLVE is closure. RESOLVE must deep-validate VERIFY readiness and carry forward residual risks/deferred items from readiness and resolve package — not drop them.
- **Unknown-kind blocking**: block unknown `uacp.*` artifact kinds rather than silently passing them.
- **State-pointer precision**: `state/current.yaml` pointers must be exact run-token/prefix bound, not substring-bound. Reconcile `state/current.yaml` with `config/state.yaml`; state pointers must be run-bound.
- **Smoke-harness isolation**: runtime smoke harnesses should use a temporary copied UACP root when they need fixture ledgers, proving they leave no repo state residue.
- **Active skill-export link checking**: check active skill exports separately from repo docs; repo docs can be correct while live `~/.hermes/skills/...` or `../references/...` paths are stale.

Also: offline `uacp.phase_transition` validation should invoke the same linked adaptive artifact checks that Heartgate relies on; otherwise agents can claim "validator passed" for a transition Heartgate would block.

---

## Remediation ordering

When external auditors return findings, patch root causes in this order across all authoritative surfaces:

1. Runtime enforcement — Guardian/Heartgate behavior.
2. Offline validator — same false-pass class must block offline too.
3. Config/schema — canonical contract must match runtime requirements.
4. Fixtures — add positive and negative regression cases.
5. Runtime smoke harness — assert actual `evaluate()` decisions where relevant, not only helper predicates.
6. Active skill exports — fix live `~/.hermes/skills/...` references separately from repo docs.
7. State/source-of-truth — reconcile current state when it contradicts doctrine.
8. Docs/trace tables — remove stale links and terminology drift.

Then run internal adversarial follow-up. If it returns CONCERNS/FAIL, patch again and rerun until PASS.

---

## Documentation anti-fracture pattern

When Mike asks for human-readable documentation after a large UACP hardening pass, create a modular guide package rather than a single mega-doc or random edits.

Recommended 5-file shape:

```text
docs/guides/<topic>/
  00-index.md                          # conductor: reading order, authority map, anti-fracture rule
  01-human-overview.md                 # readable explanation for humans
  02-agent-operating-guide.md          # future-agent workflow and pitfalls
  03-artifact-and-gate-map.md          # where meaning/evidence/enforcement lives
  04-audit-and-remediation-history.md
```

Also create or update `docs/guides/INDEX.md`, then link the package from `docs/INDEX.md` and `README.md`. The guide must explain and route; it must not become a competing authority layer.

---

## Canonical ownership pointers

| Surface | Canonical owner |
|---------|----------------|
| Phase/gate policy | `config/phase-transitions.yaml` |
| Offline validation | `scripts/validate_uacp_artifacts.py` |
| Guardian/Heartgate runtime | `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` |
| Transition evidence map | `docs/reference/lifecycle-trace-table.md` |
| Accepted historical decisions | ADRs |

---

## Verification bundle

A robust pass should include at least:

```bash
python -m py_compile \
  scripts/validate_uacp_artifacts.py \
  runtime-adapters/hermes/plugins/uacp_guardian/kernel.py \
  verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py \
  scripts/check_active_uacp_skill_links.py
python scripts/validate_uacp_artifacts.py --root .
python verification/fixtures/heartgate-runtime/run_heartgate_runtime_smoke.py
python scripts/check_active_uacp_skill_links.py
# negative sweep across adaptive execute/verify/resolve and heartgate fail fixtures
```

## Git provenance / authority

- Verify the local git identity before committing (a remediation run committed under the wrong identity pollutes provenance).
- **Rewriting already-pushed history is a separate authority decision.** Do not rewrite / force-push pushed history without explicit operator approval — treat it as its own authorized action, not part of the remediation.

Finish with a concise operator report: commit SHA, pushed/clean state, findings closed, validation evidence, and whether external follow-up remains pending.

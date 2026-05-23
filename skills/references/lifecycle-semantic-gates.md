# Lifecycle hardening pattern: semantic gates across all UACP phases

Use this reference when hardening UACP lifecycle phases, validator gates, or phase skills.

## Durable lesson from the semantic package/PIV/VERIFY/RESOLVE hardening run

Do not claim a lifecycle is hardened just because upstream phases were fixed. In this session the work initially covered PROPOSE, PLAN, and EXECUTE, then Mike correctly caught that VERIFY was still the most important unresolved truth gate, and later that RESOLVE was still only protected by VERIFY readiness rather than its own closure gate.

Correct pattern:

1. Identify the phase-local responsibility.
   - PROPOSE: semantic authority/scope/intent package.
   - PLAN: semantic work design plus Phase Intent Verification contract.
   - EXECUTE: evidence/checkpoints against PLAN's PIV contract.
   - VERIFY: truth judgment, facts vs assumptions, PIV satisfaction, readiness for RESOLVE.
   - RESOLVE: closure, residual-risk preservation, lesson/memory/skill/doc disposition, operator handoff.
2. For a missing/weak phase, run the loop:
   - retrieval-led gap audit
   - pre-design council for semantics/constraints
   - docs/config/validator/fixtures/skill implementation
   - deterministic validation including expected-fail fixtures
   - post-implementation council/adversarial audit
   - patch findings
   - focused follow-up until PASS or accepted residual risk
   - commit/push only after clean validation
3. Add both positive fixtures and must-block negative fixtures. Negative fixture coverage matters as much as pass fixtures.
4. Treat Agent Council differently by phase:
   - pre-design council is valuable when defining truth/closure semantics, especially VERIFY and RESOLVE.
   - post-implementation council is mandatory for governance/validator changes.
5. Keep external Kimi/Codex audits as a final independent review after the entire phase chain is complete, not while a known phase remains under-modeled.

## PIV naming correction

PIV in UACP means **Phase Intent Verification**, not Phase Implementation Verification. EXECUTE may produce code, docs, config, generated artifacts, council dispatch, runtime probes, state updates, or handoffs. Use neutral vocabulary:

- `work_units`, not `implementation_units`
- `produced_outputs`, not `implemented_outputs`
- phase intent/evidence obligations, not code-only tests

## VERIFY-specific pitfall

VERIFY is not just “tests passed.” It must separate:

- verified facts
- assumptions
- deferred items
- warnings
- blockers
- PIV assessment
- resolve readiness

Block if facts lack source evidence, assumptions/deferred items lack owner/accepted_by/next obligation, open blockers remain, Heartgate coherence is missing when required, or VERIFY self-remediates material findings without independent re-verification.

## RESOLVE-specific pitfall

RESOLVE is not a second VERIFY. It consumes VERIFY readiness and closes the run. It must preserve residual risks/deferred items, classify lessons (`memory`, `skill`, `docs`, `knowledge`, `no_action`), record state/memory disposition, and produce a decision-grade operator handoff. Block if closure drops VERIFY risks, uses stale/unrelated readiness, lacks final decision, or emits raw file inventory as handoff.

## Reporting discipline

When reporting completion of UACP lifecycle hardening, explicitly state which phases are covered and which remain. Do not say “done” for the lifecycle if VERIFY or RESOLVE still lacks a first-class gate.
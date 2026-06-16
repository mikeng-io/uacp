# Lifecycle Semantic Gates

Authoritative reference for hardening UACP lifecycle phases, validating gate completeness, and auditing whether a phase is genuinely done — not just nominally closed.

---

## Core corrections

- **PIV means Phase Intent Verification**, not Phase Implementation Verification. EXECUTE may produce code, docs, config, generated artifacts, council dispatch, runtime probes, state updates, or handoffs. Use neutral vocabulary: `work_units`, `produced_outputs`, `work_narrative` — not implementation-only terms.
- Do not claim lifecycle hardening is complete after covering only PROPOSE/PLAN/EXECUTE. VERIFY and RESOLVE are first-class governance phases with their own gates.
- VERIFY is the truth boundary before RESOLVE. It must separate verified facts from assumptions/deferred items, assess PIV satisfaction, prevent self-approval, and produce run-bound resolve readiness.
- RESOLVE is closure, not a second VERIFY. It consumes VERIFY readiness and proves final closure, residual-risk preservation, lesson/memory/skill/doc dispositions, and operator handoff.

---

## Gate expectations by phase

### PROPOSE / PLAN
- Semantic package directory present and `00-index.md` non-empty.
- Selected modules non-empty.
- Artifacts under canonical package directory.
- PLAN additionally: Phase Intent Verification contract authored.

### EXECUTE
- PLAN-authored PIV contract present; checkpoints bind to work units and evidence obligations.
- Semantic execution package produced.
- Drift/deviation disposition recorded.

### VERIFY
- Verification package produced.
- PIV assessment included when a PIV contract exists.
- Verified facts carry source evidence.
- Assumptions and deferred items have owner, accepted_by, and next obligation.
- Self-approval guard active (VERIFY must not self-remediate material findings without independent re-verification).
- Heartgate coherence checked when required.
- Run-bound resolve readiness produced.

### RESOLVE
- Closure package under `.outputs/{run_id}/`.
- Final decision recorded.
- Residual risks and deferred items carried forward (not dropped from VERIFY readiness).
- Lesson disposition classified: `memory | skill | docs | knowledge | no_action`.
- State and memory disposition recorded.
- Concise, decision-grade operator handoff produced (not a raw file inventory).
- Artifact-bound closed scope.

---

## Phase-by-phase responsibility list

| Phase   | Primary responsibility |
|---------|------------------------|
| PROPOSE | Semantic authority, scope, and intent package |
| PLAN    | Semantic work design plus PIV contract |
| EXECUTE | Evidence and checkpoints against PLAN's PIV contract |
| VERIFY  | Truth judgment: facts vs assumptions, PIV satisfaction, readiness for RESOLVE |
| RESOLVE | Closure, residual-risk preservation, lesson/memory/skill/doc disposition, operator handoff |

---

## VERIFY-specific pitfalls

VERIFY is not just "tests passed." It must separate:

- verified facts (with source evidence)
- assumptions (with owner and accepted_by)
- deferred items (with owner and next obligation)
- warnings
- blockers
- PIV assessment
- resolve readiness

Block if: facts lack source evidence; assumptions/deferred items lack owner/accepted_by/next obligation; open blockers remain; Heartgate coherence is missing when required; or VERIFY self-remediates material findings without independent re-verification.

---

## RESOLVE-specific pitfall

RESOLVE is not a second VERIFY. It consumes VERIFY readiness and closes the run. Block if:
- Closure drops VERIFY risks or deferred items.
- Readiness used is stale or belongs to an unrelated run.
- Final decision is absent.
- Operator handoff is a raw file inventory rather than a decision-grade summary.

---

## Fixture discipline

Each gate should include positive fixtures and expected-fail negatives covering:

- Stale or unbound artifacts.
- Missing package directory or `00-index.md`.
- Dropped risks or deferred items.
- Invalid enums.
- Missing owners or acceptance fields.
- Fake readiness (RESOLVE consuming VERIFY readiness that was never produced).
- Raw operator handoff (file list passed as summary).
- Self-approval bypasses.

Negative fixture coverage matters as much as pass fixtures.

---

## Preferred workflow for governance-core phase hardening

For high-impact phases such as VERIFY and RESOLVE, do not implement first. Use the following sequence:

1. Retrieval-led gap audit grounded in repo files.
2. Pre-design council to define constraints and must-block cases.
3. Implement docs, config, validator, fixtures, and skills together.
4. Run deterministic validation including expected-fail fixtures.
5. Post-implementation council and adversarial audit — **mandatory for governance/validator changes** (not optional for high-risk work).
6. Patch findings.
7. Focused follow-up council until PASS or accepted residual risk is explicit.
8. Commit and push only after validation passes and material audit findings are closed.

For clearer, lower-risk gaps (such as EXECUTE PIV binding), implementation before council can be acceptable. VERIFY and RESOLVE always deserve pre-design council.

When a known phase remains under-modeled, keep external Kimi/Codex audits as a final independent review — not an early substitute for completing the phase model.

---

## Hardening design principles

### Multi-surface patch principle

Do not create doctrine-only patches for UACP lifecycle behavior. A real lifecycle patch should usually touch:

- Architecture/reference doc updates.
- Config gate updates.
- Validator/schema updates.
- Positive and negative fixtures.
- Lifecycle skill updates.
- Council/audit artifact when risk warrants it.

### Granularity principle

Keep artifacts modular and class-level:

- ADR for the concept.
- Config for selection and gates.
- Validator functions for machine checks.
- Fixture directory for regression protection.
- `references/` files in skills for session-specific learnings.

### Next-phase-boundary pitfall

A lifecycle patch is incomplete if it only improves the current phase's prose. The next phase boundary must be checked too: EXECUTE needed VERIFY consumption; VERIFY needed RESOLVE readiness. Always verify the handoff into the next phase, not just the current phase's internal gates.

---

## External audit pattern

When dispatching Kimi or Codex for a full audit:

- Run read-only with a command-level timeout (for example `timeout 45m ...`).
- Track the background process.
- If a provider-specific model is rejected, retry with the default supported model — do not treat the runtime as unavailable.
- Do not persist environment-specific auth failures as doctrine; capture only the retry/fallback pattern.

---

## Reporting discipline

When reporting completion of UACP lifecycle hardening, explicitly state which phases are covered and which remain. Do not say "done" for the lifecycle if VERIFY or RESOLVE still lacks a first-class gate.

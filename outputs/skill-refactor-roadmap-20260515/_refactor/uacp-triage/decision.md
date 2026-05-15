# Phase 1 — uacp-triage Decision

Status: Draft decision only. No implementation authorized until end-of-Decision Agent Council returns PASS/no concerns.
Start gate: PASS/no concerns.
Explore and Determine: complete.

## Decision

Refactor `uacp-triage/SKILL.md` into a concise phase conductor while preserving the essential UACP triage behavior.

This is a one-file implementation. No new support files are created in this phase.

## Why

Current triage skill is 158 lines / 8,956 bytes and contains:

- duplicate `## Rules` heading
- repeated TRIAGE-before-PROPOSE doctrine
- overlapping artifact schema blocks
- inlined Agent Council follow-through body despite an existing shared primitive
- mixed real-UACP-runtime tooling language and self-repair lane concerns

The refactor should reduce duplication and clarify ownership without weakening TRIAGE discipline.

## Universal UACP boundary

TRIAGE must remain generic/adaptive. It may score risk/granularity and read routing config, but it must not import Trustless-specific fixed gates, fixed domains, fixed reviewer lists, or fixed verification sequences.

## Triage owns

- admission/routing decision
- scope and granularity estimate
- routing outcome selection
- triage-local council trigger
- immediate human-authority flag
- compact triage artifact contract
- transition obligations for PROPOSE without designing PROPOSE

## Triage does not own

- proposal design
- final authority or side-effect review
- implementation planning
- state mutation authority
- Heartgate implementation mechanics
- full Agent Council follow-through SOP
- MEMEX/BES retrieval in this pass
- Trustless fixed taxonomy

## Target implementation shape

Target: under 120 lines.

Allowed sections:

1. Frontmatter
2. Title / purpose
3. When to use
4. Read when needed
5. Rules / phase boundary
6. Execution checklist
7. Council and human-involvement trigger
8. Output contract
9. Shared follow-through reference
10. Self-repair caveat

## Draft target content outline

```markdown
---
name: uacp-triage
description: Calibrate UACP admission, scope, granularity, routing depth, and whether council/human authority is needed before proposal.
---

# UACP Triage

Triage is UACP admission control. It decides whether a request should enter UACP, at what governance depth, and what obligations the next phase inherits. It does not design the proposal.

## When to use

Use for unclear scope, governance-depth decisions, granularity scoring, phase admission, or deciding whether direct/lightweight/standard/full UACP handling is appropriate.

## Read when needed

- `UACP_ROOT/config/gate-selection.yaml` — scoring/routing factors
- `UACP_ROOT/config/review-routing.yaml` — council/review routing hints
- `UACP_ROOT/docs/orchestration-model.md` — phase and council boundaries
- `UACP_ROOT/config/phase-transitions.yaml` — transition evidence requirements

## Rules

- TRIAGE is not PROPOSE.
- Do not compress TRIAGE into PROPOSE for governance-core or high-granularity work.
- Do not assume every request needs full lifecycle governance.
- Keep scoring adaptive/config-driven, not Trustless-specific.
- Treat the output contract below as the default minimum; extend it from canonical config/schema if such config exists in the active UACP environment.
- Record routing decision, score factors, council trigger, and human-involvement decision.
- Keep output compact and machine-readable.

## Execution checklist

1. Summarize the request and authority source.
2. Score visible factors: impact, reversibility, domain count, runtime count, verification difficulty.
3. Estimate phase-local and composite granularity.
4. Select routing outcome: `direct`, `lightweight`, `standard_uacp`, `full_governance`, or `block_or_clarify`.
5. Decide whether TRIAGE-local Agent Council is required.
6. Decide whether immediate human authority is required.
7. Record a compact triage artifact or update the active refactor artifact.
8. Report routing outcome and next phase obligations.

## Council and human-involvement trigger

Strongly consider TRIAGE-local council when granularity is high, authority is unclear, phase compression risk exists, or the request touches lifecycle semantics, Agent Council behavior, Guardian/Heartgate boundaries, protected state, artifact schemas, runtime enforcement, or phase-transition rules.

TRIAGE council reviews admission, routing, scope, granularity, and whether UACP applies. PROPOSE council reviews authority, side effects, proposal quality, artifact contract, and viability.

Human involvement is required for unclear authority, irreversible/external side effects, unresolved critical risk, or Guardian/Heartgate uncertainty.

## Output contract

The YAML below is the default minimum artifact contract, not a closed universal schema. Additional fields may be added when canonical UACP config/schema requires them.

```yaml
kind: uacp.triage
triage_id: "{project}-{YYYYMMDD-HHMMSS}-001"
request_summary: "..."
authority:
  status: pass | warn | block
  source: "..."
factor_scores:
  impact: 1-10
  reversibility: 1-10
  domain_count: 1-10
  runtime_count: 1-10
  verification_difficulty: 1-10
phase_local_granularity:
  phase: triage
  entry_estimate: 1-10
  downstream_projection: {}
composite_granularity: 1-10
routing_outcome: direct | lightweight | standard_uacp | full_governance | block_or_clarify
council:
  required: true | false
  reason: ""
human_involvement:
  required: true | false
  reason: ""
next_step: "..."
```

## Shared follow-through

When TRIAGE invokes or consumes Agent Council output, use `references/agent-council-followthrough.md`. This file exists in the current skill library and is intentionally not modified in this phase. Agent Council synthesis is evidence, not transition approval.

## Self-repair caveat

During this skill-library refactor, do not use UACP protected writers, Heartgate, MEMEX/BES, or `uacp-verify` as self-approval authority. Use normal file/git workflow plus Hermes/Kimi council verification. For normal UACP operation, TRIAGE-local council is for admission/routing/granularity; full Agent Council is reserved for lifecycle-semantics, Guardian/Heartgate uncertainty, or high-impact governance ambiguity. A skill is considered repaired only after its own implementation audit and end-of-implementation council return PASS/no concerns.
```

## Implementation constraints

Allowed implementation target:

```text
/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md
```

Disallowed:

- phase skill directories other than `uacp-triage`
- shared references
- UACP docs/config/state
- MEMEX/BES integration
- protected UACP writer or Heartgate approval calls

## Rollback

Before patching, save exact current content to:

```text
_refactor/uacp-triage/backup-SKILL-before-triage-implementation.md
```

If any deterministic audit check fails, or if end-of-implementation council returns CONCERNS/BLOCK, restore only `uacp-triage/SKILL.md` from backup before attempting a correction patch.

## Deterministic audit checks

After implementation:

- `uacp-triage/SKILL.md` exists
- line count under 120
- duplicate `## Rules` heading removed
- `TRIAGE is not PROPOSE` rule present
- routing outcomes present
- council/human-involvement trigger present
- output contract present
- shared follow-through is referenced, not inlined as 9-step body
- no other phase skill directory modified
- no shared references moved/deleted
- backup exists

## End-of-implementation review requirement

After implementation and deterministic audit, run full-perspective Agent Council review/audit using Hermes delegation and Kimi Code/Kimi K2.6 reviewers. Proceed/close only on PASS/no concerns.


## End-of-Decision council patch

A Devil's Advocate reviewer returned CONCERNS. This artifact was patched to resolve them:

1. Clarified that the YAML output contract is a default minimum, not a closed universal schema.
2. Clarified normal TRIAGE-local council vs. full Agent Council use.
3. Defined repaired status as implementation audit plus end-of-implementation council PASS/no concerns.
4. Defined rollback triggers: any deterministic audit failure or end council CONCERNS/BLOCK.
5. Verified `references/agent-council-followthrough.md` exists and noted it is not modified in this phase.

A follow-up end-of-Decision council must return PASS/no concerns before implementation.


## Final end-of-Decision verification — PASS

Two independent follow-up reviewers returned PASS/no concerns after the Decision patch.

Result:

```text
Decision gate passed.
Implementation may proceed as a one-file patch to /home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md only.
Backup, deterministic audit, and full-perspective Agent Council + Kimi review are mandatory.
```


## Implementation and deterministic audit result

Implementation completed as the authorized one-file patch:

- patched: `/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md`
- backup: `_refactor/uacp-triage/backup-SKILL-before-triage-implementation.md`
- old triage skill: 158 lines / 8,956 bytes
- new triage skill: 90 lines / 4,340 bytes

Deterministic compatibility audit: **PASS**

Checks passed:

- skill exists
- line count under 120
- duplicate `## Rules` heading removed
- `TRIAGE is not PROPOSE` rule present
- routing outcomes present
- council trigger present
- human-involvement trigger present
- output contract present
- shared follow-through reference present
- inlined 9-step follow-through body absent
- backup exists
- shared reference file still exists and was not modified

End-of-implementation full-perspective Agent Council + Kimi review/audit is still required before Phase 1 can close.


## End-of-implementation council concerns and correction

Initial full-perspective implementation council produced two material/near-material issues and one path-context false concern:

1. Practical audit found frontmatter description line longer than 120 characters. Corrected by shortening line 3 in `uacp-triage/SKILL.md`.
2. Devil's Advocate reported missing `uacp-triage` implementation after searching wrong roots. Correct root for this refactor is `/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md`, which exists and was patched.
3. Practical audit claimed `references/agent-council-followthrough.md` was empty; correct root check shows `/home/norty/.hermes/skills/devops/uacp/references/agent-council-followthrough.md` exists and is non-empty.
4. Git repository absence is accepted for this skills directory; rollback/audit relies on exact backup artifact and filesystem verification, as decided earlier.

A focused follow-up full-perspective Agent Council + Kimi review must return PASS/no concerns before closure.


## Follow-up implementation correction audit

Applied correction after initial implementation council concerns:

- shortened frontmatter description line
- wrapped long prose lines so maximum line length is now 120 characters
- preserved total skill length under 120 lines
- re-verified `references/agent-council-followthrough.md` exists and is non-empty at the correct path

Updated deterministic audit: **PASS**

Current `uacp-triage/SKILL.md`:

```text
117 lines
4,372 bytes
max line length: 120
```

A focused full-perspective Agent Council + Kimi review must now return PASS/no concerns before closure.


## Second follow-up implementation correction

Resolved material end-of-implementation council findings:

1. Corrected shared follow-through reference to `../references/agent-council-followthrough.md`, because the shared primitive lives in the parent `uacp/references/` directory.
2. Added explicit granularity ~7+ TRIAGE-local council trigger back into Rules.
3. Restored richer `phase_local_granularity` fields: `exit_actual`, `delta_reason`, and `downstream_projection`.
4. Restored richer `human_involvement` fields: `authority_needed` and `decision_owner`.
5. Added compact follow-through obligation: classify material blockers/concerns and record handled findings before advancing.
6. Preserved exact backup under the refactor artifact path and copied a compatibility backup to `/home/norty/.hermes/backups/uacp-triage-SKILL-before-implementation-20260515.md` for reviewers that look in the global backups directory.

A final full-perspective Agent Council + Kimi review must return PASS/no concerns before closure.


## Second follow-up deterministic audit result

After the second correction, deterministic audit is **PASS**:

- current skill: 114 lines / 4,668 bytes
- max line length: 120
- shared follow-through reference corrected to `../references/agent-council-followthrough.md`
- parent shared reference exists and is non-empty
- refactor artifact backup exists
- global compatibility backup exists
- richer `phase_local_granularity` fields restored
- richer `human_involvement` fields restored
- granularity around 7+ TRIAGE-local council trigger restored
- compact handled-findings obligation restored

A final full-perspective Agent Council + Kimi review is required for closure.


## Third follow-up implementation correction

Resolved final Devil's Advocate concerns about over-compression and schema regression:

1. Restored explicit anti-compression obligation in the execution checklist: when routing to PROPOSE, record TRIAGE→PROPOSE obligations and do not adopt proposal artifacts early.
2. Restored `factor_scores.notes`.
3. Restored `rationale`.
4. Restored `artifact_policy`.
5. Expanded `downstream_projection` into explicit phase keys: propose, plan, execute, verify, resolve.
6. Preserved line budget: current skill remains under 120 lines with max line length 120.

Updated deterministic audit: **PASS**

```text
current skill: 115 lines / 4,925 bytes
max line length: 120
```

A final focused Agent Council + Kimi review must return PASS/no concerns before closure.


## Final end-of-implementation verification — PASS

Final focused Agent Council + Kimi review after the third correction returned **PASS / no concerns**.

Result:

```text
Phase 1 uacp-triage implementation is closed as PASS.
```

Final verified state:

- target skill: `/home/norty/.hermes/skills/devops/uacp/uacp-triage/SKILL.md`
- current skill: 115 lines / 4,925 bytes
- max line length: 120
- anti-compression safeguards present
- granularity around 7+ TRIAGE-local council trigger present
- richer schema fields restored: notes, rationale, artifact_policy, downstream_projection, authority_needed, decision_owner
- shared follow-through reference corrected to `../references/agent-council-followthrough.md`
- shared follow-through file exists and is non-empty
- exact pre-implementation backup exists in `_refactor/uacp-triage/`
- compatibility backup exists in `/home/norty/.hermes/backups/`

Next phase must begin with START Agent Council before touching `uacp-propose`.

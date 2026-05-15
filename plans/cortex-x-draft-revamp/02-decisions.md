# Decisions — Cortex x-draft revamp

Run: `cortex-x-draft-revamp-20260514`

## Accepted decisions

### D1 — Additive revamp, not rewrite

The current `MaterialBundle`, `AngleContract`, and existing safety gates remain the base path. The revamp adds a planning/coherence layer rather than replacing gather/compose/gates wholesale.

### D2 — `ContentIntentContract` is new and separate from `AngleContract`

`AngleContract` remains the source/fact boundary. `ContentIntentContract` / `DraftPlan` owns content type, language/register mode, stance, why-share rationale, and coherence requirements.

### D3 — Hybrid language is context-selected

Language/register must not be globally hardcoded to `zh-hk`. A register selector chooses among Cantonese-English, Traditional Chinese-English, English-led hybrid, Cantonese-led, and plain English.

### D4 — Praise and criticism must be scoped

The workflow may share useful tools, repositories, and articles, but must avoid fake endorsement or fake rejection. Every positive/negative stance needs a scope: good/bad for what, under what condition, and with what limitation.

### D5 — Contradiction is blocked unless framed as explicit evolution

A draft that reverses a previous stance is blocked or rewritten unless it explains a changed condition, narrower scope, or explicit learning.

### D6 — Start with x_casual/original-new lane only

Initial EXECUTE scope is `XCasualComposerWorkflow` and its direct activities/config/tests. `XInteractionWorkflow` is out of scope except for inventory and future compatibility notes.

### D7 — Preserve current no-auto-post boundary

No automatic X posting is introduced. The workflow continues to produce Discord `#x-drafts` candidates for manual operator use.

### D8 — Default path stays stable during rollout

Current zh-hk behavior should remain available as a default or fallback until hybrid modes pass tests and dry-run review.

## Open decisions for PLAN/EXECUTE

### O1 — Stance ledger storage boundary

Options:

1. Query recent `x_originals` / editorial index and derive stance dynamically.
2. Add a dedicated DB table such as `x_stance_ledger`.
3. Store a curated config/artifact ledger.
4. Hybrid: start derived, graduate to DB after evidence.

PLAN recommendation: start with derived recent-output check unless implementation findings prove a DB table is necessary.

### O2 — Gate ordering

Candidate order:

```text
MaterialBundle
→ AngleContract
→ ContentIntentContract
→ prior stance context retrieval
→ Compose
→ post-compose StanceLedgerCheck
→ existing gates
```

PLAN must decide which stance checks run pre-compose as prompt context and which run post-compose as blocking/advisory gates.

### O3 — Untracked delegate-created review file

Out-of-band file:

`CORTEX_ROOT/docs/design/editorial-mass-restructure/x-draft-verification-review.md`

Disposition options:

- keep and move/adopt into Cortex docs in EXECUTE
- copy selected findings into UACP plan only and delete later with approval
- leave untracked until implementation worktree cleanup

No disposition is taken in PLAN without explicit handling.

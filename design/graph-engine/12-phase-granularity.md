---
type: contract
title: Graph Engine — Phase Granularity & Layout
description: Per-phase on-disk file layout (entity=file OKF + _index.yaml aggregate), the semantic->structural gradient, and a full worked example (oauth-login).
tags: [graph-engine, granularity, layout, okf, contract]
timestamp: 2026-06-19
edges:
  - {dst: 11-node-taxonomy, rel: depends_on, provenance: derived}
---

# Phase Granularity & Layout (contract)

Every phase produces an **aggregate directory**: one OKF `.md` per entity + one `_index.yaml`.
This levels PROPOSE/PLAN/VERIFY up to the granularity EXECUTE and the lessons corpus already have.

Worked example throughout: `run_id: oauth-login`.

## PROPOSE — intent nodes (body-dominant ~90:10)

```
proposals/oauth-login/
├── _index.yaml          # kind: proposal_index; members: [si-1, si-2]; edges: []
├── intent.md            # the narrative spine (one concept)
├── si-1.md
└── si-2.md
```
```markdown
---
kind: scope_item
id: si-1
title: Users can sign in with Google
authority: proposal.authority        # provenance: derived
status: proposed
---
Users at /login should authenticate with Google instead of a password.
Assumption: we already hold a Google OAuth client credential.
Risk: account-linking when an email already exists as a password user.
```
The only structural act is **minting identity** so later phases have something to point at.

## PLAN — the translation / pivot (~50:50)

```
plans/oauth-login/
├── _index.yaml
├── wu-1.md  wu-2.md  wu-3.md      # work_units
└── ev-1.md                       # evidence_obligation
```
```markdown
---
kind: work_unit
id: wu-2
title: Token-exchange endpoint
derives_from: [si-1]                 # provenance: ASSERTED — the one semantic commitment, frozen
status: planned
---
Add POST /auth/oauth/callback exchanging the Google code for tokens, issuing our JWT.
Done when: valid code -> 200 + JWT; invalid -> 401.
```
```yaml
# plans/oauth-login/_index.yaml
kind: plan_index
run_id: oauth-login
members: [wu-1, wu-2, wu-3, ev-1]
edges:
  - {src: wu-1, dst: si-1, rel: derives_from, provenance: asserted}
  - {src: wu-2, dst: si-1, rel: derives_from, provenance: asserted}
  - {src: wu-3, dst: si-2, rel: derives_from, provenance: asserted}
  - {src: ev-1, dst: wu-2, rel: obligation_for, provenance: derived}
coverage: {si-1: [wu-1, wu-2], si-2: [wu-3]}   # closure-gate input
```

> **`_index.yaml` is DERIVED (D21), not authored.** `uacp-fmt` regenerates `members`/`edges`/`coverage`
> from the member node files' frontmatter `derives_from` keys — the **child node key is canonical**;
> the aggregate is a projection. This is what makes concurrent writes race-free and prevents the
> aggregate-rewrite blast radius. A closure check (`index-consistency`) BLOCKs if the aggregate can't be
> reproduced from its members.

## EXECUTE — checkpoint nodes (~20:80; the join to reality)

```markdown
---
kind: checkpoint
id: cp-2
work_unit_id: wu-2                   # provenance: derived  -> PLAN
code_anchor:                         # provenance: parsed   -> REALITY (Slice 3)
  file: auth/oauth.py
  symbol: oauth_callback
  lines: 48-92
  commit: 3af19c2
evidence_refs: [executions/oauth-login/cp-2-test-log.txt]
result: pass
---
Implemented callback; integration test test_oauth_callback_issues_jwt green.
```

## VERIFY — assessment nodes (~10:90)

```markdown
---
kind: assessment
id: as-1
obligation_id: ev-1                  # provenance: derived -> PLAN obligation
work_unit_id: wu-2                   # provenance: derived
evidence_refs: [cp-2]                # provenance: derived -> EXECUTE checkpoint
result: pass
---
ev-1 satisfied: cp-2 shows the callback issuing a JWT for a valid code.
```
An `assessment` cannot exist without a real `ev-1` and a real `cp-2` to point at — this is where
"verify something that does not exist / was skipped" dies.

## RESOLVE — re-semanticized knowledge (~80:20)

```markdown
---
kind: lesson
id: lesson-oauth-account-linking
type: lessons
source_run: oauth-login              # provenance: derived
derived_from: [si-1, wu-2, as-1]     # provenance: derived -> back into the run graph
---
When adding a federated provider, resolve account-linking against existing email-identity
*before* issuing a session, or you create duplicate identities.
```
Lands in the shared OKF wiki — a lesson and a scope_item are both nodes, differing only in `kind`
and edge provenance.

## The shape of the whole run

```
si-1 ──derives_from(asserted)── wu-2 ──work_unit_id(derived)── cp-2 ──code_anchor(parsed)── oauth_callback()
  │                                                              │
  └────────────── lesson.derived_from(derived) ──── as-1 ──evidence_refs(derived)──┘
```
Semantic at the ends, structural in the middle; one `asserted` edge, everything else provable.

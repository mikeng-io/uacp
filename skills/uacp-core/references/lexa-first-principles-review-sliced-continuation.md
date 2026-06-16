# LEXA First-Principles Review — Sliced Continuation Pattern

Use after a LEXA documentation authority reset has completed and Mike asks to continue reviewing LEXA from first principles under UACP discipline.

## Trigger signals

- Mike says to continue/proceed after `lexa-doc-restart-*` or equivalent draft reset.
- LEXA docs are all draft, but content correctness still needs review.
- The question is design/documentation review, not implementation.

## Correct framing

Treat the work as a bounded UACP review run for draft architecture coherence. Do **not** imply LEXA itself is accepted, canonical, implemented, or runtime-ready.

Typical status language:

```text
Draft architecture coherence: pass for current review scope
Implementation readiness: no
Runtime authorization: no
Canonical promotion: no
```

## Slice order that worked

1. Conductor and core boundary
   - `00-index.md`
   - `01-layer-model.md`
   - `02-boundaries.md`
2. Semantic/source/scope structure
   - `03-sef-sgrn-integration.md`
   - `04-workspace-peer-source-scope.md`
   - `10-source-registry-contract.md`
3. Query/schema guardrails
   - `05-query-contract.md`
   - `06-event-graph-schema.md`
   - `06-non-goals.md`
4. Runtime/examples/questions
   - `12-runtime-boundary-sketch.md`
   - `11-end-to-end-examples.md`
   - `07-open-questions.md`
5. Schema/review/promotion reconciliation
   - `schemas/00-schema-index.md`
   - schema files under `schemas/`
   - `08-review-notes.md`
   - `09-council-synthesis.md`
   - `13-routing-status-and-promotion-plan.md`

## Patch posture

For each reviewed slice:

- preserve `status: draft`;
- preserve or add the draft restart guard;
- add/update `review_status: first_principles_reviewed` and `review_run: <run_id>` where useful;
- remove premature `## Decision` headings from architecture docs;
- reframe accepted-sounding statements as `Draft hypothesis`, `Review conclusion`, or `Current interpretation`;
- keep review/council notes as evidence, not doctrine;
- update schema files only as draft validation aids, not runtime contracts.

## Evidence pattern

After each slice, write a compact UACP checkpoint under:

```text
UACP_ROOT/.outputs/<run_id>/slice-N-<topic>-checkpoint.md
```

Each checkpoint should state:

- reviewed docs;
- findings and disposition;
- current interpretation;
- what is **not accepted**;
- next slice or next phase.

## Key architectural lessons from the LEXA pass

- SEF and SGRN should remain internal LEXA capabilities for now, not standalone engines.
- Workspace/peer/source/scope is a required safety boundary before query/event/runtime work.
- Source registry is the structural dependency that prevents LEXA from becoming an ungrounded context blender.
- Query packets are scoped evidence packets, not raw retrieval output.
- Event/graph records are source-backed derived views, not canonical state.
- Runtime work remains blocked until a later promotion path exists.
- The next concrete propulsion surface should be schemas + fixtures + validator, not daemon/API/live Nora/Cortex integration.

## VERIFY before RESOLVE

Before closing the review run, verify:

- all in-scope docs remain draft;
- draft restart guards remain present;
- reviewed docs have review-run markers where appropriate;
- no premature `## Decision` headings remain in reviewed architecture docs;
- schema files parse as YAML;
- schema files structurally reflect the reviewed source/query/event/graph contract;
- all slice checkpoints exist.

## Operator summary rule

Report conclusion-first and compactly. Avoid raw inventories unless Mike asks. Always qualify scope: `first-principles draft review resolved`, not `LEXA resolved`.

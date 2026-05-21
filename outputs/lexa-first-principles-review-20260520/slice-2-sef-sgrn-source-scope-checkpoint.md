---
kind: uacp.execute_checkpoint
run_id: lexa-first-principles-review-20260520
phase: EXECUTE
status: pass
created: 2026-05-21
owner: mike
subject: LEXA first-principles review slice 2
reviewed_docs:
  - /home/norty/vault/02-architecture/LEXA/03-sef-sgrn-integration.md
  - /home/norty/vault/02-architecture/LEXA/04-workspace-peer-source-scope.md
  - /home/norty/vault/02-architecture/LEXA/10-source-registry-contract.md
---

# LEXA First-Principles Review — Slice 2 Execute Checkpoint

## Reviewed slice

1. `03-sef-sgrn-integration.md`
2. `04-workspace-peer-source-scope.md`
3. `10-source-registry-contract.md`

## Findings and disposition

1. `03-sef-sgrn-integration.md` still used `## Decision` language and sounded too canonical.
   - disposition: patched to `Draft hypothesis`, added review posture, containment rationale, boundary invariants, and open questions.
2. SEF/SGRN standalone-vs-internal status needed sharper reasoning.
   - disposition: kept them as LEXA-internal capabilities for now because standalone engines would multiply authority/runtime surfaces before LEXA contracts are stable.
3. `04-workspace-peer-source-scope.md` asserted workspace/source/scope rules but needed stronger leakage and projection semantics.
   - disposition: patched with workspace-first safety invariant, peer projection rule, explicit cross-workspace exclusions, and Nora/Cortex examples.
4. `10-source-registry-contract.md` needed to become the structural dependency before query/event/runtime review.
   - disposition: patched with minimum source record additions, source-backed query obligations, conflict/freshness rules, and explicit non-canonical draft posture.

## Current interpretation

The second review slice supports this draft structure:

```text
LEXA remains a Layer 1 enquiry surface.
SEF and SGRN remain internal LEXA capabilities, not standalone engines.
Workspace/peer/source/scope is a required safety boundary.
Source registry is the next structural dependency before query/event/runtime work.
```

## Not accepted

No architecture decision is accepted by this checkpoint. The reviewed documents remain Vault drafts. This checkpoint does not authorize implementation, runtime wiring, API creation, source registry deployment, or canonical promotion.

## Next slice

Review:

1. `05-query-contract.md`
2. `06-event-graph-schema.md`
3. `06-non-goals.md`

Purpose: test whether the query packet and event/graph schema now follow the source registry and workspace/scope model instead of bypassing it.

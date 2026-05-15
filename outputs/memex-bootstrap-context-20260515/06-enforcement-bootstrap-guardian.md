# 06 — Enforcement, Bootstrap, and Guardian

## User correction

Mike clarified that **during implementation of MEMEX**, it cannot be a normal UACP proposal because Guardian will eventually stop all execution when governance documents/config/runtime policy are touched.

This corrected the earlier framing.

## Core issue

If implementing MEMEX requires editing UACP governance docs/config/runtime policy, a normal UACP proposal can deadlock:

```text
Need to modify governance docs/config
→ Guardian says protected governance mutation requires UACP context / safe writer / containment
→ but the change is precisely about repairing/extending that governance machinery
→ Guardian eventually blocks execution
```

Therefore:

```text
MEMEX implementation cannot initially be governed as a normal UACP proposal/run.
```

## Correct classification

MEMEX implementation is:

```text
UACP control-plane bootstrap / governance substrate patch
```

Not:

```text
ordinary UACP proposal
```

Reason:

```text
It changes the machinery that makes UACP execution possible, so it cannot initially depend on the full UACP lifecycle path it is modifying.
```

## Control-Plane Bootstrap Lane

Proposed lane:

```text
Control-Plane Bootstrap Lane
```

Purpose:

```text
A narrow, explicit recovery/extension path for changing UACP governance docs/config/runtime policy when the normal governed lifecycle path is unavailable, circular, or fail-closed.
```

This is not bypass by convenience. It is an authority-declared bootstrap lane.

Allowed only when:

1. The change touches UACP governance/control-plane infrastructure.
2. The normal UACP lifecycle/write path is blocked or circular.
3. The intended change is required to restore or extend governance capability.
4. The scope is bounded and predeclared.
5. Every mutation is recorded as a bootstrap exception.
6. Verification occurs immediately after.

## Guardian behavior during bootstrap

Guardian should not be globally loosened.

Instead, Guardian needs a bootstrap mode / bootstrap authority artifact.

Example bootstrap authority:

```yaml
bootstrap_authority:
  id: uacp-bootstrap-memex-20260515
  reason: Implement MEMEX control-plane substrate; normal UACP proposal path is circular because protected governance docs/config are mutation targets.
  allowed_targets:
    - UACP_ROOT/docs/**
    - UACP_ROOT/config/**
    - UACP_ROOT/references/**
    - UACP_ROOT/runtime-adapters/**
    - UACP_ROOT/verification/**
  forbidden_targets:
    - secrets
    - private memory
    - unrelated Hermes config
    - production external systems
    - non-UACP project code
  allowed_actions:
    - read
    - create bootstrap docs
    - patch governance docs/config
    - add validation scripts
    - add MEMEX schema/prototype
  constraints:
    - minimal delta
    - no silent state mutation
    - no live enforcement activation until verified
    - all writes logged
    - rollback path required
```

Guardian then enforces the bootstrap contract rather than the normal proposal contract.

## If Guardian cannot support bootstrap yet

If current Guardian literally cannot support bootstrap mode yet, the first step is:

```text
manual/operator-authorized bootstrap exception
→ recorded authority artifact
→ minimal Guardian policy patch
→ bootstrap lane active
→ MEMEX docs/config/schema patch
→ verify
→ progressive enforcement
```

Not:

```text
disable Guardian globally
```

And not:

```text
pretend normal UACP proposal can handle it
```

## During implementation vs after implementation

### During MEMEX bootstrap

```text
Guardian should enforce bootstrap scope.
```

It should:

- allow only declared bootstrap writes,
- block everything outside scope,
- require artifact/log/rollback.

### After MEMEX exists

```text
Guardian should enforce MEMEX obligations.
```

It should:

- require MEMEX retrieval/extraction metadata for protected UACP actions,
- block unproven MEMEX writes,
- require governed writer for BES mutation.

## Enforcement after MEMEX exists

Each phase should have MEMEX obligations.

### Phase entry: retrieval required

Before each phase:

```text
TRIAGE: retrieve similar runs/failures/patterns
PROPOSE: retrieve authority constraints and prior decisions
PLAN: retrieve execution pitfalls and verification obligations
EXECUTE: retrieve runtime/worker failure modes
VERIFY: retrieve prior invariants/warnings
RESOLVE: retrieve prior lessons and BES candidates
```

Metadata:

```yaml
memex_context:
  retrieval_status: used | waived | not_required
  packet_id: memex.packet.20260515.x
  query_hash: ...
  generated_at: ...
  reason_if_waived: ...
```

### Phase exit: extraction declaration required

At phase exit:

```yaml
memex_extraction:
  status: none | candidates_created | deferred | not_applicable
  candidate_count: 3
  candidate_artifact: outputs/memex/candidates/...
  deferred_reason: no durable finding
```

Guardian should not force every phase to create a lesson. It should force the phase to declare whether extraction was considered.

### Creation / BES updates

Creation happens through RESOLVE or governed writer:

```yaml
memex_write:
  accepted_candidates:
    - memex.item.xxx
  bes_updates:
    - item_id: ...
      eligible_delta: 1
      success_delta: 1
```

## Layered enforcement

Enforcement should split across four layers:

```text
1. Phase skill / phase wrapper
2. Guardian
3. Heartgate
4. Governed writer
```

## Progressive enforcement stages

Because MEMEX does not exist yet, enforcement must not start hard-fail everywhere.

Stages:

### Stage 0 — Advisory

```text
Phase skills ask for MEMEX, but do not block.
```

### Stage 1 — Required declaration

```text
Every material phase artifact must say: MEMEX used / waived / unavailable.
```

### Stage 2 — Required packet for high-risk transitions

```text
Heartgate requires packet or waiver for PLAN→EXECUTE, EXECUTE→VERIFY, VERIFY→RESOLVE.
```

### Stage 3 — Guardian enforcement for protected actions

```text
Protected UACP writes and runtime execution require memex_context.
```

### Stage 4 — BES feedback enforcement

```text
RESOLVE must consider BES updates for retrieved items.
```

## Final corrected doctrine

```text
Normal UACP proposal governs work under UACP.
Bootstrap lane governs changes to the machinery of UACP itself.
```

MEMEX is the latter during implementation.

Final sentence:

```text
MEMEX implementation cannot initially be a normal UACP proposal. It should be treated as Control-Plane Bootstrap work for UACP itself. Guardian should eventually enforce MEMEX, but during implementation the first problem is to give Guardian a bootstrap authority lane so it does not block legitimate governance-substrate edits while still preventing arbitrary mutation.
```

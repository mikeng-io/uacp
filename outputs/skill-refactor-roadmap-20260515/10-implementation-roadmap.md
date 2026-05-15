# Implementation Roadmap

## Roadmap rhythm

For each item:

```text
Explore → Determine → Decision → Review → Audit → Implement
```

## Items

### 0. UACP router
Make umbrella `uacp/SKILL.md` a router only.

### 1. TRIAGE
Build `uacp-triage` as a module that prevents silent TRIAGE→PROPOSE compression.

### 2. PROPOSE
Build `uacp-propose` as a proposal package producer with evidence and approval contracts.

### 3. PLAN
Build `uacp-plan` as a plan package producer: requirements, design, execution plan, verification plan, transition.

### 4. EXECUTE
Build `uacp-execute` around mutation boundaries, side effects, worker dispatch, remediation, rollback.

### 5. VERIFY
Build `uacp-verify` as read-only verification with findings, council synthesis, follow-through gate, transition.

### 6. RESOLVE
Build `uacp-resolve` as closure: final artifacts, residual risk, lessons, state closure handoff.

### 7. STATE
Build `uacp-state` around mutation contract, schemas, transition records, audit ledger.

### 8. Shared references cleanup
Only after phase modules exist, classify shared references into shared primitives, phase-owned, archive, delete candidates.

---
type: contract
title: Graph Engine — Negative Space (constraints & metrics)
description: First-class guardrail nodes — what NOT to do, how NOT, why NOT — plus measurements; constrains/measured_by/violated edges that become deterministic EXECUTE/VERIFY checks. Slice 3.
tags: [graph-engine, constraints, metrics, negative-space, contract]
timestamp: 2026-06-19
edges:
  - {dst: 11-node-taxonomy, rel: extends, provenance: derived}
---

# Negative Space — Constraints & Metrics (contract · Slice 3)

Today the manifest serializes only **affordances**: do X, here is how, here is why. The guardrails
are missing as first-class objects — `out_of_scope` is bare strings, with no identity, no
measurement, no enforcement. The agent has no deterministic boundary, only a hope. That is its own
phantom-family failure: an agent does unrequested work precisely because nothing serialized a "don't."

## The three negatives + measurement, as nodes

| Need | Node kind | Serialized as |
|---|---|---|
| What we should **not** do | `prohibition` | a node; `constrains → si-x` (provenance: asserted) |
| **How** we should not do it | `method_constraint` | a node; forbidden approach; `constrains → wu-x` |
| **Why** we are not doing it | (the body) | the rationale prose of the constraint node |
| **Measurement** (the bound) | `metric` | `measured_by → wu-x`; the quantitative limit |

## Example

```markdown
---
kind: prohibition
id: pr-1
constrains: [si-1]                   # provenance: asserted
status: active
---
Do NOT store the Google access/refresh tokens in plaintext or in application logs.
Why: PCI/secret-handling; a leaked refresh token is a standing account compromise.
```
```markdown
---
kind: metric
id: m-1
measured_by_of: [wu-2]               # this metric bounds wu-2
threshold: { p95_callback_latency_ms: 800, token_at_rest_plaintext_count: 0 }
---
Callback p95 latency must stay under 800ms; zero tokens may be persisted in plaintext.
```

## From semantic to enforceable

A constraint is *authored* semantically (judgment: "we must not store raw tokens — why: PCI") — that
is an `asserted` edge. But once it carries a **metric**, it becomes a **deterministic check** at
EXECUTE/VERIFY:

- the checkpoint/assessment evaluates the metric's threshold against captured evidence,
- a breach emits a `violated` edge (`checkpoint → metric` / `assessment → prohibition`),
- the closure report surfaces any `violated` edge as a blocker.

Negative edges are exactly as provable as positive ones. Where `derives_from` says "this exists
because of that intent," `constrains` says "this must not cross that boundary," and `measured_by`
says "here is how we prove it stayed inside." Together: directives + boundaries + measurement = a
complete spec.

## Why Slice 3, not Slice 1

Constraints reuse the entire node/edge/granularity/writer machinery — they are new `kind`s and new
`rel_type`s, nothing structurally novel. So they build **on** Slice 1 and sequence cleanly after it.
PLAN is where they matter most: it is the execution-level translation that today inherits zero
enforceable limits from PROPOSE.

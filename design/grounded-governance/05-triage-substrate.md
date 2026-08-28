---
type: design
title: "TRIAGE grounding: the declared scope against the real project root"
description: "The head of the cascade. TRIAGE scores scope and routes governance; today it reads the design/intent and never compares to the real code the scope names. The substrate is the kernel-produced slice of the project root the scope points at — existence, structure, and (via the code plane) the real symbols — so the scope-scoring is grounded in what is actually there, not what the design assumes."
tags: [grounded-governance, triage, scope, project-root, cascade, code-plane]
timestamp: "2026-08-24"
edges: [{dst: 04-grounding-is-per-phase, rel: depends_on, provenance: derived}]
---
# TRIAGE grounding: the declared scope against the real project root

## The declaration and the disease

TRIAGE emits the first governed declaration: the **scope** (what the run will touch), the
**granularity score** (how big/entangled it is), and the **routing** (doc-hygiene vs full-governance).
The disease is that it forms all three from the *design or the intent* — the agent's account of the
work — and never compares them to the **real project root**. So triage can:

- scope to files/symbols that **do not exist**, or miss ones that do;
- score a change "small / P2 / doc-hygiene" when the real code it names is **entangled** (a two-line
  change with a large real blast-radius);
- accept a premise ("X is broken", "there is no handler for Z") that is **false against reality**.

Every one of these mis-scopes the whole run, and because triage is the *first* gate, the error is
inherited by PROPOSE, planned against by PLAN, and "verified" at VERIFY as faithful to an intent that
was never real. This is why triage is the head of the cascade.

## The substrate: the slice of the project root the scope names

There is no diff at triage (no work yet). The reality to screen against is the **current project root
as it relates to the declared scope**. The kernel produces, for the scope's declared targets:

1. **Existence + structure** (deterministic) — for each path/glob the scope names, does it resolve in
   the real tree? file vs dir, size, and for code files the real symbol inventory. A scope naming a
   nonexistent target is a hard fail, no judgment required.
2. **The real symbols + their shape** (code plane) — for a symbol-level scope, the actual
   definition and the *real* local complexity/entanglement (via LSP/SCIP — the same code plane PLAN
   uses), so the **granularity score can be checked against real structure**, not the design's
   assumption of it.
3. **The premise's referent** (for a "fix X" scope) — enough of X's real state to later let PROPOSE
   reproduce the premise (`06`); triage's job is to confirm the *referent exists and is what the scope
   says it is*, not yet to reproduce its behavior.

This slice is a **new substrate producer**: "the real state of the targets a scope declares." It reuses
the git/project-tree witness and the code plane; what is new is *keying the produced reality off the
declared scope*.

## Mechanism: a deterministic floor under a semantic screening

Two layers, matching the machine (`04`):

- **Deterministic floor** — the scope's named targets must **resolve** against the real tree (exist +
  are the declared kind). A scope naming a phantom target blocks with no agent involved. This is the
  M2 "resolves, not asserted" rule applied to scope targets.
- **Semantic screening** — over the produced slice, an agent screens the *judgment* parts: is the
  granularity score consistent with the real structure? is the routing (doc-hygiene vs full) right
  given what the code actually is? is the premise's referent real? Charged like `02` (fuzzy intent,
  Code Review Rules, no checklist), grounded in the produced slice, typed findings.

## The gate

TRIAGE-exit cannot pass unless the scope's targets resolve (floor) **and** a screening covering the
produced project-root slice cleared or its findings were dispositioned (M2/M3d, reused verbatim). The
substrate-hash fixpoint (`03`) applies: if the scope is revised, the produced slice changes, the hash
changes, and a stale screening no longer covers — re-screen. Config-gated `warn`→`block` migration,
as everywhere.

## What is genuinely new vs reused

New: the substrate producer (project-root slice keyed by declared scope) and the granularity/routing
screening charge. Reused wholesale: the resolves-not-asserts floor (M2), the disposition loop (M3d),
the fixpoint gate + config migration (`03`), and the screening dispatch discipline (`02`). Triage
grounding is the same machine with its own substrate — and the highest-leverage instance, because it
stops the cascade at its source.

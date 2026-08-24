---
type: design
title: "PLAN grounding: the declared blast-radius against the real call graph"
description: "PLAN declares an approach and a blast-radius; today it asserts what the change touches without deriving the real impact. This grounding is deterministic, not a screening: the agent CLAIMS the blast-radius, the code plane (LSP/SCIP/codeflair) DERIVES the real one, the gate COMPARES. It is prevention-at-PLAN — catch the under-scoped change before it is built — and mostly a matter of wiring a built-but-unfed tool."
tags: [grounded-governance, plan, blast-radius, code-plane, codeflair, lsp, scip, prevention]
timestamp: "2026-08-24"
edges: [{dst: 04-grounding-is-per-phase, rel: depends_on, provenance: derived}]
---
# PLAN grounding: the declared blast-radius against the real call graph

## The declaration and the disease

PLAN declares the approach and, materially, the **blast-radius**: the `write_paths` it will touch and
(implicitly) what those changes affect. The disease is that the plan **asserts** its impact without
**deriving** it. It writes "this changes the toll-fee loader, scope: `services/toll/`" without ever
asking the real call graph *who depends on the symbol being changed*. So it plans against an assumed
impact and misses the real callers — the "two-line change" whose signature change breaks eleven call
sites nobody listed. VERIFY (`00`–`03`) catches the resulting defect *after it is built*; PLAN
grounding catches the under-scope *before a line is written*. That is the prevention/detection split.

## The substrate: the real blast-radius, derived by the code plane

Reality here is the **actual call graph**: for every symbol the plan will change (signature, behavior,
deletion), its real callers, implementers, and dependents. The kernel produces this from the **code
plane** — LSP `findReferences` / call-hierarchy, or the persistent SCIP index (codeflair). This is the
same code plane TRIAGE uses for structure; here it is used for *impact*. The produced substrate is the
derived set of impacted paths/symbols — the blast-radius reality against which the plan's declared
`write_paths` are compared.

## Mechanism: deterministic — claim, derive, compare

Unlike TRIAGE/PROPOSE/VERIFY, PLAN grounding needs **no adversarial agent**. It is the deterministic
witness pattern (`Codeflair = the deterministic witness`):

> the agent **CLAIMS** the blast-radius (its `write_paths` / declared impact) →
> the code plane **DERIVES** the real one (LSP/SCIP call graph) →
> the gate **COMPARES**: does the declared scope **cover** the derived impact?

If the real blast-radius escapes the declared `write_paths` — a caller that will break lives outside
the plan's scope — the plan **under-scoped**, and the gate blocks (or warns, under migration). This is
structurally the same comparison M3c made at VERIFY (`SC_DIFF_OUT_OF_SCOPE`: real change set vs declared
`write_paths`) — but run at PLAN, over the *derived* blast-radius instead of the *actual* diff. M3c is
detection of an out-of-scope write; this is **prevention** of an out-of-scope plan.

## The one real cost: wiring, not designing

The leverage here is that the machinery already exists. **Codeflair — the code-plane engine — is built
and merged; its LSP edge source is simply unfed** (the Serena/pyright feed on the backlog). So PLAN
grounding is not a new engine so much as: (a) feed the code plane so `findReferences`/call-hierarchy
resolves, and (b) add a PLAN-exit gate that compares the derived blast-radius to the declared
`write_paths`. This is the grounded-governance fix pattern in its purest form — *the reality tool is
present but unwired; wire it to a mandatory gate.*

## The gate

PLAN-exit cannot pass unless the declared `write_paths` **cover** the code-plane-derived blast-radius,
or each escaping impact is **adjudicated** (M3d — "this caller is intentionally out of plan scope
because …"). Coverage is deterministic; the escape-hatch is the same adjudication grammar the rest of
the floor uses. Config-gated `warn`→`block` migration (the code plane's freshness/root caveats mean
warn-first is essential — an unavailable or stale index yields warn, never a false block, exactly as
`SC_DIFF_UNAVAILABLE` stays warn).

## What is reused

Almost everything: the `write_paths` declaration + the coverage comparison (M3c/`scope_conformance`),
the adjudication escape (M3d), the config migration + fixpoint (`03`), and the code-plane engine
itself. New only: feeding the code plane its LSP/SCIP edges, and pointing the coverage comparison at
the *derived* blast-radius at PLAN-exit rather than the *actual* diff at VERIFY.

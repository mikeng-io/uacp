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
plane** — codeflair's **baseline witness** (`witness.build_baseline_witness`, the diff-independent
PLAN-exit mode), fed by the **SCIP** index (the real, present edge producer; `scip_ingest`). This is
the same code plane TRIAGE uses for structure; here it is used for *impact*. The produced substrate is
the derived set of impacted paths/symbols — the blast-radius reality against which the plan's declared
`write_paths` are compared.

**Correction against reality (grounded, not assumed):** this is not unbuilt. The PLAN-exit blast-radius
path **already exists and is wired** — `scope_conformance.validate_cascade_forecast` ("PREVENTION-at-
PLAN forecast") derives the baseline neighborhood + exact `inbound_counts` of the declared refs and
even writes a *forecast-of-record*. Two facts corrected the earlier framing: (a) the blast-radius is
fed by **SCIP**, not by the "lsp" source; (b) the "unfed lsp" is a query-time **freshness overlay**
(`LspOverlay`, Serena) that re-tags node freshness — it does **not** produce blast-radius edges and is
**orthogonal** to this gate. So PLAN grounding is not an infra project; it is the smallest of the three
remaining instances.

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

## The real work: promote an existing gate, don't build a new one

The machinery already exists **and is wired**. `validate_cascade_forecast` runs at PLAN-exit today,
SCIP-fed, and derives the baseline blast-radius — but it is **advisory** (`SC_PLAN_CASCADE_FORECAST`
is `warn`) and it writes a forecast-of-record for VERIFY-side recall. So PLAN grounding is an
**M3c-style promotion**, not a new engine:

1. **Promote to blocking** — make the plan's declared `write_paths` *cover* the forecasted cascade a
   fail-closed requirement (config-gated `warn`→`block`, exactly as M3c promoted `SC_DIFF_OUT_OF_SCOPE`),
   with the M3d adjudication escape for an intentionally-out-of-plan caller. An unavailable/stale index
   stays `warn` (`SC_FORECAST_WITNESS_UNAVAILABLE` — environment fact, never a false block).
2. **(Optional) go transitive** — the wired forecast is **hop-1** only; the transitive walk
   (`query.blast_radius`) exists in codeflair but isn't projected through the witness wire. Projecting
   it gives N-hop blast-radius for deeper prevention. This is a completeness add, not a blocker.

The "lsp feed" (Serena overlay) is **not** on this path — it is a freshness nicety orthogonal to the
blast-radius, and building it is neither required nor sufficient here. This is the grounded-governance
fix pattern in its cleanest form: *the reality tool is present and wired but advisory — make it bite.*

## The gate

PLAN-exit cannot pass unless the declared `write_paths` **cover** the code-plane-derived blast-radius,
or each escaping impact is **adjudicated** (M3d — "this caller is intentionally out of plan scope
because …"). Coverage is deterministic; the escape-hatch is the same adjudication grammar the rest of
the floor uses. Config-gated `warn`→`block` migration (the code plane's freshness/root caveats mean
warn-first is essential — an unavailable or stale index yields warn, never a false block, exactly as
`SC_DIFF_UNAVAILABLE` stays warn).

## What is reused

Almost everything: the `write_paths` declaration + the coverage comparison (M3c/`scope_conformance`),
the adjudication escape (M3d), the config migration + fixpoint (`03`), the code-plane engine, **and the
already-wired PLAN-exit forecast** (`validate_cascade_forecast`, SCIP-fed). New only: flipping the
forecast from advisory to a coverage *requirement* (config-gated), and — optionally — projecting the
transitive `query.blast_radius` into the baseline witness for N-hop reach.

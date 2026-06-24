---
type: analysis
title: The Primitive — verification as comprehend → measure → serialize
description: Verification is CMS run in a particular mode. Specializes the three verbs to the verify lifecycle (measure = grounded judgment of which check would prove the claim; determinism relocated to the gate's replay), names the EXECUTE generation-exclusion (no-self-attestation), and references the canonical CMS bundle rather than re-deriving it.
tags: [verification, primitive, comprehend-measure-serialize, generative-gate, no-self-attestation]
timestamp: 2026-06-24
edges:
  - {dst: 01-evidence-503, rel: motivated_by, provenance: asserted}
---

# The Primitive — verification as `comprehend → measure → serialize`

## In one sentence

`comprehend → measure → serialize` (**CMS**) is UACP's core principle — the canonical statement lives in [`design/comprehend-measure-serialize/`](../comprehend-measure-serialize/00-the-axiom.md) and in AGENTS.md's *Core Principle*. This bundle does not redefine it; it is the **verification instantiation** of CMS. Making verification systematic is therefore not "designing a verify feature" — it is **running the one principle correctly in the verify mode at every phase.**

## What verification adds to CMS

CMS already fixes the disciplines on the three verbs ([10-comprehend](../comprehend-measure-serialize/10-comprehend.md), [11-measure](../comprehend-measure-serialize/11-measure.md), [12-serialize](../comprehend-measure-serialize/12-serialize.md)). Verification *specializes* them — the column that matters here is **how `measure` is run** and **who holds authority**:

| Verb | In verification | The CMS discipline it inherits |
|---|---|---|
| **comprehend** | read the artifact's actual intent / claims / reality | the ONLY semantic touch; **bounded** (one judgment), **recorded** (auditable) |
| **measure** | judge **which specific check would actually prove the claim** — author an executable assertion, not a weak proxy | **grounded in the real property** + **fail-closed** (PASS/FAIL/**ERROR** distinct, ERROR on malformed input). It is a *semantic* act — **not** deterministic; determinism is relocated to where the check is replayed |
| **serialize** | **canonicalize** that authored check + its verdict into a typed key with provenance (`derives_from`) | one explicit canonical form, provenanced — *not* "durability" |

## The determinism relocation (why verification is the cleanest CMS instance)

CMS's load-bearing move: the **agent's `measure` is grounded, not deterministic** — *determinism belongs to the verifying gate, not the agent's judgment* (AGENTS.md Core Principle; [25-enforcement-surfaces](../comprehend-measure-serialize/25-enforcement-surfaces.md)). Verification embodies exactly this as a pipeline:

> the agent **comprehends** the artifact → **measures** (grounds a judgment of *which check would prove it*) → **serializes** that check (freezes it) → the **gate replays it deterministically**, forever.

The one semantic touch is **bounded to generation** and **recorded**; the **replay is deterministic**. Same move as the graph-engine's `asserted` edge — *judgment made once, serialized, replayed deterministically after* ([graph-engine overview](../graph-engine/00-overview.md)). The gate does not "use AI to check"; it uses comprehension to **author a deterministic check**, freezes it, and the [harness](11-harness.md) replays it. The [investigation ledger](13-investigation-ledger.md) records what was generated and why, so the generation is auditable, not a black box.

This is the graph-engine thesis generalized from *edges* to *the whole method*: **a verification not serialized as a replayable check is one you have agreed to re-judge by hand every phase** — exactly how Trustless #503 burned 7 review rounds ([01-evidence-503](01-evidence-503.md)).

## It is fractal — by design, for coherence

The same triad is **imposed** at three scales — lifecycle, phase, gate. Per [23-composition](../comprehend-measure-serialize/23-composition.md) this is a **deliberate choice for coherence, not a discovered recursion** (there is nothing to retrofit): the system reasons the way its gates govern the way its phases chain.

- **lifecycle** — phases chained by serialized artifacts; `serialize(phase N)` *is* the `comprehend` input of phase N+1.
- **phase** — each phase's internal verification *is* a CMS loop.
- **gate** — the [generative gate](10-generative-gate.md) is literally comprehend→measure→serialize.

The chaining is what makes it cognition rather than context: each frozen anchor resists drift, so a disciplined *loop* of comprehensions becomes coherent direction held over time ([23-composition](../comprehend-measure-serialize/23-composition.md) covers the iterated axis).

## Per-phase: same operation, rotating measure-mode + authority

The canonical per-phase crosswalk (which artifact kind / gate each phase serializes) lives in [24-phase-crosswalk](../comprehend-measure-serialize/24-phase-crosswalk.md). What *this* table adds is verification's two specializing columns — the **mode of `measure`** and **who holds authority** ([12-phase-profiles](12-phase-profiles.md) expands it, incl. the goal-driven track):

| Phase | measure — mode | authority |
|---|---|---|
| TRIAGE | classify (scope / risk / granularity) | router |
| PROPOSE | **generate** success criteria (assertions) | authority |
| PLAN | **generate** decomposition checks (coverage, per-`work_unit` obligations) | authority |
| **EXECUTE** | **satisfy** the frozen criteria (produce evidence) | **the doer (blind)** |
| VERIFY | **check** criteria + **generate** checks for emergent reality | separate authority |
| RESOLVE | **distill** what held | curator |

### Why EXECUTE is excluded from *generation* (the structural guarantee)

The measure-mode **generate** *authors the success criteria*. UACP invariant #5 is **"no self-attesting closures."** If the **doer** (EXECUTE) could generate its own measurements, that is the doer defining its own pass condition — self-attestation, structurally forbidden. So:

- the **generative** half runs at PROPOSE / PLAN (define) and VERIFY / RESOLVE (check + distill) — **never EXECUTE**;
- the **running** half (the [harness](11-harness.md) replaying frozen checks) runs **everywhere**, including at EXECUTE checkpoints.

EXECUTE is therefore **sandwiched, blind, producing** between "define success" (authority) and "confirm success" (separate authority). That sandwich *is* the separation of powers. CMS confirms this independently: EXECUTE is "the one phase excluded from self-measurement … the load-bearing asymmetry of the whole lifecycle" ([24-phase-crosswalk](../comprehend-measure-serialize/24-phase-crosswalk.md)).

## Two layers fall out of this

- **Layer 1 — the harness** ([11-harness](11-harness.md)): fixed *activity* — run / reconcile / loop / escalate. Deterministic machinery, same every time. Mostly **IMPROVISE/UPDATE** of the existing engines (`run_all_engines`, `GP_CONTRADICTED`, `uacp_escalation_event`).
- **Layer 2 — the generative gate** ([10-generative-gate](10-generative-gate.md)): dynamic — per-phase `comprehend → measure → serialize` whose *actions are generated from the content*. The real **BUILD** (the generator; its substrate — the schema registry, the engine/Violation model — already exists).

Mapping the investigation moves: **run / reconcile / loop / escalate = harness**; **enumerate / route / bind = generative gate** (all content-derived). Comprehension lives *only* in the gate — bounded, recorded, immediately frozen into a replayable check.

## Honest caveat (the guardrail)

This is *seductively* clean. The guardrail is CMS's own failure-test: a `measure` that is **not grounded in evidence** (or not fail-closed), or a `serialize` without provenance, is **decoration** — the narrative still reads as systematic while the verification rots back into semantic re-judgment (the #503 failure mode). Hold that line and the triad is the spine; drop it and it is a slogan.

---
type: design
title: The Generator — comprehend→author contract + per-phase synthesis
description: >-
  The one semantic step: how the agent reads an artifact's content and AUTHORS the frozen checks for it
  — selecting + parameterizing catalog kinds from what the work actually claims (the #503 class B/D fix:
  checks DERIVED from content, not hardcoded). Defines the authoring contract (a governed-writer step in
  the propose/plan/verify SKILLs), the per-phase synthesis rules (which targets get checks, and which
  kinds), and how this extends 12-phase-profiles. The agent's freedom is bounded to selection; the form
  it emits is the typed catalog (node 30); the run is deterministic (node 31).
tags: [verification, generative-gate, generator, synthesis, phase-profiles, authoring-contract]
timestamp: 2026-06-25
edges:
  - {dst: 10-generative-gate, rel: realizes, provenance: asserted}
  - {dst: 12-phase-profiles, rel: extends, provenance: derived}
  - {dst: 30-assertion-model, rel: depends_on, provenance: derived}
---

# The Generator — comprehend → author

This is the **one place a semantic act happens**: the agent reads the artifact's *actual content* and
authors the checks that would prove it. Everything downstream ([31](31-replay-engine.md)) is
deterministic. The generator's output is **not** code — it is a set of typed catalog entities
([30](30-assertion-model.md)) the agent SELECTED and PARAMETERIZED from the content. Its discipline:
derive the check from *what the work claims*, never a hardcoded template (the #503 class **B**/**D** fix).

## The authoring contract (a governed step, not a vibe)

Generation is a **governed-writer step** in the PROPOSE / PLAN / VERIFY skills, not an informal habit:

1. **comprehend** — for each target the phase owns (a `scope_item` at PROPOSE, a `work_unit` at PLAN, an
   obligation/claim at VERIFY), read its intent and classify it (does it *wire* a symbol? *set* a field?
   *satisfy* an obligation? *change* a behavior?). The classification is recorded as `from.basis`.
2. **author** — `uacp_entity_write` one `uacp.check.<kind>` per target, choosing the kind(s) its class
   *requires* (the floor — [34](34-adequacy-and-coverage.md)) plus any the agent judges necessary,
   parameterized from the content, with `from.target` = the target's node id (the `measured_by` edge).
3. **serialize** — the entity-writer validates against the schema + auto-registers it, so it projects as
   a `check` node and the replay engine + coverage gate see it. The agent never hand-writes a verdict.

Because authoring goes through the governed writer, the checks are watermarked, provenanced, and
graph-visible — the same trust path as every other manifest entity.

## Per-phase synthesis (extends 12-phase-profiles)

[12-phase-profiles](12-phase-profiles.md) already assigns each phase a measure-mode + authority. This
node fills in *what the generator emits per phase*:

| phase | targets | typical kinds it must author | binds against |
|---|---|---|---|
| **PROPOSE** | each `scope_item` (intent) | `field_present` (the intent is concretely stated), an *intent-class* check stub naming what PLAN must prove | the proposal graph |
| **PLAN** | each `work_unit` | the class-required kind: `symbol_resolves` for "wire X", `field_equals` for "set Y", `obligation_satisfied` for "ensure Z"; `edge_exists` for required coverage topology | graph + (later) code |
| **EXECUTE** | — | **no generation** (EXECUTE is excluded from authoring — [00](00-the-primitive.md)/[12](12-phase-profiles.md)); it produces the *evidence* the VERIFY checks bind to | — |
| **VERIFY** | each obligation / done-claim | `obligation_satisfied`, `artifact_integrity`, and (later) `behavioral` — the reality-binding pass | artifact + (later) behavior |

The PROPOSE→PLAN→VERIFY chain is itself a coverage chain of checks: a PROPOSE intent-class check names
what PLAN must prove; PLAN's check binds it to a symbol/field; VERIFY's check binds it to evidence. A
break anywhere is caught by the structural coverage gate ([34](34-adequacy-and-coverage.md)).

## What stops a lazy generator

Nothing in *this* node forces good faith — that is exactly why generation is **not trusted alone**. The
generator is bounded and checked by the three layers in [34](34-adequacy-and-coverage.md): structural
coverage (every target carries a check), the required-kinds floor (the class dictates the minimum kind,
so a "wire X" task cannot be "proven" by a `field_present`), and council default-to-refute on the
residual. The generator proposes; the kernel + council dispose.

## What is built vs new

- **Built / IMPROVISE:** the governed entity-writer (validate + watermark + auto-register); the
  PROPOSE/PLAN/VERIFY SKILL contracts (extend them with the authoring step); #503's narrow "propose emits
  executable assertions" precedent (generalize to every phase).
- **New (BUILD, slice 1):** the per-phase authoring contract text + the class→required-kind taxonomy the
  comprehend step uses; the SKILL-level instructions that make authoring a required PHASE output.

## To build (slice 1)

- Extend `skills/uacp-propose` / `uacp-plan` / `uacp-verify` with the authoring step + the
  class→kind taxonomy.
- A test that a phase whose target has NO authored check is blocked by the coverage gate (the producer
  side of [34](34-adequacy-and-coverage.md)).

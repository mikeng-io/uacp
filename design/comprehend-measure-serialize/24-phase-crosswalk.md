---
type: analysis
title: Phase cross-walk — the 7 lifecycle phases as CMS (the fractal, made concrete)
description: Proves node 23's fractal claim phase-by-phase. Each lifecycle phase plays ONE role in the macro loop yet is INTERNALLY a full comprehend→measure→serialize loop (its gate = its measure-discipline; its artifact = its serialize). The per-phase agent prompts (one file each, in prompts/) are derived from this table — they are the substance the portable uacp.md + the agent skill are written from.
tags: [primitive, crosswalk, fractal, lifecycle, prompts]
timestamp: 2026-06-24
edges:
  - {dst: 23-composition, rel: derives_from, provenance: derived}
  - {dst: 31-instantiations, rel: extends, provenance: asserted}
---

# Phase cross-walk — CMS made concrete for all 7 phases

The fractal claim (node 23) stated abstractly: *every phase runs CMS internally.* Here it is grounded for all seven, against the real artifact kinds + Heartgate gates (produced by a per-phase fan-out, 2026-06-24). This is the **coherence discipline ([00](00-the-axiom.md)) applied per-phase** — a design choice, not a discovered recursion — and the kernel **enforces** it at each phase-exit *gate*. Per-phase agent prompts live in [`prompts/`](prompts/) — one file each.

| Phase | Macro role | comprehend (input model) | measure (decidable signal + gate) | serialize (kind, via `uacp_entity_write`) |
|---|---|---|---|---|
| **brainstorm** | comprehend | vague/ungoverned idea → one bounded scope model | admissible to governance? — `brainstorm→triage` exit invariant | `uacp.brainstorm_scope_package` |
| **triage** | measure | request (or brainstorm scope) → scope/admission model | routing_outcome + track + granularity + council/human flags — triage artifact **and** `TRIAGE_COMPLETE` ledger | `uacp.triage` |
| **propose** | comprehend | triage verdict → first governance model (KEYED scope_items) | viability/admissibility — `PROPOSE→PLAN` gate (keyed scope shape at write) | `uacp.proposal` (+ `proposal_package_selection`, `intent`) |
| **plan** | measure | proposal → plan graph (`work_units` + `derives_from`) | plan sound+bounded+covered — `PLAN_VALIDATION` ledger + `plan_exit` graph_invariant | `uacp.phase_intent_verification_contract` (+ `scope`, `plan_package_selection`) |
| **execute** | serialize | frozen PIV contract → live runtime/worktree state | per-unit `result ∈ {pass,warn,block,deferred}` — `execute_exit` checkpoint-coverage | `uacp.execution_checkpoint` (one per work_unit) |
| **verify** | measure | execution record vs obligations → evidence graph | per-obligation verdict + resolve-readiness — `verify_exit` (GP_UNVERIFIED / GP_CONTRADICTED) | `uacp.piv_assessment` (+ `verification_package`, `verify_resolve_readiness`) |
| **resolve** | serialize | upstream readiness → closure picture | safely closable? + residual obligations — `VERIFY→RESOLVE` gate | `uacp.resolve_package` (+ `resolve_closure`, `lessons`) |

## The pattern (read honestly)

- **The macro loop is not a single tidy `C→M→S`.** The roles run `comprehend → measure → comprehend → measure → serialize → measure → serialize`: the lifecycle *iterates* comprehend/measure to refine intent (brainstorm→triage→propose→plan) before EXECUTE *serializes* it to reality, then VERIFY *measures* the result and RESOLVE *serializes* closure. That is CMS **iterated + nested** (node 23), not one flat triple — and it is the honest shape.
- **Every phase's GATE is its measure-discipline** — fail-closed, evidence-bound, judged by Heartgate (a separate authority), never the doer's say-so.
- **Every phase's ARTIFACT is its serialize** — typed, validated, watermarked, registered via the entity-writer (explicit, canonical, traceable).
- **EXECUTE is the one phase excluded from self-measurement** (no-self-attestation): it serializes *evidence*; VERIFY supplies the *verdict* EXECUTE cannot self-grant. This is the load-bearing asymmetry of the whole lifecycle.

## To expand
- The base case (finest grain): a single governed write = a CMS atom whose *measure* is the validate-on-write.
- Reconcile each prompt's wording against the live SKILL.md once the rename/promotion lands (the prompts cite real kinds, so they track the as-built).

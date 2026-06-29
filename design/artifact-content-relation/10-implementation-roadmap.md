# 10 — Implementation roadmap (gate-side B1)

The forward plan that turns [09-grounding-retarget-experiment](09-grounding-retarget-experiment.md)
into shipped governance. Scope = the **gate side** of B1 (prose-reading gates → claim-vs-witness).
The skill/transition side (lifecycle-executability breaks #2/#3) is a sibling initiative, not here.

## Cross-cutting invariant (holds in every phase)

> **Agent claims → independent witness derives the fact → code compares + blocks on mismatch.**
> Witness #1 codeflair = deterministic FLOOR (cannot be overridden). Witness #2 semantic =
> escalate-only CEILING (raises class, never lowers floor). Synthesis = `max(floor, ceiling)` vs
> declared, **in code, never an agent.** Correctness never excuses non-conformance — an out-of-scope
> but correct change is still a flag; the remedy is **re-declare** (amend PROPOSE/PLAN), not forbid.

## Phase 0 — Experiment ✅ DONE

Commit `da86643`. Gate retargeted to consume an `entailed_class` oracle; dark regression + restored
teeth + independence all proven; 2202 suite green. Oracle is test-injected. See node 09.

## Phase 1 — codeflair as the real oracle (MVP, detection-mode)

The smallest step that makes Phase 0 real and high-value. Three pieces:

1. **codeflair class-entailment (the new logic).** Today codeflair has edges / blast-radius /
   heatmap but does **not** entail a UACP class. Add a deterministic map *code-graph signal →
   class*: does the target's touched symbol get **wired in** (new route registration / mount /
   inbound edge)? → entail `wires_symbol`. This is feasible because wiring is an observable edge, and
   it is exactly the critical weak-vs-strong boundary (`sets_value` vs `wires_symbol`,
   `verification_floor.py`).
2. **crossplane write of `entailed_class`.** codeflair writes the entailed class onto the target
   node via the existing `code_anchor` / crossplane join. (Gate consumption already built in P0.)
3. **detection-mode wiring (EXECUTE→VERIFY).** Run after the diff exists, when there is a real symbol
   to parse — simpler than prevention. Mismatch (declared weaker than entailed) → `CHK_CLASS_UNDERCLAIM`.

**Exit measurement:** a real run where the agent under-declares wired work is caught by codeflair's
entailed class (not by prose), on a true diff, with the legacy prose path still green.
**Dependencies / risks:** codeflair class-entailment is net-new; crossplane adapter exists; assumes a
fresh index (codeflair delta-reindex/freshness is a known gap — see codeflair gap analysis).

## Phase 2 — prevention-mode (PLAN)

Same witness, earlier boundary. At PLAN/PROPOSE the agent declares its touch-set; codeflair computes
the **dependency closure** against the *current* graph (no new code needed). Claimed boundary ⊉
computed cascade → block **before** work starts. This is the prevention half of the same mechanism.
**Exit measurement:** a PLAN that claims a contained change to a high-fan-in symbol is blocked with
the real cascade as evidence.

## Phase 3 — semantic witness (escalate-only) — DEFERRED

For what codeflair structurally can't see: `changes_behavior` (runtime semantics) and pure-doc work
with no symbol. An independent reviewer or small embedded model produces the CEILING; stays
escalate-only so its non-determinism can't corrupt the floor. Home of the parked edge-LLM "Job 2 /
independence pre-screen." **Nice-to-have, lengthy — explicitly deferred** (operator decision).

## Phase 4 — generalise the pattern — DEFERRED to bundle rework + council

Apply claim-vs-witness to the other prose-reading gates the council named: D43
`_scope_concern_is_keyed`, `schema.py` `statement`-required, the evidence_disposition validator
([06-evidence-disposition-case](06-evidence-disposition-case.md)). This is the horizontal B1 rollout
— kernel + schema + lifecycle skills → **Invariant #4 council + cross-provider reviewer**, on the
additive ratchet of [05-migration](05-migration.md) (legacy prose stays valid; flip per-kind once
each gate's witness is proven; remove legacy last).

## Sequencing logic

P1 is the load-bearing build (proves codeflair can be the oracle at all); P2 reuses its entailment
at a different boundary; P3/P4 are deferred and gated on P1 succeeding. Each phase ships green and
additive — no cutover at any point.

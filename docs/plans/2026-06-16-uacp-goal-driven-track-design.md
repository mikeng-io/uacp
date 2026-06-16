# UACP Goal-Driven Track — Design

> **Status:** validated design (brainstorming complete). Next step is an implementation plan (superpowers:writing-plans). Design-only; no code in this doc.

**Goal:** Add a second *track* to the existing UACP lifecycle so that **semantic / exploratory** work (where the outcome is judged subjectively and attempts are disposable) is governable under the *same* phases — without forcing it through the forward-only, deterministic progression that fits 0→100 work.

---

## Problem

UACP's lifecycle assumes a single mode: linear 0→100. You move forward through TRIAGE→PROPOSE→PLAN→EXECUTE→VERIFY→RESOLVE one phase at a time, each phase anchored to the prior completing, and a mid-course change is treated as a deviation to re-authorize.

That fits **deterministic** work (migrations, contracts, security) where the target is known and rigor de-risks the path. It does **not** fit **semantic / exploratory** work — a landing-page hero section, a positioning statement, a conceptual data model, a research direction — where:

- the target is *discovered*, judged subjectively, not specified up front;
- early attempts are *disposable* ("by step 3 it's wrong; scrap it, start over");
- you frequently need to roll back to an earlier point rather than march forward.

Today that work either escapes UACP entirely — and then there is **no record of what changed, why, the evidence, the verdict, or the invariants** — or it fights the forward-only lifecycle. (Note: this is **not** UI-only. It is any work that is semantic rather than deterministic.)

---

## The idea (one paragraph)

Keep the existing lifecycle. **The five phases are golden and are reused unchanged.** TRIAGE selects a **track**. The two tracks differ in exactly **one** thing — the *transition discipline*:

- **Standard track** (existing, default): forward-only progression, anchored to the phase *sequence*. Unchanged behavior.
- **Goal-driven track** (new): anchored to the **goal**, not the sequence. Transitions may **roll back to a prior checkpoint**. A "build" is a **checkpoint** (a disposable probe toward the goal), *not* an impactful commitment — impact/commitment is **deferred until a checkpoint satisfies the goal**.

That is the whole of it. One framework, one phase set, two tracks; the only thing that varies is whether you must go strictly forward or may roll back to a checkpoint while staying anchored to the goal.

---

## The key move: swap *which* anchor binds

This is the conceptual core, in the operator's own framing:

- Today you are anchored to the **sequence** — go in order, no going back.
- Goal-driven, you are anchored to the **goal** — the sequence becomes a *space you can move through, including backward to a checkpoint*, as long as you are still serving the fixed goal.

The **goal is the invariant that does not move.** The phase order is what gets freed. "Decoupling the anchor" = decoupling the strict one-by-one progression requirement, and binding to the goal instead.

---

## What this is NOT (hard-won boundaries — do not re-derive these)

These were each explored and explicitly rejected; re-introducing them is the failure mode.

1. **NOT a second / forked lifecycle.** One framework, one phase set. A forked lifecycle is "another thing to manage" — the opposite of the intent.
2. **NOT a unification where the standard track is melted into "iteration with n=1."** The two tracks stay **distinct**. We do not collapse them into one mechanism.
3. **NOT a port of trustless ACP.** trustless ACP's loop is a *deterministic, post-implementation, findings→fix* correction loop (forward-only). That is a **different** loop. trustless is *evidence the pattern works in practice*, not a template to copy. UACP is the superior, generic, unified expression — not an import.
4. **NOT a rewind-tree / branching-topology state machine.** Roll-back is recorded as a manifest entry; it is not a live tree of compared branches.
5. **NOT a redesign of UACP into a "semantic" or "pre-implementation" system.** "Semantic" and "thematic" describe the *kind of work* the goal-driven track serves — not a new identity for UACP.

---

## Mechanism

- **TRIAGE selects the track.** Extend the existing TRIAGE routing to set a `track` field (alongside the existing `routing_outcome`). [Track names not finalized — see Open Items.]
- **PROPOSE declares the goal as the fixed anchor.** Success criteria are *semantic* (operator/defined satisfaction), not a fixed spec. PROPOSE sets the sandbox + authority + scope; the goal is the invariant the rest of the track serves.
- **Checkpoint = a recorded phase-state you can return to.** Rolling back = returning to a checkpoint and proceeding again, still toward the same goal.
- **Transition discipline is the only per-track difference (Heartgate-owned):**
  - Standard: forward-only.
  - Goal-driven: a transition may roll back to a prior checkpoint; the binding constraint is the goal, not the phase order.
- **Builds are checkpoints, not commitments.** A checkpoint is disposable. Heavy weight — impact, commitment, governance pressure — attaches to **the goal** and to **the moment of satisfaction**, not to every attempt. When a checkpoint meets the goal it is *promoted from checkpoint to result*, and VERIFY/RESOLVE close against the goal + manifest coherence.
- **Lightweight manifest (append-only) makes roll-back traceable.** One short entry per checkpoint: **what changed · why · evidence (the "see it" — render/screenshot/preview/sample) · verdict (keep / roll back / restart) · invariant (what must still hold).** This is the reason to do exploratory work under UACP at all: even when you scrap and restart, you retain what/why/evidence/verdict/invariant.

### Where an "unsatisfying outcome" goes (roll-back semantics)

The destination depends on *what* the dissatisfaction indicts; the goal-driven track makes this an explicit, recorded decision, not a vibe:

- **Goal right, approach right — the attempt was just weak → stay put; take another checkpoint** toward the same goal. Nothing was committed, so there is no "back." *This is the common case and the whole point of the track.*
- **Approach wrong → roll back to the PLAN checkpoint** (re-set the exploration rules / what is fluid). Recorded escalation.
- **Goal wrong → roll back to the PROPOSE checkpoint.** Rare, explicit, recorded.

The deciding question at each unsatisfying outcome: *"Is this fixable within what the plan left fluid?"* → yes: another checkpoint · no, approach wrong: PLAN · no, goal wrong: PROPOSE. The manifest verdict records which of the three, and why.

---

## What stays identical across both tracks

The phases, the artifacts, the governed writers, and the core invariants — **authority is explicit, side effects are declared/contained, writes are governed, claims are backed by evidence, no self-attesting closure.** Only the *transition discipline* and the *manifest obligation* differ. The goal-driven track is not "less governed" — it is differently shaped, and it adds a finer-grained (per-checkpoint) record stream on top of the existing per-phase artifacts.

---

## Non-goals

- No change to the **standard track's** behavior (must be provably unchanged — same production-equivalence bar used in the config-collapse slices).
- No new phases; no second lifecycle.
- No automated semantic judgment of "is this satisfying." The operator (human, or a defined criterion) judges; UACP **records**. UACP does not try to be the taste.

---

## Open items (resolve in the implementation plan)

1. **Track naming.** Working pair: `standard` vs `goal-driven`. Alternatives considered: directed/exploratory, deterministic/generative. Not finalized.
2. **Checkpoint + manifest schema.** Exact fields, storage location under `state/`, granularity, and how a checkpoint records the returnable phase-state.
3. **Validator relaxation per track.** Which validators stay vs relax for the goal-driven track. Instinct: authority / containment / no-fabrication **stay**; deterministic findings-clearing / PIV-style gates **relax** into the manifest obligation.
4. **Heartgate transition-rule representation.** How the transition validator (and `engines/domain/phase_graph.py`) encode "roll-back-to-checkpoint allowed" for the goal-driven track *without* making the standard track non-linear. (The standard track must stay strictly forward/acyclic.)
5. **Roll-back ↔ worktree/state interaction.** Returning to a checkpoint = restoring a recorded state; define how this composes with the worktree protocol and governed `state/` writers.
6. **Convergence / termination.** Operator sign-off as the exit; whether an iteration/spend budget bounds the checkpoint loop.

---

## Provenance note

This design was reached through a long brainstorming dialogue that repeatedly over-built (porting trustless ACP, unifying the tracks into one, inventing rewind topologies, reclassifying UACP as "semantic"). The kernel above is the de-scrambled result: **same lifecycle, golden phases reused; TRIAGE picks the track; the goal-driven track swaps forward-only progression for goal-anchored roll-back-to-checkpoint, with a lightweight manifest for traceability.** The "What this is NOT" section exists to prevent re-derailing.

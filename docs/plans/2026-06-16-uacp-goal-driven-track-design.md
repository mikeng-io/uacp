# UACP Goal-Driven Track — Design

> **Status:** BUILT and merged to main (2026-06-16). Implemented per the 9-task plan (`2026-06-16-uacp-goal-driven-track-implementation.md`); P2 resolved = option (b); 2-lens council cleared after resolving 2 MATERIAL findings. See ADR-0016. This design doc is retained as the as-designed record.

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

- **TRIAGE selects the track**, via a *mechanical* test (closes the escape-hatch risk): **"Is the success criterion specifiable as a verifiable artifact before EXECUTE begins?"** — yes → `standard`; no → `goal-driven`. The selection is recorded as a `track` field on the triage artifact (a canonical, validated location every downstream phase + Heartgate reads — track identity must not be inferred or stored out-of-band). [Track names not finalized — see Open Items.]
- **PROPOSE declares the goal as the fixed anchor.** Success criteria are *semantic* (operator/defined satisfaction), not a fixed spec. PROPOSE sets the sandbox + authority + scope; the goal is the invariant the rest of the track serves.
- **Checkpoint = a recorded phase-state you can return to.** Rolling back = returning to a checkpoint and proceeding again, still toward the same goal.
- **Per-track difference (updated by P2=(b)):** per-run transitions are **forward-only in BOTH tracks** — the phase graph is untouched. The goal-driven track differs by *(i)* a **persistent goal** that anchors a **chain of forward runs** (re-launch under the held goal = the "roll back"), and *(ii)* an **in-EXECUTE checkpoint manifest**. The binding constraint is the goal across the chain, not the phase order within a run. (The earlier "transition discipline / back-edge" framing applied to the rejected option A.)
- **Builds are checkpoints, not commitments.** A checkpoint is disposable. Heavy weight — impact, commitment, governance pressure — attaches to **the goal** and to **the moment of satisfaction**, not to every attempt. When a checkpoint meets the goal it is *promoted from checkpoint to result*, and VERIFY/RESOLVE close against the goal + manifest coherence.
- **Manifest (append-only, gate-ledger-backed) makes roll-back traceable — and is NOT an honor system.** Entries route through the existing `uacp_gate_ledger_append` writer (not a new one), and Heartgate runs the **same no-self-attestation check on checkpoint entries that it runs on standard-track phase transitions**. The `evidence` slot must reference an **externally verifiable artifact** (a committed render/screenshot/preview/sample path), not a prose description — this is the *structural claim⇒evidence coupling* enforcement finding applied here. This is the reason to do exploratory work under UACP at all: even when you scrap and restart, you retain a governed record of what/why/evidence/verdict/invariant.

  **Manifest entry schema (stub — `[schema TBD]`, promote in the plan):** `checkpoint_id` · `phase` · `what_changed` · `why` · `evidence` (verifiable artifact ref) · `verdict` (keep | roll_back | restart) · `invariant` (what must still hold) · `rolled_back_to` (checkpoint_id | null).

### Where an "unsatisfying outcome" goes (roll-back semantics)

The destination depends on *what* the dissatisfaction indicts; the goal-driven track makes this an explicit, recorded decision, not a vibe:

- **Goal right, approach right — the attempt was just weak → stay put; take another checkpoint** toward the same goal. Nothing was committed, so there is no "back." *This is the common case and the whole point of the track.*
- **Approach wrong → roll back to the PLAN checkpoint** (re-set the exploration rules / what is fluid). Recorded escalation.
- **Goal wrong → roll back to the PROPOSE checkpoint.** Rare, explicit, recorded.

The deciding question at each unsatisfying outcome: *"Is this fixable within what the plan left fluid?"* → yes: another checkpoint · no, approach wrong: PLAN · no, goal wrong: PROPOSE. The manifest verdict records which of the three, and why.

> **Per P2=(b):** "roll back to PLAN/PROPOSE" means **launch a new forward run under the same persistent goal, reusing that phase's prior output** — not an in-run rewind. The common case ("attempt weak") stays in-place inside one run's EXECUTE. The manifest chains the runs under the goal.

---

## What stays identical across both tracks

The phases, the per-run forward transition discipline, the artifacts, the governed writers, and the core invariants — **authority is explicit, side effects are declared/contained, writes are governed, claims are backed by evidence, no self-attesting closure.** Per P2=(b), what the goal-driven track *adds* (rather than changes) is: a **persistent goal** anchoring a **run-chain**, and an **in-EXECUTE checkpoint manifest**. The goal-driven track is not "less governed" — it is differently shaped, and it adds a finer-grained (per-checkpoint) record stream plus a cross-run goal link on top of the existing per-phase artifacts.

---

## Non-goals

- No change to the **standard track's** behavior (must be provably unchanged — same production-equivalence bar used in the config-collapse slices).
- No new phases; no second lifecycle.
- No automated semantic judgment of "is this satisfying." The operator (human, or a defined criterion) judges; UACP **records**. UACP does not try to be the taste.

---

## Council audit (2026-06-16, 3 Sonnet lenses) — verdict: kernel sound, not yet implementable

### Preconditions — MUST resolve before an implementation plan (elevated from "open item" to blocker)

P1. **Checkpoint semantics / state serialization (the #1 blocker).** "Return to a checkpoint" must specify *exactly what is restored vs preserved*: the `state/current.yaml` phase pointer, worktree git SHA (revert build commits or leave them?), scope-artifact version, the append-only gate-ledger (entries can't be erased → tombstone with a `rolled_back_by` pointer?), and the run-manifest `state_history` (preserved — it's the audit trail). Minimum viable definition: a checkpoint is a named `(phase, run-manifest snapshot, git SHA, gate-ledger length, scope-artifact version)` tuple, with a chosen+recorded policy for worktree commits. Until this is defined, roll-back has no stable operational meaning.

P2. **The roll-back MECHANISM — RESOLVED 2026-06-16: option (b).** "Roll back to PLAN/PROPOSE" is *a new forward run with the goal held constant and the prior PROPOSE/PLAN output reused* — NOT a graph back-edge and NOT an in-run state restore. Consequences, which materially de-risk the design:
  - **The phase graph is untouched.** Per-run transitions stay forward-only in *both* tracks; `LIFECYCLE_GRAPH` / `_transition_allowed` need no change. → **O3 dissolves** (no per-track back-edge allowlist needed).
  - **P1 shrinks drastically.** A "checkpoint" you roll back to is just a *reusable prior-phase output reference* (the frozen goal + the prior PROPOSE/PLAN artifact), not a restorable in-run state snapshot. No worktree-revert / gate-ledger-tombstone machinery for roll-back. The in-EXECUTE checkpoint remains a manifest entry (+ optional worktree marker).
  - **The kernel reframes:** the goal-driven track is realized as **(i) a persistent GOAL that anchors a chain of forward runs + (ii) an in-EXECUTE checkpoint manifest** — not as a "transition-discipline" change. The standard track = a single run whose goal is satisfied once. The one genuinely new construct is the *persistent goal that links a run-chain* (a goal-id in the run registry).

### Resolved in this audit (fold into the plan)

R1. **TRIAGE selection test** — mechanical ("success criterion specifiable as a verifiable artifact before EXECUTE?"). Recorded in Mechanism above.
R2. **Required convergence budget** — goal-driven runs MUST declare a budget (max checkpoints / spend / wall-clock) at PROPOSE; Heartgate blocks PROPOSE-exit if absent. Without it, an autonomous run (`claude -p`, cron, no human to sign off) is an infinite loop by design. Operator sign-off is the *interactive* exit; the budget is the *autonomous* exit.
R3. **Manifest is gate-ledger-backed + no-self-attestation + external evidence refs.** Recorded in Mechanism above.

### Remaining open items (resolve in the implementation plan)

O1. **Track naming.** Working pair `standard` vs `goal-driven`; alternatives directed/exploratory, deterministic/generative. Not finalized.
O2. **Validator relaxation per track.** authority / containment / no-fabrication **stay**; deterministic findings-clearing / PIV-style gates **relax** into the manifest obligation. (Coupled to the Hermes grounding-gate work item — see Provenance.)
O3. **Heartgate transition-rule representation.** Recommended shape (Lens 1, Option A): keep `LIFECYCLE_GRAPH` acyclic; the standard track keeps the existing DAG check unchanged; the goal-driven track consults a separate mode-gated `ROLLBACK_TRANSITIONS` allowlist — so the standard track stays provably linear. (Contingent on P2.)
O4. **"build" vs "checkpoint" naming** — canonicalize one term in the plan.
O5. **Promotion semantics** — what "promoted from checkpoint to result" requires at VERIFY (define "manifest coherence" so it isn't a lower bar than standard VERIFY).

---

## Provenance note

This design was reached through a long brainstorming dialogue that repeatedly over-built (porting trustless ACP, unifying the tracks into one, inventing rewind topologies, reclassifying UACP as "semantic"). The kernel above is the de-scrambled result: **same lifecycle, golden phases reused; TRIAGE picks the track; the goal-driven track swaps forward-only progression for goal-anchored roll-back-to-checkpoint, with a lightweight manifest for traceability.** The "What this is NOT" section exists to prevent re-derailing.

**Origin / coupling:** this design spun off from a separate queued work item — a **Hermes "grounding gate"** (hard enforcement that catches/blocks ungrounded final answers). The connection is load-bearing: the trustless-ACP grounding exploration done during this design found that robust grounding enforcement is **structural claim⇒evidence coupling checked deterministically** (trustless has *no* response-text LLM judge), which is exactly what shapes O2 (validator relaxation) here *and* the Hermes work item. The full reasoning + the rejected-detour arguments + the trustless dossier are preserved in **ADR `docs/architecture/0016-goal-driven-track.md`** and **`docs/decisions/decision-log.md` (2026-06-16)** — leaving them only in chat would itself be the self-attesting closure UACP forbids.

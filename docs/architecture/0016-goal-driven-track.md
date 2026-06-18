---
type: adr
title: Goal-driven track — second lifecycle track for semantic/exploratory work
description: Add a goal-driven track alongside the standard track so semantic/exploratory work is governable under the same lifecycle without forking the phase graph.
tags: [goal-driven, lifecycle, tracks, exploratory]
timestamp: 2026-06-16
status: accepted
---

# Goal-Driven Track: A Second Lifecycle Track for Semantic / Exploratory Work

## Metadata

- **Status**: accepted — BUILT and merged to main (2026-06-16). 9-task implementation, two-stage-reviewed per task + a 2-lens council; both MATERIAL council findings (M-1 cross-chain cap evasion, M-2 forgeable track) resolved. Standard track provably byte-identical; suite 604/2.
- **Date**: 2026-06-16
- **Decision Makers**: UACP maintainer
- **Consulted**: 3-lens Sonnet council (architecture/governance, devil's-advocate, capture/traceability)
- **Informed**: TRIAGE, Heartgate, lifecycle, and state-mutation skills
- **Related**: design doc `docs/plans/2026-06-16-uacp-goal-driven-track-design.md`; decision-log entry 2026-06-16; the queued Hermes "grounding gate" work item

## Context and Problem Statement

UACP's lifecycle assumes a single mode: linear 0→100. You move forward through TRIAGE→PROPOSE→PLAN→EXECUTE→VERIFY→RESOLVE one phase at a time, each phase anchored to the prior completing, and a mid-course change is treated as a deviation to re-authorize.

That fits **deterministic** work (migrations, contracts, security) where the target is known and rigor de-risks the path. It does **not** fit **semantic / exploratory** work — a landing-page hero, a positioning statement, a conceptual data model, a research direction — where the target is *discovered* and judged subjectively, attempts are *disposable*, and you frequently scrap and restart. Today such work either escapes UACP entirely (losing the record of *what changed, why, the evidence, the verdict, the invariants*) or fights the forward-only lifecycle.

UACP is the generic, unified successor of the (proven but sprawling) **trustless ACP**; the goal here is to express this capability in UACP's own terms, not to port trustless.

## Decision Drivers

- One framework, less to manage: reuse the existing five phases (they are "golden"); do not fork a second lifecycle.
- Keep the two work-modes **distinct** (do not melt them into one mechanism).
- Preserve UACP's core invariants in both modes: authority explicit, side-effects declared/contained, governed writers, evidence/no-fabrication, no self-attesting closure.
- The standard (linear) track's behavior must be **provably unchanged** (same production-equivalence bar as the config-collapse slices).

## Considered Options (with rejection reasoning — the hard-won boundaries)

1. **Forked second lifecycle** — *rejected.* A separate state machine + gate set + mental model is "another thing to manage" forever; every future change must be made twice. The opposite of UACP's reason to exist (unify trustless ACP's sprawl).
2. **Unifying generalization — one mechanism where "linear" is iteration with n=1** — *rejected.* Collapsing the two modes into one melts away the distinctness that the tracking is *for*; it repeatedly led the design astray ("scrambling everything back into one piece"). The two modes must stay two.
3. **Port trustless ACP's loop** — *rejected.* trustless's loop (`auto-orchestrate`) is a **deterministic, post-implementation, findings→fix correction loop** — forward-only, it *corrects*, it never *rewinds*. That is a different loop than the *thematic, pre-commitment, goal-driven* one needed here. trustless is **evidence the pattern works in practice, not a template to copy**; UACP is the generic expression.
4. **Rewind-tree / branching-topology state machine** — *rejected* as the modeling primitive. The traceability need is met by a recorded manifest, not by a live tree of compared branches. (Note: the council showed roll-back still implies *some* back-edge semantics — see Decision Outcome / precondition P2 — but not a live comparison tree.)
5. **Reclassify UACP as "semantic" / "pre-implementation"** — *rejected.* "Semantic/thematic" describes the *kind of work* the new track serves, not a new identity for UACP. UACP records; it does not become the taste.
6. **Two tracks, same phases, differing only in transition discipline** — **chosen.** See below.

## Decision Outcome

Add a **goal-driven track** alongside the existing **standard track**, both under the one lifecycle:

- **The five phases are reused unchanged.** TRIAGE selects the track via a mechanical test: *"Is the success criterion specifiable as a verifiable artifact before EXECUTE?"* — yes → standard; no → goal-driven. The choice is a validated `track` field on the triage artifact.
- **The anchor swaps.** Standard = anchored to the phase *sequence* (forward-only). Goal-driven = anchored to the **goal** (the invariant that does not move); the phase order becomes a space you can move through, including backward to a checkpoint, while serving the goal.
- **Builds are checkpoints, not commitments.** A checkpoint is a disposable probe toward the goal; impact/commitment is deferred until a checkpoint *satisfies* the goal, at which point it is promoted to result and VERIFY/RESOLVE close.
- **Per-track difference (per P2=(b), below): per-run transitions are forward-only in BOTH tracks — the phase graph is untouched.** The goal-driven track differs by adding *(i)* a **persistent goal** that anchors a **chain of forward runs** (re-launching a run under the held goal *is* the "roll back") and *(ii)* an **in-EXECUTE checkpoint manifest**. No back-edges, no per-track transition allowlist. The standard track = a single run whose goal is satisfied once.
- **A gate-ledger-backed, append-only manifest** records each checkpoint (what/why/evidence/verdict/invariant), with no self-attestation and externally-verifiable evidence refs — the structural claim⇒evidence enforcement applied at the checkpoint boundary.

### The grounding / enforcement finding (load-bearing, preserved here)

During this design we audited trustless ACP's enforcement (`/Users/mike/Workplace/trustless`). Findings worth preserving:

- trustless enforces via **deterministic `.claude/hooks`**: `guard-phase-complete.py` (a phase can't be marked complete without a git commit — a hard `exit 2` block, built after an incident where 10 phases were "completed" with 0 files); `safety-phase-piv.py` (per-task PIV requires an `output_hash` proof, re-run if missing); verify-read-only-revert; state-authority guard.
- **Crucially, trustless has NO response-text-level grounding judge.** Grounding is enforced **structurally** — a *claim* requires an *evidence artifact* (commit, `verified-facts.md`, PIV hash). A semantic LLM judge is, at most, augmentation.
- This is why the goal-driven manifest is gate-ledger-backed with verifiable evidence refs (not prose), and why O2 (which validators relax) must keep the structural coupling. It is also the central input to the **Hermes grounding-gate** work item.
- Honcho is *not* a fit for per-checkpoint evidence (it is session-level user memory — peers/observations→conclusions); loop/checkpoint state belongs in governed `state/`.

### Preconditions before implementation (from the council)

- **P1 — checkpoint state serialization** must be fully defined (what a checkpoint restores vs preserves: phase pointer, worktree SHA, scope-artifact version, gate-ledger tombstoning, run-manifest history). Until defined, roll-back has no stable operational meaning.
- **P2 — RESOLVED 2026-06-16: option (b).** "Roll back to PLAN/PROPOSE" = *a new forward run with the goal held constant and the prior phase output reused* — not a back-edge, not an in-run state restore. This **dissolves the phase-graph mutation entirely** (no back-edges; per-run transitions stay forward-only in both tracks) and **shrinks P1**: a "checkpoint" is a reusable prior-phase output reference, not a restorable in-run state snapshot. The remaining new construct is the **persistent goal that links a run-chain** (a goal-id in the run registry); P1 reduces to defining the in-EXECUTE checkpoint manifest entry + how a run inherits a goal + prior output.
- **R2 — a convergence budget is required** for goal-driven runs (max checkpoints / spend / wall-clock), Heartgate-enforced at PROPOSE-exit, because operator sign-off is not an exit in an autonomous run.

## Consequences

- **Positive:** semantic/exploratory work becomes governable under the same lifecycle, with a traceable record across restarts; the standard track is untouched; one framework, not two.
- **Negative / risks:** the goal-driven track adds a denser (per-checkpoint) record stream; mislabeling work as "goal-driven" to dodge rigor is a real risk (mitigated by the mechanical TRIAGE test + Heartgate-enforced budget + non-self-attesting manifest); checkpoint/roll-back semantics are non-trivial and gate the implementation (P1/P2).
- **Standard track:** provably unchanged (production-equivalence bar).

## Status / next step

Proposed. Next: the operator resolves P2 (roll-back mechanism); then an implementation plan (superpowers:writing-plans) that specifies P1, O1–O5, and the per-track Heartgate transition rule. No code until P1/P2 are resolved.

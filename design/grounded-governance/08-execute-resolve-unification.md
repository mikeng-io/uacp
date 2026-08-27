---
type: design
title: "EXECUTE and RESOLVE: completing the grounding already half-present"
description: "The two phases that already carry half the machine. EXECUTE grounds the checkpoint's claimed work against the real worktree diff (diff-coverage, largely built); RESOLVE grounds the closure's claims against the run's real evidence residue (evidence-must-resolve, Invariant 5). Neither needs a new substrate — the work is to unify them under the per-phase frame and close the remaining gaps."
tags: [grounded-governance, execute, resolve, diff-coverage, evidence, unification]
timestamp: "2026-08-24"
edges: [{dst: 04-grounding-is-per-phase, rel: depends_on, provenance: derived}]
---
# EXECUTE and RESOLVE: completing the grounding already half-present

Unlike TRIAGE/PROPOSE/PLAN (pure declaration-checks today), EXECUTE and RESOLVE already carry *half*
the machine. Their nodes are short because the substrate producers exist; the work is unification and
gap-closing, not new construction.

## EXECUTE — the checkpoint against the real diff

**Declaration:** the execution checkpoints — the account of what was done, and the `write_paths` it
claims to have stayed within.
**Reality:** the actual worktree diff (the git witness).
**Already present:** EXECUTE→VERIFY is guarded by checkpoint/diff-coverage (the work-unit status gate,
and M3c's `SC_DIFF_OUT_OF_SCOPE` comparing the real change set to declared `write_paths`). The behavior
half is M3a — a code-touching change must carry a behavioral check that *ran*.
**The gap under the frame:** these grounds exist but as separate gates, not as one "the checkpoint's
claimed work == the real diff" statement. Unification: state EXECUTE grounding as the single claim —
*every path the checkpoint says it wrote resolves in the real diff, and every path in the real diff is
claimed* — with the two halves (coverage + no-orphan-writes) as its faces. The producers (git witness,
behavior_plane) are already built; this is consolidation, and it is the phase closest to done.

## RESOLVE — the closure against the real evidence residue

**Declaration:** the closure — "done", the lessons, the disposition of every finding.
**Reality:** the run's real evidence residue — the artifacts, ledger entries, and dispositions the run
actually produced.
**Already present:** Invariant #5 (evidence must be produced; no self-attesting closure) and the M2
evidence-reference type (a closure's proof pointers must *resolve*, not merely be named) and the M3d
rework-cap breaker (open findings need discharge or adjudication). RESOLVE is where the whole floor's
"resolves, not asserts" rule already bites hardest.
**The gap under the frame:** RESOLVE should state one claim — *every obligation the run opened is
closed by evidence that resolves against reality* — with M2/M3d as its mechanism. The remaining work is
completeness: ensure the closure's obligation set is derived from the run's real opened obligations
(the manifest's `deferred_items` / `next_phase_obligation`, already replayed by M4's `next` block), not
from the agent's list of what it chose to close.

## Why these two are one node

Both are **deterministic** grounds over substrates that already have producers (the git witness; the
manifest/ledger). Neither needs a semantic screening — the checkpoint-vs-diff and closure-vs-residue
comparisons are hard-edged. The value of naming them here is completeness: with EXECUTE and RESOLVE
stated as instances of the machine, all six governed phases are covered, and the grounded-governance
thesis is closed — *at every governed crossing, the declaration is checked against a kernel-produced
reality, and cannot self-attest around it* — from the head of the cascade (TRIAGE) to its close
(RESOLVE).

## Build implication

EXECUTE/RESOLVE come **last** in the build order (`04`): they are mostly re-statement + gap-closing of
grounding that already ships, so they carry the least risk and the least new code. The build effort
concentrates where the gap is real — TRIAGE (`05`), PROPOSE (`06`), and the PLAN code-plane wiring
(`07`).

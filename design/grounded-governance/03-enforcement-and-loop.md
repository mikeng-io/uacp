---
type: design
title: "Enforcement and the loop: a mandatory, grounded VERIFY sub-step"
description: "The gate that makes the screening non-skippable: VERIFY cannot exit unless a correctness-screening artifact exists, resolves, and covers the kernel-produced substrate for the run's true range. Findings flow into the existing disposition grounding (M2/M3d); re-review is scoped to the fix delta and loops to a clean round, the fixpoint that terminates."
tags: [verify, enforcement, gate, disposition, fixpoint, grounded-governance]
timestamp: "2026-08-24"
edges: [{dst: 02-the-screening-dispatch, rel: extends, provenance: asserted}]
---
# Enforcement and the loop: a mandatory, grounded VERIFY sub-step

## The gate: screening is not optional, and its claim must resolve

A new VERIFY engine — the correctness-screening floor — blocks the VERIFY→RESOLVE crossing unless:

1. a **screening artifact exists** for this run, and
2. it **resolves** (run-bound + loads) exactly as M2 requires of any evidence-bearing pointer, and
3. it **covers the kernel-produced substrate** — the screening references the substrate identity for
   the run's true `merge-base..HEAD` range (`01`), so a screening of *some other* diff cannot clear.

This is the enforcement half Superpowers lacks: a fail-open prose instruction ("please review the
diff") can always be skipped; a gate keyed on a resolving, substrate-covering artifact cannot. It is
the exact shape the floor already uses (M2/M3a): the claim ("I screened the work") validates on the
artifact's *resolution against reality*, never on its presence or the agent's word. Migration follows
the M3 precedent — land config-gated at `warn`, flip to `block` in a named release — so live runs are
not broken the day it ships.

## Findings reuse the disposition grounding, not a new store

A screening finding is a carried finding. It flows into the **same disposition machinery** the rework
floor already grounds (`rework_completeness`): every open correctness finding must be *discharged* (a
fix whose pointer resolves — M2) or *adjudicated* (decision + rationale + cost-if-wrong — M3d), **recorded as a well-formed canonical
disposition** — at the rework cap the OR is AND: an adjudication on a *malformed* record does not
discharge (matching `#149` fail-closed-on-malformed); and
an undischarged, unadjudicated finding **blocks**. No parallel correctness-only ledger: the same
"a claim of the form 'X is handled by Y' validates only on Y's resolution" rule that M2 generalized
applies to correctness findings unchanged. This is why the floor was built first — Layer 2's verdicts
land in structure that already grounds them.

## The loop terminates by re-screening the fix delta

Review is a fixpoint, not a step (a fix mutates the global delta; a fix can introduce a new defect —
the don't-review-a-fix-into-a-new-defect rule). So on any fix in response to findings:

- the substrate is **re-produced** (the diff moved; `01` recomputes from the new HEAD), and
- the screening **re-runs scoped to the changed delta** plus any finding it interacts with, and
- the loop continues until a **clean round** — a screening pass with no new P1 over the current diff.

Termination is the clean round, not a fixed count: an attempt counter would stop at the tail where
the subtle defects live. The rework-cap breaker (M3d) is the backstop — if the loop cannot converge
within the cap, each still-open finding needs an explicit adjudication or VERIFY blocks. Convergence
or adjudication; never a silent give-up.

## What "done" now means

With this gate, "VERIFY passed" stops meaning "the declarations are grounded" and starts meaning
"the real work was read for undeclared defects by an external witness, over kernel-produced material,
and every defect it found was fixed-and-resolved or explicitly adjudicated." That is the conformance
loop closed on *reality* — the product (coherence, claims bound to evidence) the whole machine exists
to manufacture, finally covering correctness and not only conformance.

## Build order

1. **Substrate production** (`01`) — `gitio.diff_content` + the governed `review-substrate` artifact +
   its producer at VERIFY entry. Deterministic, testable now.
2. **The screening gate** (this node) — the new VERIFY engine: exists + resolves + covers-substrate,
   config-gated `warn`→`block`. Deterministic, testable now; the enforcement that makes the rest bite.
3. **The dispatch** (`02`) — the council-based screening skill: charge, probes, typed output. The
   agent-facing content that rides on the enforced substrate.
4. **The loop** — wire findings into disposition + scoped re-screening. Reuses M2/M3d.

Slices 1–2 are the floor for Layer 2 (produce the substrate, make the screening non-skippable) and
are built the same grounded, TDD way as M1–M5; slice 3 is the semantic content; slice 4 closes the
fixpoint.

---
type: design
title: "Screening, enforcement, and where every piece slots"
description: "A screening = a review agent passing the substrate through its attention until defects precipitate — improvised, grounded, not rubric-bound. The council is the screening framework; the deterministic floor makes both substrate and screening non-skippable (the enforcement Superpowers lacks). Maps M2/M3/council/kernel-diff onto substrate-production vs screening."
tags: [verify, screening, council, enforcement, superpowers, defect-lane]
timestamp: "2026-08-24"
edges: [{dst: 00-the-substrate-principle, rel: extends, provenance: asserted}]
---
# Screening, enforcement, and where every piece slots

## What a screening is

A **screening** is a review agent passing the substrate through its attention until whatever is wrong
**precipitates**. It is:

- **improvised** — the agent constructs the input that defeats the work (point a symlink at the path;
  split a multibyte char at the read boundary; clone clean and look for the gitignored artifact). No
  fixed checklist enumerates these; the defeating input is specific to *this* material.
- **grounded** — every claim binds to the substrate (the diff, the run output, the real file), not to
  the author's account. "Reproduce, don't read": an unexecuted reading cannot block or clear.
- **not pre-judged** — the dispatch never tells the screener what to ignore or cap. The moment you
  write "don't flag X" or hand it a rubric, you have re-pre-digested the work.

A "dimension" (correctness, security, compliance) is not a role assigned to the substrate — it is what
a screening **surfaces**. The same substrate, screened, precipitates different classes; the Code
Review Rules (`AGENTS.md`) are the *charge* a screening runs under, not a rubric of expected findings.

## Enforcement: why UACP, not Superpowers, and why the floor exists

Superpowers gets the object right — its reviewer reads the **diff as a file**, forbidden to be steered
— but ships **zero enforcement**: nothing forces the screening to run, and nothing produces the
substrate. UACP has the enforcement machinery (gates, governed writers, the council) and today points
it at the wrong object (the declaration).

So the two halves are distinct and both required:

- **Substrate + screening** — the *content* of a real review (take this from Superpowers / Codex / the
  defect-lane design).
- **Enforcement** — the *floor* that (a) makes the substrate **exist and be grounded** and (b) makes
  the screening **non-skippable**. This is what a fail-open prose instruction can never be.

The floor is not the review. It is what stops the review from being optional.

## Where every piece slots

| Piece | Layer | Role under this frame |
|---|---|---|
| **M2** — evidence-reference type (built) | floor / substrate-production | a claimed fix must *resolve*; grounds the conformance screening's material |
| **M3** — behavioral floor (in progress) | floor / substrate-production | witnessed diff touches code ⇒ force a behavioral check to **run**, producing reality-run output as substrate |
| **Kernel-produced diff** from true commit range | substrate-production | the primary substrate; must be kernel-made, never agent-nominated |
| **Promote `SC_DIFF_*`** warn→block (migration) | floor / substrate-production | make the git witness bind — containment as a fact the screening trusts |
| **The council** | screening framework | the agent-dispatch mechanism a screening runs on |
| **Correctness dimension** (the "defect lane") | screening | an agent screening the substrate for undeclared defects — open-adversarial, not finding-driven |
| **Security / compliance / deploy-safety** | screening (later) | further screenings over the same substrate — the full-dimensional set |
| `witness_class` / keyword classification | **rejected** | pre-digests the substrate into a label; a structural proxy for the judgment a screening must do |

## The one non-negotiable

VERIFY must **produce and expose a grounded substrate**, and **force at least one screening over it**.
Everything else — which screenings, how many dimensions, how they dispatch — is composition over that
invariant. Miss the substrate and every screening is theatre; miss the enforcement and the screening
is optional prose. UACP already has the enforcement; this frame points it at producing the substrate
and running the screening, which is the delta between a verify that checks paperwork and one that
verifies the work.

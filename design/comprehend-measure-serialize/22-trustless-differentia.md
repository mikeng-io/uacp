---
type: analysis
title: The Differentia — coherence + the discipline on each verb
description: Information-processing pipelines are common; UACP's distinction is two things — COHERENCE (one discipline imposed on every layer so they cannot drift) and the DISCIPLINE on each verb (fail-closed measure, provenanced serialize, governed routing). Without these, CMS is a slogan; with them, a re-derivable, coherent computational model.
tags: [coherence, differentia, governance, discipline, re-derivable]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: extends, provenance: asserted}
---

# The Differentia — coherence + discipline

"Context → state" describes *any* pipeline — ETL, a logger, a RAG stack. So CMS needs its **differentia**: what makes UACP's instance more than a pipeline. Two parts.

## Part 1 — Coherence (the architectural differentia)

The same discipline — comprehend → measure → serialize — is imposed on **every layer**: the governance lifecycle, semantic execution, and the LLM's cognition ([25-enforcement-surfaces](25-enforcement-surfaces.md)). A generic pipeline disciplines one layer (its data flow). UACP disciplines all three with *one* invariant, so they cannot drift: the agent reasons the way the gates govern the way execution commits. That coherence — not novelty — is the point. It is also why "is CMS a discovered law?" is the wrong question: it is a *chosen* unifying discipline, justified by the consistency it buys, not by being empirically true (so "retrofitted" is not an objection — you do not retrofit a choice).

## Part 2 — Discipline on each verb (the per-verb differentia)

- **measure is deterministic + fail-closed** — a decidable signal that can fail for the right reason, never a weak proxy (a `grep` standing in for "it works");
- **serialize is provenanced** — a typed key tracing to its source, verifiable mechanically forever;
- **routing is governed** — policy-decided by an authority *separate from the doer* (no-self-attestation, [21-decision-hinge](21-decision-hinge.md)).

## The load-bearing claim

> The discipline IS the engineering. A `measure` that isn't deterministic, or a `serialize` without provenance, is **decoration**: the narrative reads systematic while the result rots back into semantic re-judgment.

So the principle is *not* "everything is CMS" (true but vacuous); it is "**one discipline holds every layer coherent, and trustworthiness is exactly the discipline on the three verbs.**"

## Consequence

UACP = a **re-derivable, governed, coherent information-processing architecture**. *Re-derivable* = no actor (including the producing agent) is trusted; every claim is mechanically reconstructable. That is the line between a foundational model and a tautology. The disciplines must be **enforced** — architecturally where the layer allows, and by prompt-injection on the cognition layer that infra cannot reach ([25-enforcement-surfaces](25-enforcement-surfaces.md)). An enforced-nowhere principle is the decoration it warns against; the cognition surface's enforcement (the injection) is a *build task*, not a deferral.

## To expand
- The failure modes when a discipline is dropped (the #503 taxonomy, one per verb).
- Which disciplines are mechanized vs normative (the split in [25-enforcement-surfaces](25-enforcement-surfaces.md)).

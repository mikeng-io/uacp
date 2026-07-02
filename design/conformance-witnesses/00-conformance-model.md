---
type: analysis
title: "The Conformance Model — layers, witnesses, and the correctness asymptote"
description: "Defines UACP as a conformance architecture: every gate checks whether layer N conforms to layer N-1, never whether N is correct. Progress is converting layers from self-attested to independently witnessed. Names the witness independence classes."
tags: [conformance, witness, gate, architecture, model]
timestamp: 2026-07-03
edges: []
---
# 00 — The conformance model

## The claim UACP can actually make

No gate in UACP verifies that work is **correct**. Correctness means
conformance-to-intent, and intent has no independent witness — the only record
of intent is what the agent itself serialized. That makes correctness an
**asymptote**: approachable, never reached. What a gate CAN decide is
**conformance**: *does layer N conform to layer N-1?*

- EXECUTE conforms to PLAN (the diff stayed inside the declared boundary),
- PLAN conforms to PROPOSE (the plan realizes the declared intent's checks),
- evidence conforms to claim (the ledger entry has a backing artifact),
- serialized state conforms to schema (writers validate, gates re-derive).

Each of those is decidable *given a trustworthy account of both layers*. The
architecture question is therefore not "how do we verify correctness" but
"**who witnesses each layer?**"

## Witness independence classes

A layer's account of itself can come from three kinds of witness, in strictly
increasing trust:

| Class | Definition | Example |
|---|---|---|
| **self-attested** | The agent that did the work also produced the only record the gate reads. The gate measures a claim against a claim. | `entailed_class` on a check manifest — agent-written, agent-graded (`manifest/projection.py::validate_class_underclaim`) |
| **LLM-independent** | A *different* model/provider derives its own account; the gate compares provenance-checked accounts. Semantic, non-deterministic, but no longer self-grading. | cross-provider council review; the generative gate's independent lens |
| **deterministic** | Code derives the account from ground truth with no model in the loop; the gate compares claim vs derived fact. | git diff vs declared `write_paths`; codeflair symbol graph vs declared touch-set |

The **ratchet** is one-directional: a layer converts self-attested →
LLM-independent → deterministic, never back. Not every layer can reach
deterministic (semantic adequacy of a proposal cannot be computed), and that
is fine — the model demands each layer sit at the *highest class available to
it*, and that the class be **declared, not implied**.

## The guardrail

"Conformance architecture" is a name that is **earned by shipping witnessed
layers, not declared**. A scoreboard row may only claim a class when the
witness is merged, exercised by tests, and its bypass surface has been
adversarially reviewed. Until then the row stays at its honest current class.

## Division of labor with the structural witness

Codeflair is the deterministic **structural** witness: it grounds *structure*
(what symbols exist, what references what, what a change cascades into) and
never *meaning*. Pairing rule (CF-D9): the kernel must never import the code
plane — the seam is an injected value or a produced artifact the gate reads.
Which layers it can witness, and in what order they convert, is the
scoreboard's job (next node).

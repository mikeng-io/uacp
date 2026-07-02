---
type: design
title: "The Witness Scoreboard — layer inventory and conversion order"
description: "Owns the scoreboard MODEL: the row schema (layer, gate, witness, independence class, conversion target) and the seeded as-built inventory. The LIVE state lives on the program board's Scoreboard view; this node is the model, never a second copy of the state."
tags: [conformance, witness, scoreboard, inventory, design]
timestamp: 2026-07-03
edges:
  - {dst: 00-conformance-model, rel: realizes, provenance: asserted}
---
# 01 — The witness scoreboard

## What this node owns (and what it must not)

This node owns the **model** of the scoreboard: what a row is, what the
columns mean, what evidence a class claim requires, and the seeded inventory
below. The **live state** — which layer sits at which class *today*, what is
in flight — lives on the program board's Scoreboard view (group by Witness
class). One owner per fact: when a conversion merges, the *board* row moves;
this node changes only if the *model* changes. A duplicated status table here
would rot within one iteration (the propagation-loop failure mode).

## Row schema

A scoreboard row is:

```
layer            what conformance question this gate decides (N vs N-1)
gate             the code that decides it (engine / validator, file-anchored)
witness          who produces the account of layer N the gate reads
class            self-attested | LLM-independent | deterministic  (per 00)
target           the class this layer can reach, and via what witness
```

Class-claim evidence bar (from 00's guardrail): merged witness + teeth tests
(the check fires on a corrupted fixture) + an adversarial bypass review.

## Seeded inventory (as-built, 2026-07-03)

Snapshot at authoring time to seed the board — the board is authoritative
from here on.

| Layer | Gate (as-built anchor) | Witness today | Class today | Target |
|---|---|---|---|---|
| Scope / boundedness | `engines/scope_conformance.py` | agent's own `write_paths` declaration, cross-checked only against its own mirrors (scope artifact vs registry vs manifest) | self-attested (deterministically cross-checked) | **deterministic**: git diff (actual writes) + codeflair cascade vs declared touch-set — the named next conversion |
| State/serialization integrity | `engines/coherence.py`, `engines/ledger_integrity.py`, `engines/artifact_integrity.py` | governed writers' own outputs, re-derived by independent read-path code | deterministic (within the writer trust boundary) | hold; boundary documented |
| Evidence presence (VERIFY) | `engines/evidence_completeness.py`, `engines/deferral_completeness.py` | artifacts the agent produced; gate checks presence/shape, not truth | self-attested content behind a deterministic shape check | LLM-independent (independent reviewer grounds evidence-vs-claim) |
| Verification strength | `engines/manifest/projection.py::validate_class_underclaim` | agent-supplied `entailed_class` (forgeable; today test-injected) | self-attested | deterministic via codeflair-derived class (issue #87, after Scope proves the seam) |
| Plan/graph closure | `engines/graph_projection.py` + manifest projection | declared relations projected and swept deterministically | deterministic over declared relations (relations themselves self-attested) | deterministic: codeflair edges as independent relation source |
| Semantic soundness (PLAN/PROPOSE) | council review + generative gate | reviewer models; cross-provider required | LLM-independent | asymptote — highest class available; never claim more |
| Doc/design structure | `engines/domain/design_lint.py`, OKF lints | code reads the artifacts directly | deterministic | hold |

Two honest subtleties the columns force into the open:

- "Deterministic gate" ≠ "deterministic witness". Scope's gate is
  deterministic code, but every input it compares is the agent's own
  declaration — the row is **self-attested** until an account of *actual*
  behavior (diff, graph) arrives from outside the agent.
- Rows above the writer trust boundary (state integrity) are deterministic
  only because governed writers are the sole write path; that assumption is
  part of the row and breaks if raw writes bypass the writers.

## Conversion order

Next conversion: **Scope / boundedness** (epic #80, issue #82) — chosen
because ground truth is cheap and unambiguous (git knows the diff; the symbol
graph knows the cascade), the payoff is Invariant-#2-adjacent, and it forces
the witness seam (CF-D9-clean artifact handoff) that Verification strength
(#87) then reuses. Prevention-at-PLAN (#86) follows only after the
detection-at-VERIFY witness has proven the seam on real runs.

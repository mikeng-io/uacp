---
type: design
title: "The screening dispatch: an adversarial read over the substrate, charged not scripted"
description: "How the correctness screening runs: a council dispatch over the review substrate, charged by the Code Review Rules, given writable-scratch mutation probes (behavior_plane), told to construct the input that defeats the work — never handed a checklist of what to find. Produces typed findings plus an honest 'cannot verify from diff' when the substrate is insufficient."
tags: [verify, screening, council, code-review-rules, behavior-plane, anti-pre-judging]
timestamp: "2026-08-24"
edges: [{dst: 01-the-review-substrate, rel: depends_on, provenance: derived}]
---
# The screening dispatch: an adversarial read over the substrate

## Reuse the council; it is already the dispatch framework

UACP already has the machinery to dispatch a semantic actor over material and synthesize its output:
`skills/uacp-council/` (registration → routing → domain-planning → dispatch → synthesis → artifact),
including a **finding-driven mode**. The screening is a council dispatch whose *material* is the
review substrate (`01`) rather than a design narrative, and whose *charge* is correctness. No new
orchestration is invented; what is new is the object it reads and the discipline it reads under.

## The charge, not a checklist

The dispatch prompt hands the screener the **substrate** and the **Code Review Rules** (AGENTS.md:
P1/P2 by consequence, saturation, class-completeness, don't-review-a-fix-into-a-new-defect,
behavioral-over-structural proof) as the *charge it runs under* — and nothing that pre-judges the
work. The moment the prompt says "check for X" or "you are the security reviewer, look for Y," it has
re-digested the work outside the agent and reintroduced the disease (`design/verify-substrate/02`).
So the dispatch is:

- **open-adversarial** — "here is the real diff and what it did when run; construct the input that
  defeats it." Dimensions (correctness, security) are what the reading *surfaces*, not roles assigned
  up front.
- **grounded** — every finding binds to a hunk in the substrate or to a probe result, never to the
  author's account. *Reproduce, don't read*: an unexecuted reading cannot block or clear.
- **improvised** — the defeating input is specific to *this* material (point a symlink at the path;
  split a multibyte char at the read boundary); no fixed list enumerates them.

## Writable-scratch probes: the reviewer runs the work

The screener is not confined to reading. It gets a **writable scratch** and `behavior_plane` to
*run* the changed component against inputs it constructs — the mechanism that turns "I think this
`open()` follows symlinks" into "I pointed one at it and it did." This is the same containment the
independence scripts (M5) provision, reused so the probe itself is witnessed (its exit evidence is
grounded, not self-declared). A screening that only reads is Superpowers; a screening that *runs* is
the grounded version.

## Typed output, including honest abstention

The screening returns typed findings — each `{severity, class, message, substrate_ref (hunk/probe),
repro}` so they flow into disposition (`03`) with structure, not as prose. Crucially it can also
return **`cannot_verify_from_substrate`** for a claim the diff+run cannot settle (e.g. a
behavior that needs an environment the scratch cannot stand up). That abstention is a first-class,
*typed* result — not silence — so the gate can tell "screened and clean" from "screened and
inconclusive," and the second never masquerades as the first. Silence is the failure mode the whole
floor exists to prevent.

## What stays out of scope here

The screening does not decide the phase. It produces findings; the *enforcement* — whether VERIFY may
exit given those findings and their dispositions — is `03`. Keeping the read separate from the gate
is the plane separation UACP already insists on: the council screens, the kernel gates, and neither
does the other's job.

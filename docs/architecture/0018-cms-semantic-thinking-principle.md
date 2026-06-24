---
type: adr
title: CMS — comprehend → measure → serialize as the principle for semantic thinking
description: Ratify comprehend then measure then serialize as UACP's core principle — a coherence invariant (architectural, not an axiom/law) and the discipline for SEMANTIC agent thinking (determinism is to machines as CMS is to agents), with measure kept, determinism relocated to the gate, and two enforcement surfaces.
tags: [cms, core-principle, semantic, coherence, cognition, enforcement]
timestamp: 2026-06-24
status: accepted
---

# CMS — comprehend → measure → serialize as the principle for semantic thinking

## Metadata

- **Status**: accepted — design bundle complete and adversarially validated; injection mechanism built; promoted to AGENTS.md. Cleanup + cross-runtime injection remain (see Consequences).
- **Date**: 2026-06-24
- **Decision Makers**: UACP maintainer
- **Consulted**: a cross-provider adversarial panel (Codex, Kimi, MiniMax-M3) and ChatGPT review, each fed the kernel — not the doc in isolation; two counterexample hunts (foreign domains, then formal CS)
- **Informed**: all agents (the principle is now injected into cognition and stated in AGENTS.md)
- **Related**: the design bundle `design/comprehend-measure-serialize/`; ADR-0012 (phase-intent verification); ADR-0016 (goal-driven track); the graph-engine serialization initiative

## Context and Problem Statement

`comprehend → measure → serialize` (CMS) had been carried informally as UACP's "core principle / candidate axiom" but never ratified or precisely classified. Pressing it through external review and two counterexample hunts surfaced four problems that a ratified framing must resolve:

1. **Wrong claim-type.** Framed as an *axiom/law* ("every operation reduces to CMS"), it is empirical and — a kernel-grounded panel showed — either circular or unfalsifiable.
2. **Wrong domain.** Both the reviews and the hunts (and we, running them) drifted into testing CMS as a theory of *computation* (Paxos, SAT, DFA, a SHA round). The actual claim is about *agent cognition* — **how agents think, not how machines compute.**
3. **A smuggled machine method.** `measure` was specified as "deterministic + fail-closed." Determinism is how *machines* earn trust; demanding it of an *agent's* (semantic) judgment is a category error.
4. **Unenforced on the cognition surface.** The portable preamble (`UACP.md`) stated the discipline but nothing injected it — the panel's strongest standalone objection ("decoration").

## Decision Drivers

- A claim that survives a kernel-grounded adversary, not just a sympathetic reading.
- Honesty about what is *mechanized* vs *normative*, and about the principle's true domain.
- Preserve the wins (the disciplines, the no-self-attestation core) while dropping overclaim.
- The principle must be *enforced*, not merely stated.

## Considered Options (with rejection reasoning)

1. **Keep "axiom / law / primitive."** *Rejected* — empirical and unfalsifiable here; the panel showed "governed = satisfies CMS" reads circular.
2. **Rename `measure` → `decide`** (4 reviewers + both hunts recommended it). *Rejected* — that is the *descriptive* test ("the step produces a verdict"). CMS is *normative*: the LLM's failure mode **is** premature deciding, so "measure" is the corrective name that forces grounding; once injected into cognition the word is the intervention.
3. **Keep `measure` deterministic.** *Rejected* — applies a machine method to a semantic system. Determinism is *relocated* to the verifying gate.
4. **Ship `UACP.md` as an inert payload, or soften it to "aspirational."** *Rejected* — the honest fix for "decoration" is to **build the injection**, not weaken the claim.

## Decision Outcome

Adopt CMS with this framing:

1. **The principle for semantic thinking.** `determinism : machines :: CMS : agents`. Machines earn reliability through determinism; agents are semantic and cannot, so they need their own discipline. Domain = how agents think, not how machines compute.
2. **A coherence invariant (architectural), not an axiom (empirical).** One discipline is *imposed* across the agent's cognition, execution, and governance so the system stays coherent with itself — a chosen unifying constraint, justified by the consistency it buys, not by being a discovered law.
3. **`measure` is kept** — as the corrective name (see option 2).
4. **Determinism relocated** — the agent's `measure` is **grounded + fail-closed** (semantic); determinism belongs to the verification **gate** (the architecture surface).
5. **Two enforcement surfaces** — architecture (Guardian / Heartgate / gates / governed writers) for governance + execution; **system-prompt injection** (`UACP.md` via a SessionStart hook) for cognition.

The three verbs map to three consistencies — comprehend→semantic, measure→decision, serialize→state — which is the **discriminator** for whether something is a semantic (agent) act at all.

## Consequences

- **Generalizes beyond agents, with a non-circular boundary.** The formal-CS hunt found CMS reduces cleanly across all *decision-bearing* computation (consensus, solvers, compilers, symbolic execution); the "breaks" (a SHA round, a DFA transition, a GPU shader) are *deterministic machine operations* — out of domain by the *semantic vs deterministic* criterion, which is independently checkable (not "satisfies CMS").
- **The cognition surface is now real** — the SessionStart hook (`runtime-adapters/hooks/inject_uacp_md.py`) injects the preamble; "decoration" was a build gap, now closed.
- **Follow-up:** (1) cross-runtime injection for Kimi/opencode (their hook formats); (2) finish the `trustless`→`re-derivable` sweep across the bundle and re-ground node 31 against the merged graph engine; (3) a labeled evalset measuring the injection's actual behavioral effect on a host agent.

Canonical targets: `AGENTS.md` (Core Principle section), `design/comprehend-measure-serialize/`, `UACP.md`, `hooks/hooks.json` + `runtime-adapters/hooks/inject_uacp_md.py`.

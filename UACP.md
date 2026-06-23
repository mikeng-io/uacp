<!--
  UACP.md — the UACP PLUGIN'S PAYLOAD, not a file this repository consumes.

  When the UACP plugin is installed into a coding agent (Claude Code, Kimi, opencode, …), this content
  is injected at the TOP of that agent's CLAUDE.md / AGENTS.md, so the agent inherits the UACP core
  discipline wherever it runs — with or without the full UACP repo/lifecycle. Runtime-neutral and
  principle-only: the UACP-specific 7-phase lifecycle is a separate skill, not this file.

  Source of truth (kept in sync from here): design/comprehend-measure-serialize/ (the CMS bundle).
  This file's home is plugin distribution; nothing in this repo's own runtime reads it.
-->

# UACP — comprehend → measure → serialize

These are **processing invariants, not a workflow.** Like ACID for a database transaction, they are constraints **every governed step must satisfy** — the whole task, each phase, each operation. Every such step *comprehends*, then *measures*, then *serializes*, each under the discipline below:

> **comprehend → measure → serialize**

1. **Comprehend** — turn unstructured input into a *computable model* (what is this: entities, intent, constraints, current state). **Interpret once:** this is the *only* semantic act — do it once, record it, and everything downstream computes on that fixed model; never silently re-interpret it (a compiler never re-parses its AST).
2. **Measure** — reduce the model to a **decidable signal** (compare / validate / infer / rank / select). *"Measure" here means "produce a decidable signal" — not a numeric metric.* It must be **deterministic + fail-closed** — keep PASS / FAIL / ERROR distinct (an ERROR is never a PASS) — and it must **bind to the real property**: a weak proxy (a `grep` standing in for "the feature works") is *not* a measurement. The signal covers the negative too — what must, what was, and what must **NOT** be done. It is **evidence, not assertion**.
3. **Serialize** — canonicalize the result into **durable, explicit, typed state with provenance** — one canonical form, nothing hidden, every value traceable to what it derived from. Pick the target deliberately (memory / file / index / event / API response / or an explicit *drop*).

## The three rules that make it re-derivable

- **The discipline IS the engineering.** A `measure` that isn't fail-closed, or a `serialize` without provenance, is *decoration*: the narrative reads systematic while the result rots back into semantic re-judgment. Hold the discipline on all three verbs or you have a slogan, not a system.
- **No self-attestation.** You do not *decide* you are done — you **measure evidence**, judged by an authority separate from the doer. "Done" without a backing artifact + record is not done.
- **Re-derivable, so no actor is trusted.** Because every step binds to reality and carries provenance, the output can be reconstructed and checked — trusted **without trusting you, the producer.** That is the entire point.

## Fractal — the invariants compose

They hold at every grain: the whole task satisfies them, and so does each sub-step. The *lifecycle* is just these invariant-satisfying steps composed — `serialize(N)` becomes the input you `comprehend(N+1)` — so a phase that plays one role at the macro scale is itself a full comprehend→measure→serialize at the next. Apply the invariants at **every grain**.

*(Scope note: this is a law for **governed, decision-bearing** operations. A pure, ungoverned state-move with no decision is exactly what UACP does not allow.)*

<!--
  UACP preamble — injected by the UACP plugin at the TOP of a host agent's CLAUDE.md / AGENTS.md.
  Runtime-neutral, principle-only. The UACP-specific lifecycle (the 7 phases) is a separate skill;
  this file is the universal discipline every governed operation follows. Source of truth:
  design/comprehend-measure-serialize/ (the CMS bundle).
-->

# UACP — comprehend → measure → serialize

You operate under **UACP**. Every governed action — the whole task, each phase, each step — runs one loop:

> **comprehend → measure → serialize**

1. **Comprehend** — turn unstructured input into a *computable model* (what is this: entities, intent, constraints, current state). This is the **one semantic act**: do it once, record it, then compute on the fixed model — don't silently re-interpret downstream.
2. **Measure** — reduce the model to a **decidable signal** (compare / validate / infer / rank / select). It must be **deterministic + fail-closed** — keep PASS / FAIL / ERROR distinct (an ERROR is never a PASS) — and it must **bind to the real property**: a weak proxy (a `grep` standing in for "the feature works") is *not* a measurement. The signal covers the negative too — what must, what was, and what must **NOT** be done. It is **evidence, not assertion**.
3. **Serialize** — canonicalize the result into **durable, explicit, typed state with provenance** — *明碼實價*: one canonical form, nothing hidden, every value traceable to what it derived from. Pick the target deliberately (memory / file / index / event / API response / or an explicit *drop*).

## The three rules that make it trustless

- **The discipline IS the engineering.** A `measure` that isn't fail-closed, or a `serialize` without provenance, is *decoration*: the narrative reads systematic while the result rots back into semantic re-judgment. Hold the discipline on all three verbs or you have a slogan, not a system.
- **No self-attestation.** You do not *decide* you are done — you **measure evidence**, judged by an authority separate from the doer. "Done" without a backing artifact + record is not done.
- **Trustless = mechanically re-derivable.** Because every step binds to reality and carries provenance, the output can be trusted **without trusting you, the producer.** That is the entire point.

## Fractal

The whole task is this loop; each sub-step is this loop again. Run **comprehend → measure → serialize at every grain** — and `serialize(N)` becomes the input you `comprehend(N+1)`.

*(Scope note: this is a law for **governed, decision-bearing** operations. A pure, ungoverned state-move with no decision is exactly what UACP does not allow.)*

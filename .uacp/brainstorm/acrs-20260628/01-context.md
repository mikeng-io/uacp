# Phase 1 — Context & Intent Classification

## Signal source
Surfaced while dogfooding the `hermes-native-plugin` run (hnp-20260628) through the
real PROPOSE lifecycle. After council, the agent had no clear contract for how to
*update* the proposal/plan artifacts. Operator (mike) diagnosed the deeper cause:
the artifact substance is split across YAML + Markdown with no coherent model for
which surface owns what.

## Intent (the real ask)
Not "how do I update after council" (that's the symptom). The real intent:
**define a coherent model for what lives in YAML vs Markdown across all lifecycle
manifest artifacts**, so that:
- the coding agent / council can actually *comprehend* an artifact (prose, not scalars);
- the gate can *measure* it deterministically (relations, not prose proxies);
- updating after council touches ONE home per concern, not two surfaces to hand-sync.

## Operator's framing (the candidate principle)
> "markdown does the content / semantic things; yaml does the relation / deterministic things."

This maps directly onto UACP's own core principle:
`determinism : machines :: CMS : agents` →
- **Markdown = semantic surface** (the `comprehend` input — what the agent + council read)
- **YAML = relations surface** (the `measure` substrate — what the gate computes on)

## Classification
- Domains: governance-core, lifecycle-semantics, artifact-schema, runtime (projection/checks)
- Consequence: HIGH (touches the kernel projection + check engine + every lifecycle skill)
- Council-required: yes (Invariant #4 — kernel/schema change), cross-provider reviewer
- Track: standard

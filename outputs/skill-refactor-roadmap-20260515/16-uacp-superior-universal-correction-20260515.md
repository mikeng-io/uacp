# UACP Superior / Universal Correction — Trustless ACP Is Pattern Evidence, Not Authority

Status: correction artifact. This narrows the prior Trustless ACP pattern grounding so it does not collapse UACP into Trustless ACP.

## Correction

Trustless ACP is not equal to UACP.

Trustless ACP is a project/product-specific Agent Control Plane created to preserve, govern, and evolve the Trustless product. It has specific gates, domains, proposal topology, worktree policies, verification gates, and domain experts because Trustless itself has a domain and product lifecycle.

UACP is superior in abstraction: Universal ACP. It is generic, unified, and domain-neutral. It must not inherit Trustless-specific fixed gates, fixed classifications, fixed reviewer roles, or fixed domains as canonical UACP semantics.

## Correct relationship

```text
UACP = generic/universal governance and execution abstraction
Trustless ACP = one concrete domain-specific instantiation/pattern evidence
```

Trustless may demonstrate useful mechanics, but UACP decides whether and how to generalize them.

## What can be copied from Trustless ACP

Copy structural patterns:

- lifecycle trace shape: entry condition, owner, required checks, outputs, exit condition
- owner skill concept
- executable conductor `SKILL.md`
- local support files only when justified by the skill's checklist
- artifact roots and state authority separation
- runtime adapters as adapters, not authority roots
- phase handoff invariants
- read-only verification principle
- council output shape as evidence, not automatic authority

## What must not be copied as UACP canon

Do not copy:

- fixed G0-G8 gate model
- fixed Gate 0/1/2/3 verification sequence
- fixed domain expert list
- Trustless-specific proposal topology
- Trustless-specific worktree paths
- Trustless-specific review dimensions
- Trustless-specific state schema
- Trustless-specific external reviewer resolver semantics
- any assumption that every UACP run has a product/spec/task classification like Trustless

## UACP Verify correction

Trustless verify has defined gates because Trustless has a defined product/domain. UACP VERIFY must stay adaptive.

UACP VERIFY should not say:

```text
always run fixed Gate 0 -> Gate 1 -> Gate 2 -> Gate 3
```

UACP VERIFY should say:

```text
Determine the verification target, risk surface, evidence clusters, required expertise, and council/review topology adaptively from the current phase artifacts, side effects, authority boundary, and domain context.
```

The council is selected by adaptive routing:

- What is being verified?
- What could fail?
- Which invariants or negative findings exist?
- What expertise is needed now?
- Is a council needed, or is deterministic verification enough?
- If council is needed, what roles/domains should be selected for this specific case?

## UACP skill refactor implication

When using Trustless ACP for the UACP skill refactor, ask:

```text
What abstract pattern is demonstrated here?
How does that pattern generalize without importing Trustless domain assumptions?
What must remain adaptive in UACP?
```

Do not ask:

```text
How do we clone Trustless ACP into UACP?
```

## Refactor method adjustment

For each UACP skill, Explore must include:

1. UACP universal role: what does this phase mean without a domain?
2. Trustless evidence: what pattern does Trustless show?
3. Generalization boundary: what is pattern vs. project-specific detail?
4. Adaptive points: what must remain selected at runtime/context time?
5. Minimal sufficient structure: what files/support are needed to express the universal skill without freezing Trustless-specific gates?

## Final rule

Use Trustless ACP as implementation evidence and design inspiration. Do not let it define UACP's ontology. UACP must remain generic, unified, adaptive, and domain-neutral.

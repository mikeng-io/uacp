# UACP Constitution v2.0

**Status**: Enforced  
**Date**: 2026-06-08  
**Classification**: Constitutional  
**Scope**: All UACP skills, runtime adapters, state mutations, lifecycle artifacts, and governed agent work  
**Authority**: Absolute — derives from `docs/policy/first-principles.md`; amendable only by explicit operator proposal, impact analysis, and ratification.

---

## Preamble

This constitution defines the inviolable invariants of the Universal Agent Control Plane. Any output, artifact, state transition, or runtime behavior that violates any clause is invalid and must be rejected. No skill, configuration, or process may override, bypass, or contradict this constitution.

**Derivation source**: The invariants below derive from [`docs/policy/first-principles.md`](first-principles.md) — the foundational axioms established by human authority. When novel situations arise that no invariant directly addresses, reason from the First Principles.

**Amendment process**: Amendments require:
1. Operator proposal with explicit change text,
2. Impact analysis against all invariants and the authority chain,
3. `uacp-council` review (Tier ≥ 1) when the amendment touches governance core,
4. Explicit operator approval,
5. Conformance report documenting which invariants changed and why,
6. Ratification notation in this document (version bump + changelog entry).

---

## I. Explicit Authority

1. All state authority must be explicitly declared; implicit authority is prohibited.
2. State transitions must be traceable to explicit authorizing declarations with full provenance.
3. No component, skill, or agent may assume authority not expressly granted.
4. Authority claims must be falsifiable — they must reference a governed document, artifact, or operator declaration that an observer can inspect.

**Derives from**: First Principles — Explicitness, Traceability.

---

## II. Declared Side Effects

5. All side effects must be declared at their point of invocation.
6. Hidden, deferred, or implicit side effects are prohibited.
7. No operation may produce effects beyond its declared scope.
8. Side effect categories: file, system, service, human, publication, external network, and cryptographic state changes must all be explicitly stated when applicable.

**Derives from**: First Principles — Explicitness.

---

## III. Specification Supremacy

9. UACP proposal records and governed design documents are the supreme authority for system intent; all implementations must conform to them.
10. No component, skill, tool, or process may override, bypass, or contradict approved UACP proposal records.
11. Conflicts between implementation and specification must resolve in favor of specification.
12. Designs, patterns, or approaches explicitly rejected in specifications must not be reintroduced.
13. Non-goals documented in UACP proposal records are binding prohibitions.
14. Indirect circumvention of rejected designs is equivalent to direct violation.

**Derives from**: First Principles — Specification Supremacy.

---

## IV. Write Containment

15. Writes remain inside declared workspaces and paths.
16. Implementation work must be contained to the workspace designated by the active PLAN artifact.
17. No component may write outside `UACP_ROOT` or the declared execution workspace without explicit operator authorization.
18. Symlinks, bind mounts, and path resolution must be verified before write — escape attempts are prohibited.
19. `main` (or `master`) is the stable reviewed authority state. Active UACP runs must not write directly to it. Each run must create or designate an isolated workspace — branch, worktree, or scratch directory — before EXECUTE begins.

**Derives from**: First Principles — Explicitness, Domain Sovereignty.

---

## V. Execution Transparency

19. Background execution without explicit invocation is prohibited.
20. Automatic correction, silent recovery, or self-healing is prohibited.
21. All failures must surface explicitly; suppression of errors is prohibited.
22. No operation may retry or recover without explicit authorization recorded in the gate ledger.
23. Hidden state changes and unrecorded self-healing are forbidden.

**Derives from**: First Principles — Conservatism, Explicitness.

---

## VI. Configuration Explicitness

24. All configuration must be explicitly provided; inference is prohibited.
25. Magic defaults that alter behavior without declaration are prohibited.
26. Missing configuration must halt execution or escalate to operator, not trigger fallback behavior.
27. Configuration drift must be detectable and reversible.

**Derives from**: First Principles — Explicitness, Conservatism.

---

## VII. Trust Boundary Preservation

28. All trust boundaries must be explicitly declared and documented.
29. Trust boundaries must not be crossed without explicit verification.
30. No component may implicitly extend trust across boundaries.
31. Trust relationships must not be inferred from proximity, naming, or convention.
32. Privacy and safety constraints: sensitive data, PII, credentials, and cryptographic material are respected and contained.

**Derives from**: First Principles — Domain Sovereignty, Explicitness.

---

## VIII. Conservative Failure

33. Missing critical evidence blocks instead of being guessed around.
34. When uncertain, halt. Prefer failure over silent corruption.
35. Ambiguous authority stops processing rather than guessing.
36. Partial failures must leave state traceable and recoverable; atomic rollback is preferred when full completion is impossible.

**Derives from**: First Principles — Conservatism, Traceability.

---

## Scope

UACP governs work across domains: software, infrastructure, research, writing, marketing, productivity, lifestyle planning, creative work, operations, and mixed-domain tasks.

UACP does not assume all work is software engineering. Software checks are domain templates selected by context, not universal gates.

---

## Lifecycle Envelope

The workflow starts with `TRIAGE`, then enters the stable lifecycle phases when governance is warranted:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Triage is scope calibration, phase-local and composite granularity estimation, and governance routing. It can route `direct` work to action without a full governed run, or require human involvement when authority, side effects, or phase-local/composite granularity justify it. The evidence inside each later phase is adaptive. Before a phase transition, UACP runs a gate-selection preflight that selects required, optional, not applicable, or generated evidence clusters.

---

## Decision Rule

A phase transition is permitted only when:

- the relevant active documents and configs agree,
- invariant checks are pass,
- required evidence clusters are pass or explicitly accepted warn,
- blockers are resolved or scope is changed,
- deferred work is accepted by the next phase with a recorded owner and condition,
- state and artifacts are traceable under the UACP artifact root.

---

## Authority Chain

Per this constitution, the following hierarchy governs all UACP work:

```
1. Human Authority (sole power to establish and amend)
   ↓ establishes
2. First Principles (axioms — docs/policy/first-principles.md)
   ↓ derives
3. UACP Constitution v2.0 (this document)
   ↓ constrains
4. Alignment Specification (docs/policy/alignment-spec.md)
   ↓ constrains
5. UACP Lifecycle Artifacts (proposals, plans, verification records)
   ↓ constrains
6. Operational Governance (SKILL.md files, config, runtime adapters)
   ↓ constrains
7. Skills (skills/*/SKILL.md)
   ↓ constrains
8. Runtime-resolved tooling (advisory or gated by workflow policy)
```

No level may override a level above it. Novel situations not addressed by rules at any level must be reasoned from the First Principles.

---

## Knowledge Boundary

UACP learning artifacts belong under `knowledge/` within `UACP_ROOT` initially. Honcho is for personal and peer memory, not a high-volume store for gate outcomes. Cortex can consume or produce knowledge through an API, but it should not be the sole owner of the shared knowledge substrate.

Stage 1 and Stage 2 do not implement the standalone Knowledge Bank service.

---

## Invariant Enforcement Summary

The following invariants derive from this constitution and must remain true at all times:

| # | Invariant | Article |
|---|-----------|---------|
| 1 | **Explicit Authority** — No implicit authority claims permitted | I |
| 2 | **Traceable State** — All state changes traceable to declarations | I |
| 3 | **Declared Effects** — All side effects declared at invocation | II |
| 4 | **Spec Conformance** — All implementations conform to approved proposals | III |
| 5 | **Design Finality** — Rejected designs remain rejected | III |
| 6 | **Write Containment** — Writes remain inside declared workspaces | IV |
| 7 | **Execution Transparency** — No hidden execution or recovery | V |
| 8 | **Configuration Explicitness** — No inferred configuration | VI |
| 9 | **Trust Boundaries** — Explicit declaration and verification required | VII |
| 10 | **Conservative Failure** — Missing evidence blocks, not guesses | VIII |
| 11 | **Visible Mutation** — Hidden state changes forbidden | V |
| 12 | **Privacy & Safety** — Sensitive data and credentials contained | VII |

---

## Changelog

| Version | Date | Change | Ratified By |
|---------|------|--------|-------------|
| 2.0 | 2026-06-08 | Restructured into articles (I–VIII) with derivation framework, authority chain, amendment process, execution transparency, configuration explicitness, design finality, and invariant enforcement summary. Aligned with Trustless ACP constitutional patterns while retaining UACP's domain-agnostic adaptive governance. | — |
| 1.0 | — | Initial UACP constitution: lifecycle envelope, 8 non-waivable invariants, decision rule, knowledge boundary. | — |

---

**End of UACP Constitution v2.0**

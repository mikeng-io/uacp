# What Debate Is For

Debate is NOT brainstorming and NOT round-table discussion. Debate is **adversarial validation** — the structured attempt to disprove each finding before accepting it as real.

**The core problem debate solves:** Domain experts find what they're looking for. A security expert finds security issues. A database expert finds schema problems. Left unchallenged, findings accumulate without any filter for whether they're actually real, actually severe, or actually the root cause. Debate applies that filter.

**What debate produces that solo analysis cannot:**
- Findings that survived an attack (higher confidence than ones that weren't challenged)
- Downgraded findings where the initial severity was an assumption, not evidence
- Withdrawn findings that were patterns, not problems
- New findings that only appear when you combine two domain experts' views

## Brainstorm Is Related, But Not The Same

Brainstorm mode is **divergent proposal generation followed by adversarial convergence**. It should not force proposals into finding/severity fields. Use brainstorm mode when the task is to design an architecture, generate alternatives, or discover candidate approaches before deciding what to build.

Brainstorm phases:

1. **Diverge** — independent proposal generation with minimal, non-leading context.
2. **Expand** — publish proposal inventory; participants improve, combine, or add missing alternatives.
3. **Challenge** — Devil's Advocate and peers challenge assumptions, complexity, feasibility, and hidden coupling.
4. **Converge** — merge, split, reject, or park proposals.
5. **Handoff** — produce an accepted direction, open questions, and next-step recommendation.

Proposal states: `proposed`, `expanded`, `challenged`, `revised`, `merged`, `split`, `accepted`, `rejected`, `parked`, `superseded`.

## What "Debate" Means Per Task Context

The same 5-phase structure applies to every context. What changes is *what each participant is looking for* and *what counts as a valid challenge*:

**Code / Technical Review:**
- Domain experts analyze: correctness, safety, performance, maintainability
- DA challenges: "Is this finding a real bug or just a style preference? What production scenario triggers it? Has the codebase already handled it somewhere else?"
- IC checks: "If this bug exists in module A, does module B's error handling assume it can't happen?"
- Valid challenge: "This SQL injection claim assumes the ORM doesn't sanitize inputs — it does at the call site in auth_middleware.go"

**Security Audit:**
- Domain experts analyze: threat vectors, attack surface, data exposure, access controls
- DA challenges: "Is this exploitable in practice given the deployment context? Does the attacker need prior access that narrows the risk?"
- IC checks: "Does this authentication gap in the API also affect the admin panel that shares the same session store?"
- Valid challenge: "CRITICAL classification assumes external attacker access — this endpoint is only reachable from the private VPC"

**Architecture / Planning:**
- Domain experts analyze: feasibility, scalability assumptions, dependency risks, sequencing
- DA challenges: "What assumption does this plan depend on that hasn't been validated? What's the failure mode if the third-party API changes its contract?"
- IC checks: "Does the proposed event-sourcing approach in service A create a schema coupling problem with service B's projection?"
- Valid challenge: "This plan assumes linear traffic growth — if traffic spikes 10x on launch day, step 3 blocks everything"

**Research Synthesis:**
- Domain experts analyze: source credibility, evidence quality, conclusion validity
- DA challenges: "Does this conclusion follow from the cited sources, or is there a logical gap? Are the sources independent, or do they all cite the same original study?"
- IC checks: "Does finding X from the technology domain contradict finding Y from the business domain in a way neither domain's report acknowledged?"
- Valid challenge: "The cited study had n=47 and no control group — the confidence should be LOW, not STRONG"

**Creative / UX / Content:**
- Domain experts analyze: clarity, consistency, user task completion, brand alignment
- DA challenges: "Does this UX issue reflect the actual user population or just power users? Would the proposed fix create a different problem for a different segment?"
- IC checks: "Does the navigation change proposed by the UX expert break the content structure the content expert assumed?"
- Valid challenge: "The 'confusing label' finding is based on one user test — the current label tests well with users who read the tooltip"

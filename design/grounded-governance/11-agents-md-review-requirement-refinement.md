---
type: design
title: "AGENTS.md review requirement — needs improvisation, not correction (adjudication is resolution; materiality is severity-relative)"
description: "Answers the question: does merging the floor with documented-but-unfixed findings mean AGENTS.md's council-gate requirement ('zero material findings unresolved') is inaccurate? No — but it is UNDERSPECIFIED in two ways that directly cause the fix-to-zero spiral. This proposes the two clauses that make the requirement a governable stop-rule instead of an infinite loop."
tags: [grounded-governance, agents-md, council-gate, invariant, stop-rule, adjudication, materiality]
timestamp: "2026-08-27"
edges: [{dst: 10-floor-known-limitations, rel: extends, provenance: asserted}]
---
# AGENTS.md review requirement — improvise, don't correct

## The question

Merging the floor (#173) with Codex findings L1/L2 documented-but-unfixed (node `10`) — does that
mean AGENTS.md Key Invariant #4 ("Council gate … **Zero material findings unresolved**") is
**inaccurate**, or does it **need improvisation**?

## The answer: not inaccurate — underspecified, in two ways that cause the spiral

The invariant is right in spirit. But two undefined words let it be read as "fix every finding,"
which is exactly the non-convergent loop of node `09`:

### 1. "Resolved" is read as "fixed" — but **adjudication is also a resolution**

The framework already ships the machinery: `handled_findings_chain` dispositions
(`remediated` / `justified` / `deferred` / accepted-exception). A finding that is **adjudicated** —
accepted with a documented rationale + residual risk + follow-on — **is resolved**, not unresolved.
The invariant is satisfied by adjudication, not only by a code fix. Node `10` uses exactly this: L1
and L2 are `deferred` dispositions with rationale, so the council gate is met. The current wording
never says this, so every finding reads as a blocker until fixed.

### 2. "Material" is undefined — it must be **severity-relative**

The gate blocks on *material* findings but never defines material. Proposed definition: **a finding
is material when, left unaddressed, it breaks a stated guarantee at its gate's configured severity.**
A **warn**-advisory gate's edge-case gap (L1's closed suffix list; L2's narrow at-cap corner) is
**not** material — the gate only nudges. A **block**-gate bypass (e.g. a run-binding escape that lets
another run's evidence discharge a finding — the P1s already fixed on #173) **is** material. Same
review, opposite dispositions, decided by severity — not by the reviewer's willingness to keep
finding edges.

## Proposed AGENTS.md refinement (for review — canonical-doc change per Invariant #4)

Amend Invariant #4's last sentence from:

> Zero material findings unresolved.

to:

> Zero material findings unresolved, where **resolved** means *fixed OR adjudicated* (a governed
> `handled_findings_chain` disposition — remediated / justified / deferred — carrying rationale and
> residual risk), and **material** means *a finding that, left unaddressed, breaks a stated guarantee
> at its gate's configured severity* (a warn-advisory gap is not material; a block-gate bypass is).

## Why this is the fix to the spiral, not a loophole

Node `09`'s lesson: grounding-as-gates never reaches zero findings, so "reviewer is silent" is an
unreachable bar. Nodes `10`+`11` supply the stop-rule the reviewers (Kimi + Codex) both named —
**convergence is accepting adjudicated residual at a bounded severity, not fixing to zero.** Without
these two clauses, an honest reviewer's endless edge-finding is indistinguishable from a merge
blocker, and the only stable outcomes are infinite fixing or abandoning the work — both of which this
session hit. The clauses do not weaken the gate: a *material* finding (severity-appropriate, breaks a
guarantee) still blocks unconditionally, and adjudication still requires a governed, rationaled record
— self-attested "won't fix" is not a disposition.

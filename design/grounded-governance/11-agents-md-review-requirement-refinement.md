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

## What shipped in the invariant (the stable, coherent core)

After three review rounds (Kimi ×1, subagent ×1, Codex ×1 on the PR), the invariant ships the
**coherent core only** — the part that matches the existing `handled_findings_chain` machinery and
contradicts none of the subordinate lifecycle-policy docs:

> Zero material findings unresolved, where a finding is **resolved** by a fix *or* by adjudication (a
> governed `handled_findings_chain` disposition — handling classification, owner, residual risk,
> next-phase obligation — carrying rationale, never a self-attested "won't fix"). **Material** = a
> finding that breaks a stated guarantee; classification is **read from the finding's source**
> (external-reviewer severity / firing gate), not (re)assigned by the author. Where source severity
> and failure direction conflict, **source severity governs**; failure direction may only *downgrade*
> to non-material a defect that provably fails toward *over-enforcement*, never excuse an
> under-enforcement defect.

### What was pulled to *proposal* (and why — Codex #176, honest flip)

An earlier draft (Kimi's hardening) put "a material finding needs an author-independent
**countersignature**" *into the invariant as law*. Codex's PR review correctly showed this creates a
**coherence break**: the invariant would sit atop `docs/runtime/runtime-enforcement.md` — which
describes what Heartgate *actually* does — while mandating a countersignature that **nothing in the
kernel enforces**. Unenforced law in the top authority, over docs that describe real behavior, is the
very incoherence UACP forbids. So the countersignature — and in-kernel enforcement of
disposition/materiality — is recorded here as a **proposed follow-on**, not shipped as invariant law.
This is a deliberate reversal of the prior draft, logged rather than silent.

**Proposed follow-on (NOT built):** a governed `material` + `countersigned_by` field on the
disposition; a Heartgate check requiring, for a source-`block` finding, a resolving fix OR a
countersignature by an identity distinct from the run's author (mirroring the run-binding check in
`_artifact_resolves` / `_entry_addresses`); and propagation of that rule into
`docs/lifecycle/orchestration-model.md`, `docs/runtime/runtime-enforcement.md`, and
`skills/uacp-verify/SKILL.md` step 7. Whether to build it is the same enforcement-gate tradeoff as
node `09`.

### Why the two extra clauses (audit provenance)

A Kimi cross-provider audit of the *first* draft (which said only "fixed OR adjudicated" + "material =
severity-relative") found it was still a loophole, on two grounds that were then folded in above:

1. **Adjudication had no severity gate** — read literally, a *material* block-gate bypass could be
   "resolved" by an author-written `deferred` paragraph, contradicting this node's own claim that
   material findings block unconditionally. Fixed by: adjudication resolves *non-material* findings
   alone; **material findings need a fix or an author-independent countersignature** (Kimi's
   cross-provider premise turned inward — the same mechanism that caught this).
2. **"Severity-relative" was a soft anchor** the author can turn (warn vs. block is a config knob).
   Fixed by anchoring materiality in **failure direction** (under- vs. over-enforcement) and stated
   guarantees, not severity alone; severity config is itself council-gated, not author-set.

The audit also demonstrated the risk empirically: the very first adjudication written under the draft
regime (node `10` L2) shipped with a rationale that *misstated the gate's severity* — proving that
"carrying rationale" is a structural bar the kernel validates for shape, not adequacy, and that
independent review of a deferral is therefore load-bearing, not optional.

## Enforcement status (honest scope — subagent review, third pass)

An independent subagent review verified every factual claim against the code (PASS: disposition enum
at `validate_uacp_artifacts.py:73`; cap codes are `block` at `rework_completeness.py:583`/`:169`;
discharge = adjudicate-AND-well-formed at `:491-494`; severity is council-gated config) and then found
the control's real limit: **materiality classification and the countersignature are, in the kernel
today, prose — author-self-declared and un-witnessed.** No `material` / `countersigned_by` field exists
on `handled_findings_chain`; the kernel validates disposition *shape* (`_CANONICAL_DISPOSITION_REQUIRED_FIELDS`,
`rework_completeness.py:120-129`), never *who signed* or *whether the finding is material*. So the hole
moves one step upstream: an author could relabel a material (under-enforcing) defect as
"non-material / over-enforcing" and discharge it solo — the countersignature never fires. This node's
own L2 example (an author misstating a gate's severity) is the worked proof.

Two responses:

1. **Norm-level closure (applied):** materiality is **read from the finding's source** — the external
   reviewer's severity or the firing gate's council-gated severity, under the failure-direction rule —
   **not (re)assigned by the author**. A Codex/Kimi P1 on a block-gate is material by its source; the
   author cannot downgrade it. This makes the label witness-anchored, not judgment-anchored, without a
   new gate.
2. **Enforcement (tracked follow-on, NOT built):** a governed `material` + `countersigned_by` field on
   the disposition, and a gate that — for any finding whose source severity is `block` or class ∈
   {blocker, invariant_failure} — requires a resolving fix OR a countersignature by an identity
   distinct from the run's author (mirroring the run-binding check in `_artifact_resolves` /
   `_entry_addresses`). Whether to build this is the **same tradeoff as the whole effort** (node `09`):
   it is another enforcement gate, with its own edge cases. Until it is built, Invariant #4's
   material-finding teeth are a **documented norm, not a kernel-witnessed gate** — and the invariant
   text now says so plainly rather than implying enforcement that does not exist.

## Why this is the fix to the spiral, not a loophole

Node `09`'s lesson: grounding-as-gates never reaches zero findings, so "reviewer is silent" is an
unreachable bar. Nodes `10`+`11` supply the stop-rule the reviewers (Kimi + Codex) both named —
**convergence is accepting adjudicated residual at a bounded severity, not fixing to zero.** Without
these two clauses, an honest reviewer's endless edge-finding is indistinguishable from a merge
blocker, and the only stable outcomes are infinite fixing or abandoning the work — both of which this
session hit. The clauses do not weaken the gate: a *material* finding (severity-appropriate, breaks a
guarantee) still blocks unconditionally, and adjudication still requires a governed, rationaled record
— self-attested "won't fix" is not a disposition.

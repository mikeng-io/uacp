---
type: analysis
title: The Independence Gap — the external reviewer audits our narrative, not the artifact
description: The Agent-Council external reviewer (Tier >=2) is meant to be an independent auditor, but every role at every tier is push-fed the orchestrator's framing; independence is faked via runtime-swap alone. Frames the goal (Deloitte audit) and records why the naive "empty the fields" patch was refuted.
tags: [council, external-reviewer, independence, audit, pull-vs-push]
timestamp: 2026-07-10
edges: []
---

# The Independence Gap

## The goal, in Mike's framing

> "When you ask Deloitte to do the audit, you're not telling them what to audit. The
> information already exists in the system as files and data, so they retrieve whatever
> they want."

The whole point of dispatching an **external runtime** (Codex, Kimi — a different
provider/model) as a reviewer is that its independent harness finds flaws the author and
the orchestrator would miss. Independence means the reviewer **pulls** its own grounding
from the artifact. A reviewer that is handed the orchestrator's summary of "here is what
this change does and here is what matters" is not independent — it is self-attestation by
proxy (see the standing rule: a same-model-only review is self-attestation; the same
failure reappears if the review is same-*framing*-only, regardless of which model runs it).

## What is actually built today

Two things are correctly separated in the taxonomy already:

- **Role** (Domain Expert / Devil's Advocate / Integration Checker) — a *prompt-construction*
  concern, resolved from the domain registry, identical shape at every tier.
- **Runtime** (Claude / Codex / Kimi / …) — a *which-process-executes* concern, resolved by
  the `uacp-bridge` per-adapter pre-flight.

`council-taxonomy.md`'s Diversity Dimensions table lists `role` and `runtime` as orthogonal
axes — so the mechanism for "a separate entity reviews independently" exists: at Tier 2/3 the
orchestrator dispatches a runtime adapter, and that adapter runs *its own* internal Tier-1
council using its own native tools.

**But independence is faked by runtime-swap alone.** Everything the external runtime's internal
council sees is still assembled by the orchestrator and pushed across the boundary as a single
`runtime_input` payload (`phase-4-dispatch.md` Step 6.2.3): `task_description`,
`context_summary`, `domains`, `mode`, `task_type`. The external council never starts from the
artifact — it starts from our narrative, one process removed. There is **no Diversity Dimension**
for pull-vs-push grounding; the property we want is not even named.

Worse, the one real external-audit pattern in the repo,
`uacp-bridge/references/kimi-codex-agent-council-audit-loop.md`, is *more* push-heavy than the
default: it hands the external runtime a pre-curated "Required surfaces" file list **and**
prescribes which five roles to simulate. The orchestrator decides both what to look at and who
looks, before the external agent reads a line. That is the exact opposite of the Deloitte model.

## Why the obvious patch is wrong (the refuted diagnosis)

The tempting fix — "for Tier >=2, set `task_description` and `context_summary` empty and tell the
reviewer to derive its own understanding" — was put to a 3-reviewer adversarial subagent audit
(2026-07-10). All three, reading the skills independently, **refuted it as reviewer-starvation**:

1. **The leak is not one field.** Framing also reaches the external runtime through the `domains`
   array, the Codex coordinator prompt (`codex.md` Step 3 literally dictates the external runtime's
   internal council structure), `mode`/`task_type`, and the between-rounds context packet. Emptying
   two fields closes none of those.

2. **Emptying starves the reviewer of the artifact itself.** The MCP path (`mcp__codex__codex`,
   the *preferred* path for non-Codex runtimes) has **no working-directory parameter** — the only
   way to point it at the artifact is prompt text. And for an **uncommitted-diff** review the change
   under audit lives *only* in the prompt (`phase-4-dispatch.md:18-19`: "embed the diff in the
   prompt; the sandbox is at the committed ref"). Emptying the fields deletes the sole copy of the
   change — the reviewer audits baseline code, unaware anything changed.

3. **It is convention, not teeth, and it overclaims.** "Derive your own understanding" is a hope,
   not a mechanism; synthesis cannot tell "pulled its own grounding" from "reviewed blind and
   confabulated." The repo's own honesty rule (`uacp-bridge/SKILL.md:244`) forbids describing a
   convention-tier control as a guarantee.

The audit relocated the defect precisely (see [[01-narrative-vs-spec]]): the fields conflate
**leading narrative** (bias toward a conclusion) with the **engagement specification** (what to
review at all, including the diff pointer). The fix is not to blank them — it is to strip the
*leading* half while preserving the *specification* half, and to make the pull **measurable**.

## Honest framing: elective improvement, hygiene not guarantee

Three things must be said plainly so the bundle does not oversell itself. **First, nothing is broken
today** — current behavior is full-push, which is *not independent* but is *not failing*. The "hard
breaks" catalogued in [[20-blast-radius]] only fire *if* you strip the narrative; the change introduces
the risk it then closes. This is an elective improvement to a real property, not the defusing of a live
bug. **Second, the council gate is not merely advisory** — `unresolved_material_council_findings` is a
real phase-transition blocker (`config/phase-transitions.yaml`). That cuts toward doing this: a *blocking*
gate whose external reviewer is push-fed the author's conclusion is the framework self-attesting exactly
where it matters most. (Only the deferred `grounding_provenance` teeth ship advisory-first — see
[[11-grounding-provenance]] — not the council gate itself.)

**Third — and this is the unanimous verdict of a cross-provider council (Codex + Gemini + Kimi,
2026-07-10) that re-verified every claim here against source — Slice 1 is dispatch *hygiene*, not
achieved independence.** Removing the leading narrative redecorates the push; it does not manufacture a
pull. True independence is an **environmental** property, not a prompt property: as long as the
orchestrator constructs the prompt and (for an uncommitted change) embeds the only copy of the diff, the
reviewer is definitionally push-fed on the MCP/uncommitted path ([[01-narrative-vs-spec]] Modes 1–2). So
Slice 1 must be framed as "minimal-non-leading dispatch hygiene + two real break fixes," and *not* as a
guarantee that the external reviewer became independent. The property that would make independence real
(measured pull) is [[11-grounding-provenance]], which is deferred precisely because it does not yet work.

## What this bundle proposes

| Concern | Node |
|---|---|
| The load-bearing distinction (narrative vs spec) + the two starvation modes | [[01-narrative-vs-spec]] |
| Correctness fix: plumb `context_policy: minimal-non-leading` into review/audit dispatch | [[10-minimal-non-leading-dispatch]] |
| Independence teeth: declared + checked `grounding_provenance`, fail-closed at synthesis | [[11-grounding-provenance]] |
| Reframe the pushed `domains` array as a coverage floor, not a suspect ceiling | [[12-domains-coverage-floor]] |
| Name the pull-vs-push axis in the Diversity Dimensions table | [[13-taxonomy-dimension]] |
| Build constraints: consumers that break if fields are naively emptied | [[20-blast-radius]] |
| Apply the distinction: rewrite the kimi-codex audit-loop doc | [[21-audit-loop-rewrite]] |
| Sequencing | [[30-rollout]] |

## Status / Checkpoint

**2026-07-10** — Design drafted this session. Diagnosis confirmed by 3-subagent adversarial review
(refuted the naive patch; relocated the defect to narrative-vs-spec conflation + missing teeth).
Nothing built yet. No PR. The correctness fix ([[10-minimal-non-leading-dispatch]]) is load-bearing
and must land before or with any field-emptying; the teeth ([[11-grounding-provenance]]) are the
part that makes independence real rather than instructed.

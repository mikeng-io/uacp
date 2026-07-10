---
type: design
title: grounding_provenance — a DEFERRED candidate for measuring the pull (not honest yet)
description: The independence "teeth" — a bridge-output field in which the external reviewer enumerates what it self-retrieved, checked fail-closed at synthesis. DEFERRED because as first sketched it does not work — a resolve-in-scope check cannot distinguish self-pull from restated-push, because the retain-vs-strip contract forces the diff into the prompt (for an uncommitted change the diff IS the summary), and on the preferred MCP path pull is environmentally impossible. Records the conditions that would make it honest before it may ship.
tags: [grounding-provenance, teeth, fail-closed, deferred, diff-echo, mcp]
timestamp: 2026-07-10
edges:
  - {dst: 01-narrative-vs-spec, rel: depends_on, provenance: derived}
  - {dst: 00-problem, rel: realizes, provenance: asserted}
---

# `grounding_provenance` — the deferred teeth

## Status: DEFERRED (Slice 2, not built with Slice 1)

Stripping the leading narrative ([[10-minimal-non-leading-dispatch]]) makes it **absent**; it does not
make the pull **present**. The intent of this node is to make the pull *measurable* rather than hoped-for
— the same declare→check→fail-close move `bridge-containment` already ships for `model_authorized`
(`design/bridge-containment/20-model-authorization.md` — referenced, not restated). A 3-reviewer audit
(2026-07-10) showed the first sketch **does not achieve that**, so this node records the idea, why it
fails as drafted, and the exact conditions that would make it honest. It ships nothing until those hold.

## Why the obvious version does not work

The naive design: reviewers enumerate what they retrieved (SHAs, diff hunks, files:lines); a checker
(sibling to `check_model_authorized.py`) verifies the cited references **resolve in scope**; synthesis
rejects reports whose findings lack resolvable provenance. Three defects, each grounded:

1. **Diff-echo — resolution ≠ derivation.** The retain-vs-strip contract *forces the diff into the
   prompt* ([[10-minimal-non-leading-dispatch]] RETAIN; [[01-narrative-vs-spec]] Mode 2). For an
   uncommitted change the pushed diff **is** the summary — the same bytes. A reviewer that derived
   nothing and merely restated the pushed diff emits a provenance trail citing the diff's *own*
   coordinates, which resolve perfectly. The check passes. It cannot separate "pulled from the artifact"
   from "restated what I was handed" — which is the entire distinction it exists to measure.

2. **Environmentally hollow on the preferred transport.** The MCP path (`mcp__codex__codex`, *preferred*
   for non-Codex runtimes) has no working directory and never reaches `$SANDBOX` ([[01-narrative-vs-spec]]
   Mode 1). A reviewer there *cannot* self-retrieve — its only grounding is the pushed prompt, so its
   provenance can only echo pushed content (defect 1) or cite whatever unrelated tree the server launched
   in. Genuine pull is possible only on the CLI/contained path, where `$SANDBOX` is the cwd.

3. **False assurance + a false parallel.** Stamping `diversity_sources: pull` because a field resolved
   would certify a push-fed, decorated report as "independent" — manufacturing exactly the confidence
   UACP exists to prevent, and violating the `SKILL.md:244` honesty rule this bundle wields against the
   naive patch. The "sibling of `model_authorized`" framing is also wrong on timing: `model_authorized`
   is a **pre-dispatch** callable gate; provenance is inherently **post-hoc** (you cannot check what a
   reviewer retrieved until it returns), and `phase-7-synthesis.md` is presently a stub — so this is a
   synthesis-time stage to **build**, not one to extend. "Approved provider" is a checkable fact;
   "reasoned independently" is categorically not — the residual here is larger than model-auth's.

## What would make it honest (the conditions to un-defer)

This node may proceed to build only when all three hold — otherwise it overclaims:

- **Path-scoped pull credit.** Record `pull` (and run the check) *only* on the CLI/contained path where
  `$SANDBOX` is genuinely reachable. On the MCP/uncommitted-diff path, record honestly-degraded grounding
  and never claim `pull`. (This also depends on closing the MCP-no-`$SANDBOX` containment gap flagged out
  of scope in [[01-narrative-vs-spec]] — track with `design/bridge-containment/`.)
- **Evidence beyond the pushed diff.** Provenance is credible only if it cites what the reviewer fetched
  *itself* and could not have gotten from the prompt: a base-SHA it resolved, surrounding/unpushed
  context, related files outside the diff. Resolution then actually *implies* retrieval. A trail that
  cites only the pushed diff's coordinates counts as no pull.
- **Calibration before enforcement.** A planted-fault fixture must show a fabricated/diff-echo-only trail
  is caught and a genuinely self-grounded one passes, before any flip to fail-closed — consistent with the
  advisory-first sequencing in [[30-rollout]].

## Honest limit (state it, per SKILL.md:244)

Even satisfied, this checks the **artifact** of independence, not independent reasoning — a determined
model could fetch beyond-diff evidence and still not *use* it. That residual is real; the hard version is
environmental (a reviewer whose network/filesystem exposes *only* the contained scope — the Tier-3
container line in `bridge-containment`). Until then this is a floor, and only a floor once the three
conditions above hold. It is explicitly **not** part of Slice 1, and Slice 1 does not assert `pull`
without it.

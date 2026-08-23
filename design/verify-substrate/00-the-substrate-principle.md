---
type: design
title: "VERIFY is a substrate, not a role"
description: "The reframe: verify is not a reviewer role or a conformance rubric — it is the substrate (the real work) that review agents screen through, and whatever is wrong precipitates. Grounded in why Codex (a git diff) caught 8 defects UACP's verify (full context) missed."
tags: [verify, substrate, review, council, grounded-governance, correctness]
timestamp: "2026-08-24"
edges: []
---
# VERIFY is a substrate, not a role

## The correction

The instinct to fix "verify doesn't verify" by adding reviewer **roles** — a security lens, a
correctness lens, a compliance lens, each with its rubric — is wrong. A role/rubric **pre-digests the
work** into a checklist the agent applies. That is the same shape as the disease: the reviewer is
handed a *declaration of what to look for* instead of the work itself.

VERIFY is not a role. It is the **substrate** — the real work, produced and exposed as material — that
review agents **screen through**. You pass the work through the substrate and whatever is wrong
**precipitates out**. The agent screens the material; it does not apply a rubric to a summary.

- **Role/rubric** (wrong): "You are a security reviewer. Check: input validation, secrets, authz…"
  → the agent grades against a pre-set list, over a pre-digested view.
- **Substrate** (right): here is the real diff / the real code / what the code actually did when run.
  → the agent screens the material and constructs the input that breaks it — improvised, grounded,
  bounded only by the material, not by a checklist.

## Why this is the real fix (the grounded proof)

On PR #171, UACP's own verify — with the *full* worktree, run, and artifacts — passed a build. Then
Codex, with **only the git diff** and no run context, found eight real defects it missed (symlink
exfil, FIFO hang, a gitignored agreement that can't travel, framework-section injection, truncated
UTF-8 drop, wrong abort disposition, wrong governed-kind segment). **The reviewer with more context
caught less** — because Codex was handed the **substrate** (the diff) and screened through it, while
UACP's verify was handed the **declaration** (artifact presence, schema conformance, cluster states,
replay of the agent's own authored checks) and had no substrate to screen.

This is not a reviewer-quality gap. It is a **substrate gap**: there was nothing real to precipitate
against. Add ten reviewer roles to a declaration and you still catch nothing; hand one reviewer the
diff and it catches eight.

## The principle it instantiates

Expose the real material and let the agent **see and screen** it — do not pre-digest it into a rubric
*outside* the agent. Reading, cross-comparing, constructing the breaking input, deciding what is
wrong: that is the agent's job, done *against the substrate*, not something computed for it and handed
over as a verdict to rubber-stamp.

## What the "dimensions" actually are

Correctness, security, compliance, deploy-safety — the full-dimensional set — are **not pre-assigned
roles**. They are what a screening **surfaces** from the same substrate. Different attention over the
same real material precipitates different classes of defect. You do not assign roles to the substrate;
you expose the substrate and let screenings run over it. A dimension is an *emergent property of
screening real material*, not a job title with a checklist.

## What this reframes (see 01, 02)

- The **substrate** must be *produced and grounded* — kernel-made, witnessed, never agent-supplied
  (else it is the declaration one level up). That is what the deterministic floor is *for* (`01`).
- The **council** is the screening framework; a **screening** is an agent passing the substrate
  through its attention; the deterministic floor makes both the substrate and the screening
  non-skippable (`02`).

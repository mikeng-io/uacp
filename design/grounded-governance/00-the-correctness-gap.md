---
type: design
title: "The correctness gap: the floor is necessary, not sufficient"
description: "The grounded-conformance floor moved VERIFY from assertion to reality — the artifact resolves, the declared planes ran, the git witness binds — but it still measures whether declarations are grounded, never whether the WORK is correct. Layer 2 is the screening that reads the work for undeclared defects, precipitating what no declaration mentions."
tags: [verify, correctness, screening, grounded-governance, floor, defect-lane]
timestamp: "2026-08-24"
edges: []
---
# The correctness gap: the floor is necessary, not sufficient

## What the floor did, and did not, buy

The conformance floor (`design/verify-substrate` + register moves M1–M5) closed a specific hole:
VERIFY no longer clears on the agent's word. A remediation's fix pointer must *resolve* (M2); a
diff that touched code must carry a behavioral check that *ran* (M3a); the git witness can *bind*
(M3c); the rework cap is a *breaker* (M3d); findings carry structure, gates resolve from one table
(M4/M1). Every one of these grounds a **declaration** in reality: *did the thing the run claims
exist / run / stay in scope actually do so?*

None of them reads the work for what the run **did not declare**. A run can pass the entire floor —
every artifact resolves, every declared plane ran, the diff is in scope — and still ship a symlink
that exfiltrates, a FIFO that hangs, a truncated-UTF-8 drop, a wrong abort disposition. The floor
verifies the *account*; correctness lives in what the account omits.

## The proof is already on the record

PR #171 passed UACP's own verify with the full worktree, run, and artifacts. Codex, handed **only
the git diff**, found eight real defects it missed. The reviewer with *less* context caught *more* —
because it was handed the **substrate** (the diff) and screened through it, while verify was handed
the **declaration** and had nothing to precipitate against (`design/verify-substrate/00`). The floor
we just built makes the declaration *honest*; it does not turn the declaration *into the diff*.

## What Layer 2 adds

A **screening**: an agent passing the real work (the substrate) through its attention until
undeclared defects precipitate — improvised, grounded, not rubric-bound (`design/verify-substrate/02`).
The floor is the enforcement that makes the substrate *exist and be grounded* and the screening
*non-skippable*; the screening is the read itself. Two halves, both required:

- **the floor** (built) — the substrate is real, witnessed, and a screening is mandatory;
- **the screening** (this bundle) — an agent actually reads that substrate for correctness.

## Why this is a separate design, not another patch

The register's eighteen defects were symptoms of missing *structure*, and the floor built the
structure. Correctness is a different axis: it is not a gate you can express as "field X resolves."
It is a *judgment over real material* — the one thing the conformance loop deliberately externalizes
to a semantic actor (AGENTS.md: *the executor cannot certify its own pass, so verification is
externally witnessed*). Layer 2 is how that external witness is **produced, charged, grounded, and
made non-optional** — not a rule added to the floor, but the floor's whole purpose realized: a
screening over reality that the run cannot self-attest around.

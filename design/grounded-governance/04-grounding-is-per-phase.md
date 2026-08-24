---
type: design
title: "Grounding is per-phase: one machine, six substrates"
description: "The reframe: reality-grounding is not a VERIFY feature but the governed atom of EVERY lifecycle phase. Each phase emits a declaration and has a phase-specific reality it can be checked against; today all six check the declaration's internal consistency and none checks reality. The correctness screening (00-03) is the VERIFY instance of one machine that instantiates six times."
tags: [grounded-governance, lifecycle, per-phase, triage, plan, code-plane, cascade]
timestamp: "2026-08-24"
edges: [{dst: 00-the-correctness-gap, rel: extends, provenance: asserted}]
---
# Grounding is per-phase: one machine, six substrates

## The generalization

`00`–`03` designed a correctness screening at VERIFY. That was too narrow. The disease it treats —
*a phase measures the declaration, not reality* — is not a VERIFY property. **Every governed phase
emits a declaration, and every one has a reality it can be checked against.** The conformance loop
(*does realized reality match declared intent?*) is meant to be the governed atom at **each** phase,
not only the last one. Grounding one phase and not the rest leaves the cascade intact: a run
mis-scoped at TRIAGE against a fiction is inherited by PROPOSE, planned against by PLAN, and "verified"
at VERIFY as faithful to an intent that was never real.

## The head of the cascade is TRIAGE, not VERIFY

VERIFY grounding catches undeclared *defects in produced work*. It cannot catch *"this whole run was
scoped against something that isn't real"* — because by VERIFY the fiction is upstream. TRIAGE is the
first governed gate and the first declaration (the scope); if it is scored against the design doc and
never compared to the real project root, everything downstream is built on it. Grounding must
**start at TRIAGE** and hold through RESOLVE. (BRAINSTORM is exempt: it is the divergent,
pre-governance phase; grounding it would strangle exploration. Grounding begins where governance does.)

## One machine, six substrates

What is shared is the entire mechanism `00`–`03` built: the kernel produces a **witnessed
reality-substrate**, an agent or a gate screens **declaration-vs-that-reality**, and a **mandatory,
grounded** check (resolves + covers, M2/M3d disposition, the substrate-hash fixpoint) blocks the
crossing. What differs per phase is only the **substrate producer** and whether the mechanism is
*deterministic* (a gate) or *semantic* (a screening):

| Phase | Declaration | Reality substrate | Reality tool | Mechanism | Status today |
|---|---|---|---|---|---|
| TRIAGE | scope / granularity | the real project root the scope names | git / project tree | screening — *is the scope real?* | ungrounded |
| PROPOSE | intent / premise | real current state of the claimed code | project tree / behavior_plane | screening — *is the premise true?* | ungrounded |
| PLAN | approach / blast-radius | the real callers + impact | **LSP / SCIP (codeflair)** | deterministic — declared vs real blast-radius | ungrounded |
| EXECUTE | checkpoints / work done | the actual worktree diff | git witness | deterministic — diff coverage | partial |
| VERIFY | "done" | the diff + reality-run | `diff_content` + behavior_plane | screening — undeclared defects | built (`00`–`03`) |
| RESOLVE | closure / lessons | the run's real evidence residue | manifest / ledger | deterministic — evidence resolves | partial |

The mechanism is not always an adversarial agent. At PLAN it is a **deterministic** comparison —
the plan's declared blast-radius against the LSP/SCIP-derived real one (the long-designed
"prevention-at-PLAN" code plane, present but unwired). At EXECUTE and RESOLVE, half the machinery
already exists (diff-coverage; evidence-must-resolve). The heavy *semantic* screening is where the
declaration is a judgment over rich material the kernel cannot decide — TRIAGE (is this the real
scope?), PROPOSE (is the premise true?), VERIFY (undeclared defects?).

## Why this is the thesis, not scope-creep

The grounded-governance diagnosis was always this: *UACP kept governance's structure from Trustless
and severed the grounding; the reality tools (behavior_plane, LSP, independence) are present but
unwired; the fix is to wire existing tooling to mandatory gates.* Per-phase grounding **is** that fix,
stated completely. The M-floor and the VERIFY screening are the first two instances and the proof the
machine works; this node hoists it to the invariant it was always an instance of: **at every governed
crossing, the declaration is screened against a kernel-produced reality, and cannot self-attest around
it.**

## What this bundle now covers, and the build order

`00`–`03` remain correct as the **VERIFY instance** (the richest substrate, the built proof). The
per-phase instances are their own nodes/build slices, sequenced head-first because the cascade is:

1. **TRIAGE grounding** — scope-vs-project-root screening. Head of the cascade; highest leverage.
2. **PROPOSE grounding** — premise-vs-real-state screening.
3. **PLAN grounding** — deterministic blast-radius vs LSP/SCIP; wires the code plane.
4. **VERIFY screening** — built (`00`–`03`); folds in as instance four.
5. **EXECUTE / RESOLVE** — unify + complete the partial grounding already present.

Each instance is the same machine with a phase-specific substrate producer, built the grounded, TDD
way the M-floor was. The next design pass details the TRIAGE and PROPOSE substrates (what slice of the
project root grounds a scope; what "the real current state" is for a premise) — the genuinely new
production problems; the rest reuse producers that already exist (git witness, behavior_plane,
LSP/codeflair, the manifest ledger).

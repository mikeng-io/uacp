---
type: analysis
title: UACP kernel defect register — what the as-built system actually enforces
description: ROOT (thin). Method, baseline, and the full register. Eighteen defects found by grounding six independent investigations against the kernel rather than the docs.
tags: [audit, defects, as-built, enforcement]
timestamp: 2026-08-22
edges: []
---

# UACP kernel defect register

## What this is

A grounded audit of what UACP's kernel **actually enforces**, as distinct from what its skills,
docs, and design bundles say it enforces. It began as a comparison against `obra/superpowers`;
that comparison produced four false claims about UACP in its first pass, all failing the same
way — reading UACP's surfaces instead of its code. The comparison survives here as one node
(`50-superpowers-contrast.md`); the audit is the product.

## Method

Six independent investigations, each forbidden from reading the comparison document, each
required to carry `path:line` on every claim: lifecycle/transition, evidence/verification,
cognition/emission, state durability, dispatch/multi-agent, and an adversarial audit of the
comparison itself. Their findings were then **re-verified by content** before entry here.

Every defect below carries a status:

- **VERIFIED** — re-checked directly against the file in this session; the quoted mechanism was
  read, not inherited.
- **REPORTED** — surfaced by an investigation, consistent with verified findings, but not
  independently re-checked. Treat as a lead, not a fact.
- **ESTIMATE** — a derived number with its assumptions stated.

## Baseline — and a caveat about it

Measured on `main`. **HEAD was unstable during this session**: readings alternated between
`a1ead92` and `8fd672c` within seconds, and files present at session start (`PRINCIPLE.md`, a
modified `AGENTS.md`) were absent later. `git diff 8fd672c..a1ead92` touches **none** of the
files cited below, so every citation holds across both — but any number here should be
re-derived before it is quoted anywhere load-bearing.

| | |
|---|---|
| Tracked files | 934 |
| Python LOC | 79,498 |
| Check-engine files / LOC | 83 / 18,708 |
| `config/` lines / files | 3,477 / 8 |
| Words in `skills/` | 151,558 total · **96,567 UACP-own** (55k is the vendored `code-review` skill) |

## The register

| ID | Defect | Class | Status |
|---|---|---|---|
| D-01 | The live transition path runs a smaller gate set than `uacp_heartgate_check`, and never checks it ran | bypass | VERIFIED |
| D-02 | `triage → propose` crosses with zero live gates while auto-emitting its ledger records | bypass | VERIFIED |
| D-03 | Guardian is blind to dispatch; the per-phase `Task` rule is inert | bypass | VERIFIED |
| D-04 | A `remediated` finding passes on a non-empty string; a claimed *exception* is grounded, a claimed *fix* is not | grounding | VERIFIED |
| D-05 | The generative gate is opt-in in code, mandatory in prose — a zero-check run passes every check gate | grounding | VERIFIED |
| D-06 | `build_code_index` has zero production callers, so the code plane is unreachable | grounding | VERIFIED |
| D-07 | The only independently-witnessed input — git's real change set — is warn-only | grounding | VERIFIED |
| D-08 | The rework depth cap warns; it has no breaker, though PPV proves the pattern exists in-repo | grounding | VERIFIED |
| D-09 | `Violation.detail` — structured context for programmatic consumers — is discarded at every emission site | emission | VERIFIED |
| D-10 | There is no read-side state tool; a returning agent cannot ask "where am I" | emission | VERIFIED |
| D-11 | `uacp-context` instructs the agent to read four fields nothing writes, from a create-once pointer | emission | VERIFIED |
| D-12 | MCP ships the 4-word label, not the field carrying the preconditions | emission | VERIFIED |
| D-13 | No forward guidance at a phase crossing, though the data already exists in `config/state.yaml` | emission | VERIFIED |
| D-14 | The plugin is not enabled in this repo; every enforcement surface is inert here | operational | VERIFIED |
| D-15 | Session-start injection is Claude-only; other runtimes have no cognition surface | operational | REPORTED |
| D-16 | A `full_governance` run costs ~405 agent invocations / ~630k coordinator tokens | operational | ESTIMATE |
| D-17 | The two independence scripts have no kernel callers — they are orchestrator convention | operational | REPORTED |
| D-18 | `skills/uacp/SKILL.md` is 57% accreted session-specific correction by word count | operational | REPORTED |

## The pattern underneath

Three of the four classes are one failure wearing different clothes. UACP **computes** far more
than it **emits**, and **grounds** far less than it **could with tooling it already ships**.

- The kernel derives structured `Violation` objects and flattens them to strings (D-09).
- It holds `enters_from` / `exits_to` / `purpose` / `allowed_tools` per phase and returns
  `{ok, run_id, from_phase, to_phase}` (D-13).
- It ships a subprocess runner, a SCIP query plane, and a git differ — and makes the first two
  agent-elected and the third advisory (D-05, D-06, D-07).

The recurring shape is **the tooling survives, the mandate does not** — the same diagnosis
`design/grounded-governance/` reached from the phase side, here reproduced independently from
the kernel side.

Read next: `10-enforcement-bypass.md` · `20-grounding-defects.md` · `30-emission-defects.md` ·
`40-operational-reality.md` · `50-superpowers-contrast.md`.

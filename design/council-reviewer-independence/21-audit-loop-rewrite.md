---
type: design
title: Rewrite the kimi-codex audit-loop doc — drop the pre-curated surfaces and role prescription
description: The one existing external-audit pattern (kimi-codex-agent-council-audit-loop.md) is more push-heavy than the default — it hands the external runtime a pre-curated "Required surfaces" file list and prescribes which five roles to simulate. This is narrative-vs-spec applied concretely — replace both with a neutral engagement spec (explore the repo yourself; derive scope and roles) while keeping the read-only/containment lines.
tags: [kimi-codex, audit-loop, required-surfaces, role-prescription, applied]
timestamp: 2026-07-10
edges:
  - {dst: 01-narrative-vs-spec, rel: realizes, provenance: asserted}
  - {dst: 11-grounding-provenance, rel: depends_on, provenance: derived}
  - {dst: 12-domains-coverage-floor, rel: depends_on, provenance: derived}
---

# Rewrite the kimi-codex audit-loop doc

## Why this doc specifically

`skills/uacp-bridge/references/kimi-codex-agent-council-audit-loop.md` is the concrete case that
motivated the whole investigation. It is the repo's one real external-audit pattern, and it violates
[[01-narrative-vs-spec]] in the most direct way — it over-pushes on **both** axes the distinction
separates:

1. **A pre-curated "Required surfaces" file list** — the prompt skeleton hands the external runtime the
   exact files to read. That is the orchestrator setting the auditor's scope: a leading specification,
   not a neutral one. (An auditor told exactly which ledgers to open will not find the fraud in the one
   you didn't list.)
2. **A prescribed 5-role internal council** — "simulate at least these roles: lifecycle governance
   reviewer, validator/runtime auditor, ..." The orchestrator dictates the structure of the external
   runtime's *own* internal council, which should be the external harness's business.

Both are exactly what makes the "independent external auditor" a subagent-in-costume.

## The rewrite

Replace the two push elements with a neutral engagement spec, keeping everything that is containment
(not narrative):

**Remove:**
- The "Required surfaces" explicit file list.
- The "simulate/instantiate at least these roles" prescription.

**Replace with (engagement spec):**
- The scope pointer + the change under review as a **neutral change specification** — the current
  `HEAD`/SHA and the baseline being audited against (this is legitimate: it is the engagement letter,
  telling the auditor *which change/period*, per [[01-narrative-vs-spec]]).
- An instruction to **explore the repository itself** (`git log`, `git diff <baseline>..<current>`, read
  what it deems relevant) to determine *what changed* and *which areas are implicated* — and to run its
  own internal council structured however its harness sees fit.
- The [[12-domains-coverage-floor]] framing if any domains are named at all — floor, not ceiling (the
  Slice-1 prompt-only form).
- *(Deferred, with [[11-grounding-provenance]]):* a hard requirement to cite beyond-diff evidence as the
  basis for findings. For the Slice-1 rewrite this is phrased as an *ask* ("cite what you retrieved"), not
  a checked gate — the checkable version waits on the teeth.

**Keep unchanged (containment, not narrative):**
- READ-ONLY / no-mutation / no-commit / no-write-artifacts instructions.
- The command-level timeout + background execution guidance.
- The `git status` contamination check after the audit (external tools have created untracked files
  despite read-only instructions — a real, observed containment concern, orthogonal to independence).
- The coding-model invocation note (don't force `--model kimi`; use the coding route).

## Boundary

This is an application of [[01-narrative-vs-spec]] + [[11-grounding-provenance]] + [[12-domains-coverage-floor]]
to one reference doc — it introduces no new mechanism. It is called out as its own node because it is
the concrete artifact that most visibly contradicts the goal today, and fixing it is the clearest
demonstration that the abstract distinction changes real behavior.

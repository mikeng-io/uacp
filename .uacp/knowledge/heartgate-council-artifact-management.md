---
type: lessons
title: Heartgate Council Artifact Management
description: Phase-local council vs Heartgate Council distinction, retrieval-led reasoning requirement, artifact placement, 6 required Heartgate lenses, runtime/script alignment checklist, session-proven blocker patterns.
tags: [heartgate, council, artifacts, lifecycle]
timestamp: 2026-06-17
---

# Heartgate Council Artifact Management

Use when UACP work touches Agent Council, Heartgate, phase transitions, runtime enforcement, artifact validators, or lifecycle coherence checks.

## Core Distinction

- **Phase-local Agent Council** checks the work product inside a phase: proposal quality, plan sufficiency, implementation correctness, verification quality, local security risks, and evidence strength.
- **Heartgate Council** checks the phase boundary: whether the phase truthfully satisfied its lifecycle contract and whether the next phase receives a coherent state.

Do not collapse these into one review. A phase-local council can pass while Heartgate still blocks because state/artifacts are inconsistent, warnings are unowned, or the next phase would inherit incoherent assumptions.

## Retrieval-Led Reasoning Requirement

When changing Heartgate, Guardian, council semantics, artifact management, or lifecycle doctrine, do not claim correctness from the main session's understanding alone.

Required loop:

1. **Ground truth first:** inspect the actual UACP docs/config/runtime scripts/artifacts involved.
2. **Dispatch Agent Council:** use role-diverse reviewers for lifecycle coherence, Guardian/Heartgate runtime enforcement, and artifact-management/repo hygiene.
3. **Synthesize findings:** record blockers, concerns, accepted findings, and exact file/path evidence in `verification/`.
4. **Patch all blockers/concerns or explicitly defer them:** do not reframe a blocker as "acceptable" without an owner, residual risk, acceptance, and next-phase condition.
5. **Re-verify:** run syntax/config/artifact validators plus targeted positive/negative runtime checks.

Pitfall: prose/config updates can look coherent while runtime scripts or artifact validators still encode stale behavior.

## Artifact Placement

Heartgate Council / transition-coherence outputs are **verification evidence**, not lifecycle state.

Recommended placement:

```text
UACP_ROOT/verification/<run-id>-heartgate-coherence-<date>.yaml
```

Transition artifacts should reference them with:

```yaml
heartgate_coherence:
  status: pass | warn | block
  artifact_path: verification/<run-id>-heartgate-coherence-<date>.yaml
  lenses:
    - doctrine_coherence
    - cross_artifact_consistency
    - runtime_state_alignment
    - warning_and_deferred_item_honesty
    - authority_plane_integrity
    - next_phase_readiness
```

The coherence artifact does **not** replace `council_synthesis_artifact`. Keep both when both exist:

- `council_synthesis_artifact`: phase-local work review / audit / execution critique.
- `heartgate_coherence.artifact_path`: transition-boundary lifecycle truthfulness and consistency.

## Required Heartgate Lenses

1. `doctrine_coherence` — phase aligns with UACP doctrine and intent.
2. `cross_artifact_consistency` — docs, config, state, proposal/plan, evidence, and status agree.
3. `runtime_state_alignment` — live behavior/state matches artifacts and claims.
4. `warning_and_deferred_item_honesty` — warnings/deferred items have owners, residual risk, acceptance, and next-phase obligations.
5. `authority_plane_integrity` — Kanban, Agent Council, Guardian, Heartgate, runtimes, and UACP lifecycle state remain in their own authority planes.
6. `next_phase_readiness` — the next phase receives a coherent, safe state and explicit obligations.

## Runtime/Script Alignment Checklist

When adding or changing this distinction, check more than prose:

- `docs/lifecycle/lifecycle-reference.md`
- `docs/runtime/runtime-enforcement.md`
- `docs/INDEX.md` artifact registry/change log
- `config/review-routing.yaml`
- `config/phase-transitions.yaml`
- `config/guardian-policy.yaml` when Heartgate transitions or protected categories are implicated
- Heartgate runtime/kernel validation if transition artifacts gain a machine field
- runtime adapter/tool schemas
- artifact validators such as `scripts/validate_uacp_artifacts.py`
- lifecycle skills that mention council/Heartgate responsibilities

Pitfall: updating docs/config without updating Heartgate or artifact validators leaves the new field as unenforced prose.

## Session-Proven Blocker Patterns and Fixes

- **Governed writer symlink escape:** writer path resolution must reject symlinked intermediate directories and symlink target files before writing; resolving after concatenation is not enough.
- **Config-driven coherence requirement:** if `heartgate_coherence` is optional globally, add config/routing triggers for material runtime/governance transitions.
- **Relative path semantics:** Guardian/Heartgate path checks should resolve UACP artifact paths relative to `UACP_ROOT`, not process CWD.
- **Transition-path whitelist:** `uacp_heartgate_check` should accept managed UACP artifact/state roots that can legitimately host transition artifacts.
- **Validator strictness:** manual artifact validators should check `heartgate_coherence.artifact_path` containment and existence, not only field shape.
- **Config drift:** if `guardian-policy.yaml` duplicates transition lists from `phase-transitions.yaml`, add a consistency check or sync the duplicate before claiming coherence.
- **Residual risk honesty:** verification artifacts must name known fail-open/bypass gaps rather than implying total runtime closure.
- **End-to-end proof:** ensure at least one real transition artifact exercises the new `heartgate_coherence` field; unit-like probes alone are not sufficient.
- **Generated cache hygiene:** add/keep `.gitignore` for `__pycache__/` and `*.pyc`; clean generated cache before commit.

## Writer Safety Pitfall

`uacp_doc_write` overwrites the whole target document. Before using it on large canonical docs, build content from the current full file (or `git show HEAD:<path>` plus a targeted insertion), then verify size/expected anchors after the write. Do not paste a shortened reconstruction as the full document.

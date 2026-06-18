---
type: adr
title: Phase Intent Verification
description: Adopt PIV as the phase-local evidence contract binding a phase's intended work to concrete evidence, semantic recovery, authority boundaries, and next-phase readiness.
tags: [piv, execute, evidence, lifecycle]
timestamp: 2026-05-19
status: accepted
---

# ADR 0012 — Phase Intent Verification

## Decision

UACP adopts **Phase Intent Verification (PIV)** as the phase-local evidence contract that binds a phase's intended work to concrete evidence, semantic recovery, authority boundaries, and next-phase readiness.

PIV is deliberately **not** implementation-specific. EXECUTE work may produce code, documentation, configuration, generated artifacts, council synthesis, runtime probes, dry-run evidence, migration preparation, state updates, or handoff packages. PIV asks whether the phase intent was satisfied, not whether software implementation happened.

For the current enforcement increment, PLAN authors the PIV contract for non-trivial EXECUTE work; EXECUTE records checkpoints and semantic evidence against that contract; VERIFY assesses whether the evidence satisfies the contract before RESOLVE.

## Context

UACP already requires adaptive PROPOSE and PLAN semantic packages. EXECUTE still allowed YAML-only checkpoints that could list files and commands without preserving why the work happened, how decisions mapped to PLAN, which assumptions drifted, or whether VERIFY had enough evidence to judge the result.

Trustless PIV is useful pattern evidence, but UACP must remain generic across governance, runtime, documentation, artifact-generation, review, and execution tasks. Naming PIV as "implementation verification" would bias UACP toward code patches and miss other valid EXECUTE outputs.

## Consequences

- PLAN must design the evidence contract for selected non-trivial EXECUTE work.
- EXECUTE must produce both machine checkpoints and semantic execution evidence when the adaptive gate applies.
- VERIFY must judge PIV satisfaction rather than infer readiness from tests, diffs, or worker self-report alone.
- Low-risk/direct work is not forced into a large package; the gate is adaptive.
- YAML remains the lifecycle envelope; Markdown remains the semantic recovery substrate.

## Required Concepts

- **PIV contract:** `kind: uacp.phase_intent_verification_contract`, normally `plans/{run_id}-piv.yaml`.
- **Work units:** neutral units of phase work; not limited to implementation units.
- **Evidence obligations:** required proofs such as artifacts, diffs, tests, runtime probes, council synthesis, decision records, approvals, dry-runs, or semantic notes.
- **Intent drift:** any discovery that changes the phase intent, scope, assumptions, authority, or evidence sufficiency.
- **EXECUTE semantic package:** `executions/{run_id}/` with `00-index.md` and adaptive modules such as work narrative, decision log, evidence map, drift/deviation record, and VERIFY handoff.

## Verification Rule

For selected adaptive EXECUTE evidence gates, a YAML-only execution checkpoint is insufficient. The checkpoint must reference the PLAN-authored PIV contract, satisfy or explicitly defer evidence obligations, and point to a semantic execution package that future agents can recover without chat history.

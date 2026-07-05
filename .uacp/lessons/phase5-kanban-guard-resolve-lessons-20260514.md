---
type: lesson
id: phase5-kanban-guard-resolve-lessons-20260514
title: Phase 5 Kanban Completion Guard — Resolve Lessons
project: uacp
domains: [governance, kanban, verification]
invariants: []
affected_paths: []
severity: MEDIUM
source_run: ""
extracted_at: "2026-05-14"
eligible: 0
recurrences: 0
bes: 0.5
promoted_to: null
tags: [kanban, heartgate, agent-council, guardian, resolve]
---

# Phase 5 Kanban Completion Guard — Resolve Lessons

Phase 5 closed with the Kanban completion guard implemented locally in Hermes Agent and UACP Heartgate Council coherence hardening patched across runtime, docs, config, validator, and lifecycle artifacts.

## Durable lessons

- UACP-bound Kanban completion is a protected evidence event. Creation/dispatch context is not enough; completion must carry `uacp_run_id`, `uacp_phase`, `authority_artifact`, `guardian_policy_version`, declared side effects, and non-empty evidence references.
- Heartgate Council is a transition-boundary coherence judge, separate from phase-local Agent Council. Its evidence belongs in `verification/` and should be referenced by transition artifacts through `heartgate_coherence.artifact_path`.
- Retrieval-led council is mandatory for governance/runtime/artifact-management claims. The council must inspect ground-truth files/scripts/config instead of reviewing only the main-session summary.
- Accepted warnings and deferred items must be structured: owner, acceptance, condition, and residual risk. Vague concerns should block or be patched before RESOLVE.
- Where policy data is duplicated for runtime convenience, artifact validation should include drift checks until a single-source derivation is implemented.
- For read-only UACP containment, `python -m py_compile` can fail because bytecode writes are blocked. Prefer `PYTHONDONTWRITEBYTECODE=1` plus AST parse for syntax checks, then run validators with bytecode writes disabled.

## Accepted residual risks

- Hermes hook-boundary bypass/fail-open gaps remain a future runtime-hardening problem. Phase 5 must not be described as total runtime hook closure.
- `guardian-policy.yaml` still duplicates transition data, controlled by validator drift checks. Future cleanup can derive it from `phase-transitions.yaml`.

## Follow-up candidates

- Start Phase 6 for Agent Council operationalization if continuing the UACP roadmap.
- Consider a future config refactor to eliminate duplicate transition data in Guardian policy.
- Consider a future Hermes runtime hardening phase for hook-boundary closure.

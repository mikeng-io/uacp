---
type: lesson
id: phase6-agent-council-operationalization-lessons-20260515
title: Phase 6 Agent Council Operationalization — Lessons
project: uacp
domains: [governance, verification]
invariants: []
affected_paths: []
severity: MEDIUM
source_run: ""
extracted_at: "2026-05-15"
eligible: 0
recurrences: 0
bes: 0.5
promoted_to: null
tags: [agent-council, heartgate, validation, resolve]
---

# Phase 6 Agent Council Operationalization — Lessons

Phase 6 converted prior Agent Council doctrine into executable UACP contracts.

## Durable lessons

- Retrieval-led governance councils need an explicit `inspected_paths` contract; otherwise reviewers can drift back into summary-based inference.
- Phase-local council evidence and Heartgate transition coherence must remain separate fields/artifacts: `council_synthesis_artifact` versus `heartgate_coherence.artifact_path`.
- Councils returning `concerns` are not automatically blockers, but every concern needs one of: patched, accepted risk, deferred with owner/condition, or rerun.
- Validator hardening should start with explicit artifact-list validation before auto-discovery; auto-discovery can be future work.
- Skill alignment may be required for operational behavior, but skill storage lives outside the UACP repo; closure artifacts should disclose that boundary.
- Evidence-domain registry can exist as design/config input without being runtime-active; runtime activation requires separate selector implementation and verification.

## Future follow-ups

- Consider a validator hardening run for current-run artifact auto-discovery.
- Consider a dedicated evidence-domain-registry runtime selector run.
- Decide whether Hermes skill patches should be mirrored into UACP-managed source or documented as operational dependencies.

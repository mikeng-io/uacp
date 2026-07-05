---
type: pattern
id: skills-validator-alignment-workflow
title: Skills and Artifact Validator Alignment Workflow
description: "7 trigger categories, 5-phase alignment workflow, validator scope minimum, canonical finding-state list, EDR `not_runtime_active` check, 4 pitfalls."
tags: [skills, validators, alignment, workflow]
timestamp: 2026-06-17
---

# Skills and Artifact Validator Alignment Workflow

Use when UACP canonical docs/config have changed and the executable skill layer may be stale.

## 7 Trigger Categories

Run this alignment workflow after changes to:

1. Lifecycle semantics or phase-transition schema.
2. Agent Council / Kanban / runtime/tool/evidence adapter doctrine.
3. Phase-local or composite granularity.
4. Human involvement routing.
5. Council synthesis artifact shape.
6. Evidence-Domain Registry status.
7. Guardian/Heartgate artifact requirements.

## 5-Phase Alignment Workflow

Do not patch docs, skills, and validators ad hoc in one stream. Use a whole phased plan, then execute phase by phase:

**Phase 0 — Inventory and plan.** Inspect canonical docs/config and currently loaded UACP lifecycle skills. Write a bounded phased plan naming targets, acceptance checks, and deferred runtime work.

**Phase 1 — Skill alignment.** Patch lifecycle skills and shared lifecycle contract to implement the new doctrine. Skills should point back to canonical docs/config, not redefine doctrine.

**Phase 2 — Lightweight validation.** Add or update a validator script for manual-drill artifact sanity. Keep it lightweight unless strict schemas are explicitly approved.

**Phase 3 — Verification.** Parse YAML, run validator, search for stale terminology, and write a verification artifact.

**Phase 4 — Runtime hardening handoff.** Defer Guardian/Heartgate production wiring, adapter manifests, and strict schema systems unless explicitly in scope.

## Validator Scope Minimum

A lightweight UACP validator should check at minimum:

- core config YAML parses,
- phase-transition artifacts include required fields from `config/phase-transitions.yaml`,
- council synthesis artifacts include required fields from `council_synthesis_schema`,
- finding states are canonical only: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`,
- Evidence-Domain Registry is not reported as runtime-active while `implementation_status: not_runtime_active`.

## Finding-State Canonical List

Valid finding states: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`. Any other value in a council synthesis artifact is invalid.

## EDR `not_runtime_active` Check

When the Evidence-Domain Registry implementation status is `not_runtime_active`, skills and transition artifacts must not claim the EDR is being queried at runtime. The validator should flag this contradiction.

## 4 Pitfalls

- Do not leave lifecycle skills stale after canonical docs/config move forward.
- Do not treat a config seed/stub as implemented runtime behavior.
- Do not let a validator become a hidden authority source; it implements canonical docs/config.
- Do not harden session-specific bypasses into normal workflow. Record manual-drill bypasses as accepted risk or blockers depending on severity.

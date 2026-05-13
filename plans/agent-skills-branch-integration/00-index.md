# Agent-Skills Branch → UACP Integration Package

Status: accepted for canonical cleanup / still under verification  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

## Purpose

This directory is the split planning package for integrating the `agent-skills` branch concepts into UACP before mutating canonical UACP docs/config.

The old single-file packet remains at:

`UACP_ROOT/plans/agent-skills-branch-to-uacp-integration-requirements-design.md`

Use this split package for review so decisions, requirements, design, execution, and verification are not compressed into one giant document.

## Documents

1. `01-ground-truth.md` — source branch and current UACP inventory.
2. `02-decisions.md` — Mike/Norty design decisions D1–D8.
3. `03-requirements.md` — functional and non-functional requirements.
4. `04-design.md` — proposed canonical docs/config changes.
5. `05-execution-plan.md` — manual lifecycle drill and patch sequence.
6. `06-verification-resolution.md` — verification, resolve, downstream extraction, risks, and next step.

## Non-negotiables captured

- UACP is the single canonical doctrine.
- agent-skills is downstream extraction, not a parallel source of truth.
- No canonical UACP docs/config mutation until this planning package is reviewed.
- No `guardian.py`, adapter scripts, or implementation code port until doctrine stabilizes.
- Guardian is runtime-neutral: kernel + policies + adapters.
- Agent Council is native orchestration, not review-only.
- UACP granularity and council tier are separate axes.
- Evidence clusters and domain registry should merge.
- deep-* wrappers are deprecated/compatibility only, not doctrine.
- Use symbolic roots like `UACP_ROOT/verification/` in docs/config.


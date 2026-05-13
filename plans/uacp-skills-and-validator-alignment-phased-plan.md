# UACP Skills + Artifact Validator Alignment Phased Plan

Status: accepted for phased execution / manual drill  
Created: 2026-05-12T17:50:02.880553+00:00  
Authority source: `verification/agent-skills-branch-integration-agent-council-review.yaml` and canonical docs/config cleanup  
Scope: align lifecycle skills and lightweight validators with updated UACP doctrine.

## Goal

Bring the executable skill layer and artifact validation layer into alignment with the canonical UACP doctrine updates:

- UACP = governance cognition.
- Agent Council = deliberative orchestration.
- Kanban = coordination memory.
- Runtimes/tools/evidence services = bounded execution / observation surfaces.
- Granularity = phase-local and compositional.
- Human involvement = selected by TRIAGE and later phase-local reassessment.
- Council synthesis, phase transition, and Evidence-Domain Registry semantics must be machine-checkable enough for manual drills.

## Non-goals

- Do not implement production Guardian/Heartgate hardening in this phase.
- Do not port `guardian.py` or runtime adapter scripts from agent-skills.
- Do not claim Evidence-Domain Registry runtime selection is active.
- Do not convert all UACP artifacts into a strict JSON Schema system yet.

## Phase 0 — Inventory and plan

Inputs:

- UACP canonical docs/config under `UACP_ROOT/docs/` and `UACP_ROOT/config/`.
- UACP lifecycle skills under `HERMES_ROOT/skills/devops/uacp/`.
- Existing council review findings.

Outputs:

- This phased plan.
- Task list for Phase 1–3.

Acceptance:

- Plan names files to patch.
- Plan separates skill alignment from validator/runtime implementation.

## Phase 1 — Lifecycle skill alignment

Patch lifecycle skills so they execute the new doctrine instead of stale assumptions.

Files:

- `HERMES_ROOT/skills/devops/uacp/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/references/lifecycle-skill-contract.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-triage/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-propose/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-plan/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-execute/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-verify/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-resolve/SKILL.md`
- `HERMES_ROOT/skills/devops/uacp/uacp-state/SKILL.md`

Required changes:

- Add `docs/orchestration-model.md` to read-first where relevant.
- Add phase-local granularity fields: `entry_estimate`, `exit_actual`, `delta_reason`, `downstream_projection`.
- Add human involvement check fields and routing semantics.
- Replace bridge/deep-council assumptions with Agent Council tiers and dispatch surfaces.
- Clarify Agent Council vs Kanban cognitive roles in PLAN/EXECUTE.
- Make VERIFY consume council synthesis and finding states.
- Make RESOLVE extract lessons and downstream skill updates from council findings.

Acceptance:

- No lifecycle skill treats Kanban as governance or council as only review.
- No lifecycle skill requires external bridge dispatch just because work is “medium”.
- Skills point back to canonical docs/config rather than redefining doctrine.

## Phase 2 — Lightweight artifact validator

Create a small validator script for manual drills.

File:

- `UACP_ROOT/scripts/validate_uacp_artifacts.py`

Capabilities:

- Parse core YAML config files.
- Validate phase-transition artifacts against required fields in `config/phase-transitions.yaml`.
- Validate council synthesis artifacts against `council_synthesis_schema`.
- Check finding states use canonical values only.
- Check Evidence-Domain Registry is not reported as runtime-active unless implementation status changes.
- Emit clear PASS/WARN/BLOCK output.

Acceptance:

- Script runs without external dependencies beyond Python stdlib + PyYAML if available.
- Script validates known current verification/council artifacts without crashing.
- Script reports missing required fields as BLOCK.

## Phase 3 — Verification

Run lightweight checks:

- YAML parse for changed UACP configs and verification artifacts.
- Content search for stale terms:
  - `bridge-*` as canonical runtime wording.
  - unqualified `deep council` as doctrine.
  - unsupported finding states such as `accepted_risk_for_manual_drill`.
- Run `scripts/validate_uacp_artifacts.py` against verification artifacts where applicable.
- Create a verification artifact for this skills/validator phase.

Acceptance:

- YAML parse passes.
- Validator script runs.
- Remaining warnings are explicit and bounded.

## Phase 4 — Later runtime implementation handoff

Deferred.

Future work:

- Convert lightweight validator to strict schemas if needed.
- Wire validator into Guardian/Heartgate or lifecycle tooling.
- Add Kanban task templates for council execution topology.
- Add runtime/tool/evidence adapter manifests.
- Implement Evidence-Domain Registry selector.

## Execution posture

Proceed phase by phase. After each phase, verify before moving to the next. If a phase reveals cognitive/doctrine drift, patch canonical docs first, then skills, then validators.

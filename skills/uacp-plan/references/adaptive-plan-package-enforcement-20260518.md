# Adaptive PLAN Package Enforcement — Session Lessons (2026-05-18)

Use this reference when PLAN package shape, PLAN→EXECUTE Heartgate behavior, or UACP self-patch write authority is in question.

## Core doctrine

A serious UACP PLAN is a **human-reviewable execution package**, not a single YAML file.

```text
plans/{run_id}/                    # PLAN substance: topology, work packages, verification, rollback
plans/{run_id}-plan.yaml           # machine lifecycle envelope only
plans/{run_id}-scope.yaml          # machine scope/authority contract
plans/{run_id}-plan-selection.yaml # bridge/check artifact
```

Do not treat `*-plan.yaml` as the whole plan. YAML enforces; Markdown explains; `plan-selection.yaml` bridges.

## Universal PLAN core

Adaptive PLAN packages should cover or explicitly mark N/A:

- `work_breakdown`
- `dependencies`
- `authority_and_side_effects`
- `tool_runtime_selection`
- `artifact_write_surfaces`
- `verification_strategy`
- `rollback_recovery`
- `council_review_topology`
- `transition_readiness`

N/A entries must be falsifiable and include:

```yaml
reason: ...
accepted_by: PLAN
owner: ...
residual_risk: ...
revisit_phase: execute | verify | resolve
revisit_trigger: "observable condition that makes this selected again"
```

## OpenSpec / Trustless ACP distillation

Borrow the pattern, not the shape.

- OpenSpec lesson: split artifacts by concern; do not import fixed `design.md/specs/tasks.md` as a universal UACP requirement.
- Trustless ACP lesson: control-plane-only planning, hard preconditions, validation artifacts, rollback; do not import project-specific proposal IDs, worktrees, or application-code gates as UACP universals.

PLAN must remain UACP-native:

```text
authority -> topology -> execution graph -> tool/runtime surfaces -> verification -> rollback -> transition gate
```

## Validator / Heartgate enforcement pattern

For `kind: uacp.plan_package_selection`, validator/Heartgate should check:

- `phase: plan`
- `run_id` exists
- `plans/{run_id}/` exists
- `plans/{run_id}-scope.yaml` exists
- universal PLAN core complete
- selected modules have reason + artifact
- selected artifacts exist under UACP_ROOT
- N/A entries include all required fields, including `revisit_trigger`
- `transition_readiness.status` is valid

Negative fixtures should prove missing core concerns, missing artifacts, weak N/A, and YAML-only plan attempts block.

## Self-patch write-authority gap and fix

When a UACP self-repair PLAN needs to touch paths that normal governed writers do not reach, such as:

```text
skills/devops/uacp/
scripts/
runtime-adapters/
```

Do **not** solve it by making `terminal` or generic `patch` a universal governed writer.

Use a narrow explicit scope block:

```yaml
self_patch_write_authority:
  enabled: true
  reason: >-
    UACP self-repair touches skill/script/runtime-adapter paths no existing
    governed writer directly reaches.
  authority_artifact: proposals/{run_id}-proposal.yaml
  owner: main_session
  rollback_path: targeted patch revert or checkpoint
  allowed_prefixes:
    - skills/devops/uacp/
    - scripts/
    - runtime-adapters/
  verification_obligations:
    - AST parse changed Python sources
    - validator pass/block fixture checks
    - Heartgate transition check
```

Heartgate source should accept otherwise-unreachable `scope.write_paths` only when this block is present, complete, and the path starts with one of the hardcoded safe prefixes.

This is a bootstrap/self-repair exception only. It is not permission for ordinary work to bypass governed writers.

## Runtime reload caveat

After patching Heartgate kernel source, distinguish three claims:

```text
source-level Heartgate behavior: local import/AST verified
live uacp_heartgate_check behavior: only true after plugin/runtime reload
Guardian hard interception: only true after live runtime proof
```

If `uacp_heartgate_check` still reports old blockers after source patching, treat it as a likely stale long-lived plugin/runtime until reloaded. Record the caveat; do not claim clean lifecycle closure.

## Reporting rule

When VERIFY council returns `CONCERNS` due only to runtime reload / live-binding caveats, resolve as:

```text
resolved_with_runtime_reload_caveat
```

not as a clean PASS. The next action is runtime reload and rerun of the live transition check.
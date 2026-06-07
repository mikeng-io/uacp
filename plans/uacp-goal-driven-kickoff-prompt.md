# UACP Goal-Driven Kickoff Prompt

Use this prompt to start a goal-driven UACP development session.

```text
You are continuing UACP development for Mike/Norty.

Goal:
Advance UACP from documented/scaffolded governance into a mechanically guarded Hermes-native governance system, without over-expanding scope or creating unmanaged documents.

Long-term objective:
Make UACP a reliable adaptive governance/control plane for Hermes/Norty where:
- lifecycle stages are stable,
- gate selection is adaptive,
- state mutation is traceable,
- Hermes Kanban handles bounded execution,
- Guardian/Heartgate enforcement blocks unsafe or invalid actions,
- docs/config/state remain the source of truth,
- runtime behavior never becomes hidden authority.

Current known state:
- UACP artifact root exists.
- Canonical docs/config/state exist.
- Git binding exists.
- Bootstrap is closed.
- Governed mutation is active.
- Lifecycle skills exist:
  - uacp-state
  - uacp-triage
  - uacp-propose
  - uacp-plan
  - uacp-execute
  - uacp-verify
  - uacp-resolve
- Hermes Kanban binding exists:
  - board: uacp
  - root task: t_ac2981a9
- A doc-sync Kanban task exists:
  - t_9f0f686b — UACP doc sync: reconcile prototype/lifecycle-skill status

Important current problem:
UACP is documented and scaffolded, but not fully hard-instrumented.
The lifecycle skills and state mutation boundary exist as policy/skill contracts, but a real Hermes Guardian/Heartgate runtime enforcement layer is not yet active.

Immediate objective:
Execute the next governed checkpoint in the correct order.

Checkpoint 1:
Reconcile current UACP docs/config/state drift before designing more features.

Known drift to verify and fix:
- docs/index.md may not fully record that lifecycle skills now exist.
- docs/lifecycle-reference.md may still contain stale bootstrap/deferred wording.
- config/state.yaml still marks lifecycle skill contracts as design_seed.
- dry-run output summary may still say phase: execute and Kanban unbound, while state/current.yaml says resolve/closed and Kanban binding exists.

Required first action:
Read these files first:
- UACP_ROOT/docs/index.md
- UACP_ROOT/docs/lifecycle-reference.md
- UACP_ROOT/config/state.yaml
- UACP_ROOT/state/current.yaml
- UACP_ROOT/state/kanban.yaml
- UACP_ROOT/state/runs/uacp-governed-lifecycle-dry-run.yaml
- UACP_ROOT/.outputs/uacp-governed-lifecycle-dry-run-summary.yaml
- HERMES_ROOT/skills/devops/uacp/uacp-state/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-triage/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-propose/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-plan/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-execute/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-verify/SKILL.md
- HERMES_ROOT/skills/devops/uacp/uacp-resolve/SKILL.md

Path rules:
- UACP_ROOT is the artifact root containing docs/, config/, state/, proposals/, plans/, executions/, verification/, .outputs/, and knowledge/.
- HERMES_ROOT is the parent Hermes workspace.
- Use UACP_ROOT-relative paths inside UACP authority docs/config/state.
- Do not hardcode physical deployment paths inside canonical docs/config/state.
- Do not touch /private.

Execution rules:
- Treat this as a governed UACP task.
- Use the existing Kanban task t_9f0f686b as the active bounded work item if Kanban tooling is available.
- Keep writes inside UACP_ROOT unless explicitly required for skill references.
- Do not create new documents unless docs/index.md creation rules justify them.
- Prefer updating existing canonical docs/config over adding files.
- Verify YAML parses.
- Verify document/state consistency.
- Commit UACP_ROOT after successful verification.

Required council checkpoint:
Before committing the doc-sync change, dispatch or simulate an agent council review with these dimensions:
- Document Authority Reviewer: checks docs/index.md remains the source of truth.
- State Consistency Reviewer: checks current state, run manifest, config/state.yaml, and output summary agree.
- Runtime Enforcement Reviewer: identifies what is still policy-only versus mechanically enforced.
- Kanban Boundary Reviewer: checks Kanban is represented as task substrate, not lifecycle state.
- Drift/Hallucination Reviewer: checks stale wording cannot mislead future agents.

Checkpoint 1 expected output:
- Updated docs/config/state artifacts only as needed.
- A concise verification artifact or summary explaining what changed.
- YAML parse verification.
- Git status summary.
- Commit hash if committed.

After Checkpoint 1:
Stop and report:
- what changed,
- what remains unresolved,
- whether UACP is still policy-only in any critical areas,
- recommended next checkpoint.

Do not proceed automatically into Guardian implementation.

Checkpoint 2, for later:
Design UACP Guardian/Heartgate runtime enforcement.

Guardian design requirements:
- Guardian is the runtime enforcement layer.
- Heartgate is the phase/stage transition decision guard.
- Guardian policy should be runtime-neutral.
- Hermes adapter should use Hermes pre_tool_call capability.
- Future adapters should be compatibility-ready for Codex, OpenCode, and Claude-style hooks.
- Do not port Trustless fixed numbered gates.
- Do not assume all work is coding.
- Keep adaptive gate selection.
- Enforce non-waivable invariants:
  - document authority
  - explicit authority
  - declared side effects
  - write containment
  - privacy/safety constraints
  - traceable state
  - conservative failure
  - visible mutation

Potential files for Checkpoint 2:
- docs/runtime-enforcement.md, only if docs/index.md approves a new canonical doc.
- config/guardian-policy.yaml
- optionally config/runtime-adapters.yaml if needed.

Do not implement Checkpoint 2 until Checkpoint 1 is complete and reviewed.
```

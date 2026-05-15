# Trustless ACP Pattern Correction — Do Not Invent Extra Process

Status: Corrective grounding artifact. This supersedes any invented roadmap additions that are not grounded in Trustless ACP or Anthropic Agent Skills patterns.

## Why this exists

Mike corrected the direction: the answer is not to invent more bootstrap contracts, hygiene docs, or bespoke gates unless Trustless ACP or the Agent Skills pattern shows that such a thing is actually needed. The main source of truth for the refactor pattern should be Trustless ACP's working structure.

## Sources inspected

Trustless ACP:

- `.trustless/docs/control-plane/agent-control-plane.md`
- `.trustless/docs/control-plane/lifecycle-trace.md`
- `.trustless/docs/control-plane/workflow-spec.md`
- `.trustless/docs/control-plane/proposal-schema.md`
- `.trustless/docs/control-plane/branch-worktree-policy.md`
- `.agents/skills/agent-control-plane-propose/SKILL.md`
- `.agents/skills/implementation-plan/SKILL.md`
- `.agents/skills/implementation-execute/SKILL.md`
- `.agents/skills/review-principles/protocol/agent-council.md`
- `.agents/skills/state/SKILL.md`

Anthropic Agent Skills corroboration:

- README: "Skills are folders of instructions, scripts, and resources..."
- `skill-creator/SKILL.md`: bundled resources are `scripts/`, `references/`, assets; progressive disclosure; add scripts when repeated work appears.
- `internal-comms/SKILL.md`: conductor loads the appropriate local example/guideline file.


## UACP superiority and generalization boundary

Important correction: Trustless ACP is not UACP and must not become UACP canon. Trustless ACP is a domain-specific implementation for the Trustless product/project. UACP is the superior abstraction: Universal ACP, generic and unified across domains, task types, and runtime contexts.

Therefore, Trustless ACP is pattern evidence only. Copy structural patterns, not fixed gates or domain assumptions. In particular, UACP VERIFY must remain adaptive: it determines evidence clusters, expertise, council topology, and verification depth from the current artifacts, risks, side effects, authority boundary, and domain context. It must not inherit Trustless's fixed Gate 0/1/2/3 sequence as universal doctrine.

See `16-uacp-superior-universal-correction-20260515.md` for the canonical correction.

## What Trustless ACP actually does

### 1. It defines a lifecycle trace, not a giant roadmap system

Trustless has `.trustless/docs/control-plane/lifecycle-trace.md` with a compact phase table:

```text
Phase | Entry condition | Primary owner | Required checks | Outputs | Exit condition
```

This is the model to copy for UACP skill refactor sequencing: simple phase trace, not invented layers of meta-governance.

### 2. Each phase has an owner skill

Trustless phase trace names the owner:

```text
Propose   -> agent-control-plane-propose
Plan      -> implementation-plan
Implement -> implementation-execute and state skill
Verify    -> verify
Resolve   -> resolve and state skill
```

Pattern for UACP: each refactor phase targets one skill and asks what that skill owns.

### 3. Skills are executable conductors with local support files when justified

Examples:

- `agent-control-plane-propose/SKILL.md`: one file, because the workflow is compact enough.
- `implementation-plan/`: `SKILL.md`, `plan_format.py`, and local references for context loading, architecture agent prompt, phase detail prompt, and plan format spec.
- `implementation-execute/`: `SKILL.md`, helper scripts, and local references for PIV, scheduling, history, context building, parallel execution, and subagent verification.
- `state/`: `SKILL.md`, `state.py`, schema/reference files, and tests; state is a real tool package.

Pattern: file count is discovered from need. Single-file is valid when sufficient. Multi-file is valid when the skill needs reusable local detail or deterministic helpers.

### 4. Trustless uses explicit step checklists inside skills

Examples:

- `implementation-plan`: Step 1 read ACP artifacts; Step 2 load context; Step 3 generate plan; Step 3b standards review; Step 4 write plan; Step 5 structural validation; Step 5b external review; Step 6 initialize state/register artifacts/commit; Step 6b cross-spec awareness.
- `implementation-execute`: preflight; worktree; register artifacts; build work units; execute tasks; post-batch evidence check; PIV; tests; state update.

Pattern: the phase skill's `SKILL.md` should be an executable checklist, not a passive policy note.

### 5. Trustless separates authority by component

Observed rules:

- Proposal records own proposal intent/scope/gates.
- State skill is sole authority for state mutation.
- Guardian preflight gates phase work.
- Runtime adapters are adapters, not authority roots.
- External reviewer selection comes from resolver/config, not bridge skills.

Pattern for UACP refactor: do not create new authority documents unless needed; define owner/authority per skill from the skill's concept.

### 6. Trustless has concrete handoffs and invariants

Lifecycle trace includes authority handoffs:

- Proposal -> Plan: planning cannot redefine proposal intent or skip gates.
- Plan -> Implement: implementation follows plan or explicitly replans; it does not approve its own scope changes.
- Implement -> Verify: verify judges and does not modify implementation code.
- Resolve -> Archive/knowledge: lessons are derived knowledge, terminal state remains lifecycle authority.

Pattern: for each UACP skill refactor, define entry condition, owner, required checks, outputs, exit condition, and what the next skill must not reinterpret.

### 7. Trustless uses Agent Council at specific gates, not everywhere

`review-principles/protocol/agent-council.md` defines:

- when to trigger
- what to check
- domain selection
- execution flow
- fallback independent subagent dispatch
- output formats
- integration points

Pattern: Agent Council is a gate/review protocol with a declared trigger and output format. It is not a default brainstorming machine for every small step.

### 8. Trustless keeps verification read-only

Workflow spec says verification must not modify implementation code, task states, branches, or worktrees. Verification records and judges.

Pattern: UACP `verify` refactor must preserve read-only semantics.

## What to stop doing in this UACP refactor

1. Stop inventing more meta-docs unless they correspond to a Trustless ACP pattern.
2. Stop adding correction files for every correction if the correction should patch the operating method directly.
3. Stop designing abstract governance around the refactor. Use Trustless's concrete lifecycle trace pattern.
4. Stop predefining `references/templates/schemas/scripts` for every skill.
5. Stop treating Agent Council as a generic brainstorming default.
6. Stop expanding router Determine into a destination map for all bloat.

## Corrected next pattern

Before continuing with router Decision, rewrite the roadmap method to match Trustless ACP:

```text
For each skill:
1. Identify original concept and owner role.
2. Record entry condition, required checks, outputs, exit condition.
3. Inspect whether current SKILL.md can be a conductor.
4. Add local support files only if the skill's checklist needs reusable detail or deterministic helpers.
5. Define handoff invariant to the next skill.
6. Use Agent Council only if the skill concept or boundary is ambiguous enough to require multi-perspective review.
```

## Minimal replacement for the invented additions

Instead of creating six more new roadmap docs, add one Trustless-derived pattern note and patch the method artifacts:

- Replace proposed bootstrap/hygiene/council-use inventions with Trustless-derived rules.
- Keep normal file/git workflow as a practical constraint, but do not overbuild it into a new control plane.
- Use a compact lifecycle trace table for the refactor.
- For each skill, produce only the artifacts needed by that skill's phase loop.

## Practical implication for current work

The current Agent Council review is useful as a warning, but its recommendations should be filtered through Trustless ACP. Adopt only what maps to Trustless patterns:

- owner/authority clarity -> yes, from lifecycle trace and state/proposal authority
- independent review -> yes, from Agent Council/external reviewer gates where triggered
- baseline/audit -> yes, as required checks/output validation
- shared-reference quarantine -> yes, as artifact root/authority clarity, but keep it lightweight
- roadmap file caps / moving workspace / forbidding council for fixed skill list -> not directly from Trustless, so treat as optional caution, not doctrine

## Final rule

Ground the UACP revamp in Trustless ACP's actual mechanics:

```text
Lifecycle trace + owner skill + executable checklist + artifact roots + state authority + preflight/review gates + handoff invariants.
```

Do not create an invented meta-governance system around the refactor.

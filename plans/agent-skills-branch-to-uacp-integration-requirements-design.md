# Agent-Skills Branch → UACP Integration Requirements & Design

Status: accepted for canonical cleanup / still under verification  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

## 0. Purpose

This document captures the plan, requirements, and design for integrating the newly created concepts from the `agent-skills` branch into UACP.

The goal is not to copy the branch wholesale. The goal is to make UACP the canonical doctrine and later re-extract a cleaner agent-skills implementation from that stabilized doctrine.

UACP is currently treated as partially broken / not fully self-enforcing, so this work will be run as a **manual UACP drill**:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

The lifecycle will be followed manually and honestly. We will not claim Guardian/Heartgate automation is fully reliable until it is proven.

---

## 1. Ground Truth Inputs

### 1.1 Agent-skills branch

Branch inspected by native Hermes subagents only:

```text
/home/norty/workspace/agent-skills
origin/codex/guardian-agent-council-uacp
```

Observed scale:

- 48 files changed
- approximately +4265 / -4871 lines

Major branch changes:

- `bridge-*` renamed to `runtime-*`
- `bridge-commons` renamed to `runtime-contracts`
- standalone `deep-council` deleted
- `agent-council` becomes the unified council/orchestration surface
- council depth becomes tiered: Tier 0 / 1 / 2 / 3
- new `guardian` skill added
- `council-taxonomy` becomes the glossary anchor inside agent-skills
- `deep-review`, `deep-audit`, `deep-verify`, and `deep-research` become thin wrappers over `agent-council`
- new runtime adapter family appears: `runtime-claude`, `runtime-codex`, `runtime-gemini`, `runtime-opencode`, `runtime-kimi`

### 1.2 Current UACP

Current UACP source of truth inspected:

```text
UACP_ROOT/docs/index.md
UACP_ROOT/docs/constitution.md
UACP_ROOT/docs/lifecycle-reference.md
UACP_ROOT/docs/runtime-enforcement.md
UACP_ROOT/config/*.yaml
UACP_ROOT/state/current.yaml
UACP_ROOT/state/runs/
```

Current UACP already defines:

- lifecycle: `TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE`
- document authority chain
- file-based YAML state model
- `uacp-state` as governed state mutator
- Guardian + Heartgate as runtime enforcement concepts
- review routing
- evidence clusters
- Kanban binding as execution substrate, not phase state

Current UACP is missing or ambiguous on:

- formal council taxonomy
- exact meaning of `agent council`
- exact meaning of `deep council`
- runtime adapter vocabulary
- council tier model
- Devil's Advocate role
- Integration Checker role
- finding-driven review / verification mode
- packetized council exchange
- relationship between domain registry and evidence clusters

---

## 2. Core Decisions From Mike

### D1. UACP remains one system

UACP must not split into separate disconnected concepts such as governance framework, execution methodology, agent-skills doctrine, or Trustless ACP doctrine.

The target is one integrated doctrine where governance, execution, verification, orchestration, and enforcement are parts of the same system.

### D2. Agent Council is native multi-agent orchestration

`agent-council` must not mean only review.

Canonical target definition:

> Agent Council is a runtime-neutral multi-agent orchestration primitive that can be used for planning, proposal critique, execution, verification, audit, research, brainstorming, or review depending on UACP phase, task type, authority, evidence requirements, and selected council tier.

Therefore:

- Agent Council is not a `deep-review` wrapper.
- Agent Council is the multi-agent orchestration substrate.
- Review is only one mode of Agent Council.
- UACP phases invoke Agent Council when useful.

### D3. UACP granularity and council tier are different axes

UACP granularity means:

> End-to-end complexity / risk / governance intensity of the whole request or proposal.

Council tier means:

> Depth of multi-agent orchestration required for a specific council execution.

They are related but not identical.

Examples:

- A high-granularity UACP proposal may default to Tier 2 or Tier 3 council.
- A small sub-check within that proposal may only need Tier 0 or Tier 1.
- A low-granularity task may still use Tier 2 if runtime diversity is specifically needed.

Therefore UACP should map granularity to default council tier, but should not collapse one concept into the other.

### D4. Guardian should merge UACP Guardian, Trustless ACP Guardian, and agent-skill Guardian

The target Guardian is not only the small optional Guardian from the agent-skills branch.

The target Guardian is:

```text
runtime-neutral enforcement kernel
+ policy packs
+ runtime adapters
+ manifest validation
+ authority / side-effect / path checks
+ lifecycle transition protection through Heartgate
```

Policy packs may include:

- UACP policy
- Trustless ACP policy
- future project/domain-specific policies

Runtime adapters may include Hermes, Claude Code, OpenCode, Codex, Kimi, Gemini, and future runtimes.

Hermes is the first host/runtime, not the conceptual boundary.

### D5. Runtime adapters are both UACP-facing and downstream implementation

Runtime adapters are not purely UACP docs and not purely agent-skills implementation.

They sit between doctrine and execution:

```text
UACP doctrine
  -> Guardian / Heartgate policy
  -> runtime-neutral contracts
  -> runtime adapters
  -> Hermes / Claude Code / OpenCode / Codex / Kimi / Gemini
```

Any runtime may act as orchestrator or worker if it obeys UACP contracts.

### D6. Evidence clusters and domain registry should merge

Current difference:

- agent-skills domain registry: mostly static/predefined expert-domain extraction
- UACP evidence clusters: adaptive/dynamic phase-aware evidence selection

Target:

> a unified Evidence-Domain Registry that selects domains, evidence clusters, expert roles, verification requirements, and council shape from phase, artifact type, risk, authority, and runtime context.

The merge should preserve the strengths of both:

- static domains as seed knowledge
- adaptive UACP evidence cluster selection as runtime logic

### D7. Deep wrapper skills should be deprecated / ditched as doctrine

`deep-review`, `deep-audit`, `deep-verify`, `deep-research`, and `deep-council` should not be core doctrine.

Reason:

- UACP phases already provide the lifecycle alternative to `deep-review`.
- `agent-council` can run in different modes and tiers.
- Wrapper skills risk creating parallel doctrine.

Possible compatibility approach:

- keep old deep-* wrappers temporarily as aliases if needed
- mark them as deprecated / compatibility only
- do not make future UACP doctrine depend on them

### D8. UACP path style wins

Canonical docs should use symbolic roots without shell dollar signs:

```text
UACP_ROOT/verification/
UACP_ROOT/outputs/
UACP_ROOT/state/runs/
```

Do not use `$UACP_ROOT` in canonical docs unless writing an actual shell command.

Rules:

- Docs / schemas / policy: `UACP_ROOT/verification/`
- Shell commands: `"$UACP_ROOT/verification"`
- Templates: `{{UACP_ROOT}}/verification/` only if template syntax is explicitly declared
- Avoid `$$UACP_ROOT` entirely unless a specific escaping layer requires it and is documented
- Prefer global, variable-like symbolic roots over repeated magic physical strings inside canonical docs and config.

---


### D9. Granularity is phase-local and compositional

UACP should not treat granularity as only one flat number for the entire run.

Each phase has its own phase-local granularity. Those phase scores compose into the total run granularity together with cross-phase coupling, carried warnings/findings, side effects, and runtime/domain diversity.

Therefore:

- TRIAGE creates an initial estimate, not the final truth.
- PROPOSE / PLAN / EXECUTE / VERIFY / RESOLVE may revise their phase-local granularity as evidence appears.
- Council tier should normally be selected from the current phase-local granularity plus local evidence needs.
- Composite run granularity informs defaults and escalation, but should not force every phase to use the same council depth.
- Each phase should re-evaluate its own granularity at phase entry and phase exit, then pass updated downstream projections to later phases.

## 3. Requirements

### 3.1 Functional requirements

#### FR1. UACP must define Agent Council canonically

UACP must define Agent Council as a native multi-agent orchestration primitive, not a review-only workflow.

Acceptance criteria:

- A canonical UACP document defines Agent Council.
- The definition explicitly supports multiple modes: plan, propose, execute, verify, audit, review, research, brainstorm/design.
- The definition is not tied to Hermes only.

#### FR2. UACP must define council tier separately from granularity

UACP must define:

- granularity score / level = end-to-end governance complexity
- council tier = orchestration depth for a specific council execution

Acceptance criteria:

- A mapping exists from granularity/risk to default council tier.
- The mapping permits overrides.
- The mapping does not imply tier and granularity are identical.

#### FR3. UACP must define runtime adapter vocabulary

UACP must standardize runtime adapter terms and avoid old `bridge-*` vocabulary.

Acceptance criteria:

- `runtime adapter` is defined.
- `runtime` is defined.
- `runtime contract` is defined.
- Old `bridge-*` terminology is either absent from canonical docs or marked legacy.

#### FR4. UACP must define Guardian as runtime-neutral

UACP Guardian must be defined as runtime-neutral and policy-adaptive.

Acceptance criteria:

- Guardian Core is distinct from runtime adapters.
- Guardian can load UACP policy and Trustless ACP policy.
- Hermes is the first supported runtime but not the conceptual limit.
- Heartgate remains lifecycle-transition enforcement.

#### FR5. UACP must define Evidence-Domain Registry direction

UACP must capture the intended merge of domain registry and evidence clusters.

Acceptance criteria:

- UACP states that domain extraction and evidence selection should not remain separate competing systems.
- The merged registry has a target role and migration path.
- Static domain knowledge and adaptive evidence selection are both preserved.

#### FR6. UACP must deprecate deep-* wrappers as doctrine

UACP must not depend on `deep-review`, `deep-audit`, `deep-verify`, `deep-research`, or standalone `deep-council` as canonical execution concepts.

Acceptance criteria:

- The canonical model uses Agent Council modes and tiers instead.
- Legacy wrappers, if retained, are compatibility aliases only.

#### FR7. UACP must preserve path neutrality

UACP canonical docs and schemas must use symbolic roots without implying shell expansion.

Acceptance criteria:

- Canonical docs use `UACP_ROOT/path` style.
- Shell-specific `$UACP_ROOT` only appears in shell command examples.
- No `$$UACP_ROOT` appears unless explicitly justified.

### 3.2 Non-functional requirements

#### NFR1. Ground-truth only

All migration claims must be based on inspected files, branch diffs, or explicitly recorded Mike decisions.

#### NFR2. No hidden doctrine in implementation

Runtime behavior, skills, adapters, and code must derive from UACP docs/config, not become hidden sources of truth.

#### NFR3. Runtime neutrality

The doctrine must be portable across Hermes, Claude Code, OpenCode, Codex, Kimi, Gemini, and future runtimes.

#### NFR4. Minimal canonical-doc sprawl

Do not create many new docs unless each has a distinct durable role.

#### NFR5. Manual drill honesty

This work must not pretend UACP is fully automated or fully repaired. The lifecycle is followed manually as a drill.

---

## 4. Proposed Canonical Document Changes

### 4.1 New document: `docs/orchestration-model.md`

Recommended new canonical doc.

Role:

- define Agent Council
- define council modes
- define council tiers
- define granularity vs tier
- define runtime, runtime adapter, runtime contract
- define diversity dimensions
- define DA / IC roles
- define relationship to UACP phases
- state deprecation of deep-* wrapper doctrine

Why new doc instead of stuffing into lifecycle-reference:

- The concepts are bigger than lifecycle phase text.
- It avoids bloating `docs/lifecycle-reference.md`.
- It gives agent-skills a clear downstream source to implement.

### 4.2 Update: `docs/index.md`

Changes:

- add `docs/orchestration-model.md` to inventory
- add decision log entry for branch-to-UACP doctrine integration
- note that agent-skills branch is source material, not canonical authority

### 4.3 Update: `docs/lifecycle-reference.md`

Changes:

- clarify how each phase can invoke Agent Council
- add granularity vs council-tier distinction
- add manual lifecycle drill note if appropriate
- add finding-driven VERIFY pattern summary

### 4.4 Update: `docs/runtime-enforcement.md`

Changes:

- clarify Guardian Core + Policy Packs + Runtime Adapters
- mention Trustless ACP policy compatibility
- define runtime adapters as UACP-facing/downstream boundary components
- clarify Hermes-first but not Hermes-only

### 4.5 Update: `config/review-routing.yaml`

Changes:

- add default mapping from UACP granularity/risk to council tier
- add override triggers for tier escalation
- add diversity dimensions as routing factors

### 4.6 Update: `config/evidence-clusters.yaml`

Changes:

- add migration note toward Evidence-Domain Registry
- possibly add domain bindings as seed structure
- avoid full merge until current domain-registry shape is reviewed in detail

---

## 5. Manual UACP Drill Plan

### TRIAGE

Question: should this be governed UACP work?

Answer: yes, but manual drill because UACP automation is not trusted enough yet.

Reasons:

- affects UACP doctrine
- affects runtime enforcement vocabulary
- affects agent orchestration model
- affects downstream agent-skills repo
- introduces potential terminology drift if done casually

Triage outcome:

```text
manual_standard_uacp_drill
```

### PROPOSE

Proposal:

> Integrate selected doctrine from the `agent-skills` branch into UACP, making UACP the canonical source for Agent Council, runtime adapters, Guardian policy architecture, and evidence-domain routing.

Scope:

- planning/design docs first
- no canonical docs/config mutation until plan is accepted
- no code port yet
- no external runtime execution

Non-goals:

- do not copy agent-skills implementation code into UACP
- do not finish Guardian runtime implementation in this pass
- do not claim deep-* wrappers are core doctrine
- do not rewrite agent-skills yet

### PLAN

Patch order after this design package is accepted:

1. Create `docs/orchestration-model.md`.
2. Update `docs/index.md` inventory and decision log.
3. Update `docs/lifecycle-reference.md` with phase-to-council relationship.
4. Update `docs/runtime-enforcement.md` with Guardian/runtimes architecture.
5. Update `config/review-routing.yaml` with granularity-to-tier defaults.
6. Update `config/evidence-clusters.yaml` with Evidence-Domain Registry direction.
7. Validate YAML.
8. Review terminology consistency.
9. Record remaining work.

### EXECUTE


### Agent Council implementation expectation

Mike's original intent includes implementation/execution through Agent Council, not only council-based review.

For the later implementation phase, the plan must route non-trivial implementation through Agent Council execution mode, with Hermes Kanban as durable task substrate and council roles handling decomposition, implementation, adversarial checking, integration critique, and synthesis. Single-agent execution is acceptable only for direct/lightweight units where council overhead is unjustified.


Manual document patching only, after Mike approves the plan.

### VERIFY

Verification checklist:

- `docs/index.md` inventory includes any new doc.
- No canonical doc treats agent-skills as authority over UACP.
- No canonical doc uses `$UACP_ROOT` except shell examples.
- `bridge-*` is not introduced as current terminology.
- Granularity and council tier are distinct.
- Agent Council is not review-only.
- Guardian is runtime-neutral and policy-pack based.
- Evidence clusters/domain registry merge direction is captured.
- YAML files parse.

### RESOLVE

Resolution output should decide:

- whether UACP docs are stable enough to refactor agent-skills
- what to do with `codex/guardian-agent-council-uacp`
- whether a future standalone UACP repository is warranted
- whether to save reusable migration workflow as a skill

---

## 6. Open Questions

### Q1. Name of new doc

Recommended: `docs/orchestration-model.md`

Alternative: `docs/council-taxonomy.md`

Current recommendation is `orchestration-model` because the scope includes more than taxonomy.

### Q2. Should UACP use the word `council` for all multi-agent orchestration?

Proposed answer:

- Use `Agent Council` for orchestration primitive.
- Use `council mode` for purpose.
- Use `council tier` for depth.

### Q3. Should deep-* wrappers be deleted immediately downstream?

Proposed answer:

- Not immediately.
- First mark them compatibility/deprecated.
- Remove after UACP-derived agent-council is stable.

### Q4. Should Evidence-Domain Registry become a new config file?

Possible future file:

```text
config/evidence-domain-registry.yaml
```

But for the first pass, update existing `config/evidence-clusters.yaml` with direction only to avoid config sprawl.

---

## 7. Downstream Agent-Skills Extraction Plan

After UACP doctrine is patched and verified:

1. Rebuild `agent-council` around UACP definitions.
2. Make `council-taxonomy` derive from `docs/orchestration-model.md`.
3. Merge Guardian concepts so agent-skills Guardian becomes:
   - Guardian Core wrapper
   - runtime adapter hooks
   - policy-pack loader
4. Rename or remove `bridge-*` vocabulary.
5. Deprecate deep-* wrappers as compatibility aliases.
6. Make artifact paths configurable through symbolic roots:
   - `UACP_ROOT/verification/`
   - `UACP_ROOT/outputs/`
   - `ARTIFACT_ROOT/`
   - runtime-specific fallback roots only when configured.
7. Keep runtime adapters as downstream implementation, not UACP canonical docs.

---

## 8. Risks

### R1. Two-source doctrine drift

Risk: agent-skills and UACP evolve separately again.

Mitigation:

- UACP canonical docs win.
- agent-skills branch is source material only until re-extracted.

### R2. Overfitting to Hermes

Risk: UACP doctrine accidentally bakes in Hermes runtime details.

Mitigation:

- use runtime-neutral vocabulary
- describe Hermes as first host, not boundary

### R3. Over-creating docs

Risk: too many UACP docs create more drift.

Mitigation:

- one new orchestration doc only if approved
- otherwise fold content into existing docs

### R4. Premature code port

Risk: implementation code is ported before doctrine is stable.

Mitigation:

- no Guardian code / hook code / runtime adapter code in first patch
- do not port `guardian.py`, adapter scripts, or branch implementation code until the UACP doctrine stabilizes and the later implementation phase is explicitly approved

### R5. Path syntax confusion

Risk: `$UACP_ROOT`, `$$UACP_ROOT`, and symbolic roots get mixed.

Mitigation:

- canonical docs use `UACP_ROOT/path`
- shell examples use `"$UACP_ROOT/path"`

---

## 9. Immediate Next Step

Review this planning package.

If accepted, proceed to the first canonical patch:

1. create `docs/orchestration-model.md`
2. update `docs/index.md`
3. update `docs/lifecycle-reference.md`
4. update `docs/runtime-enforcement.md`
5. update config files after prose stabilizes
---

## Split package note

This document has been split for review into:

`UACP_ROOT/plans/agent-skills-branch-integration/`

The split package is preferred for review; this file remains the compiled reference packet.

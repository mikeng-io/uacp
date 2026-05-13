# Agent-Skills Branch → UACP Integration Package

Status: draft split planning package  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

---

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

# Agent-Skills Branch → UACP Integration Package

Status: draft split planning package  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty


### D9. Granularity is phase-local and compositional

UACP should not treat granularity as only one flat number for the entire run.

Each phase has its own phase-local granularity. Those phase scores compose into the total run granularity together with cross-phase coupling, carried warnings/findings, side effects, and runtime/domain diversity.

Therefore:

- TRIAGE creates an initial estimate, not the final truth.
- PROPOSE / PLAN / EXECUTE / VERIFY / RESOLVE may revise their phase-local granularity as evidence appears.
- Council tier should normally be selected from the current phase-local granularity plus local evidence needs.
- Composite run granularity informs defaults and escalation, but should not force every phase to use the same council depth.
- Each phase should re-evaluate its own granularity at phase entry and phase exit, then pass updated downstream projections to later phases.

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
UACP_ROOT/.outputs/
UACP_ROOT/state/runs/
```

Do not use `$UACP_ROOT` in canonical docs unless writing an actual shell command.

Rules:

- Docs / schemas / policy: `UACP_ROOT/verification/`
- Shell commands: `"$UACP_ROOT/verification"`
- Templates: `{{UACP_ROOT}}/verification/` only if template syntax is explicitly declared
- Avoid `$$UACP_ROOT` entirely unless a specific escaping layer requires it and is documented
- Prefer global, variable-like symbolic roots over repeated magic physical strings inside canonical docs and config.


### D9. Granularity is phase-local and compositional

UACP should not treat granularity as only one flat number for the entire run.

Each phase has its own phase-local granularity. Those phase scores compose into the total run granularity together with cross-phase coupling, carried warnings/findings, side effects, and runtime/domain diversity.

Therefore:

- TRIAGE creates an initial estimate, not the final truth.
- PROPOSE / PLAN / EXECUTE / VERIFY / RESOLVE may revise their phase-local granularity as evidence appears.
- Council tier should normally be selected from the current phase-local granularity plus local evidence needs.
- Composite run granularity informs defaults and escalation, but should not force every phase to use the same council depth.
- Each phase should re-evaluate its own granularity at phase entry and phase exit, then pass updated downstream projections to later phases.

---

# Agent-Skills Branch → UACP Integration Package

Status: accepted for canonical cleanup / still under verification  
Mode: manual UACP drill, not fully automated lifecycle enforcement  
Source branch: `mikeng-io/agent-skills` → `origin/codex/guardian-agent-council-uacp`  
UACP root: `UACP_ROOT`  
Prepared for: Mike / Norty

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

## 9. Immediate Next Step

Review this planning package.

If accepted, proceed to the first canonical patch:

1. create `docs/orchestration-model.md`
2. update `docs/index.md`
3. update `docs/lifecycle-reference.md`
4. update `docs/runtime-enforcement.md`
5. update config files after prose stabilizes

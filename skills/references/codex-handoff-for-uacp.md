# Codex Handoff for UACP Development

Use this reference when Mike wants to move UACP implementation from Telegram/Hermes chat into Codex because the conversation surface is too constrained.

## Trigger

- User asks for a context transfer form for Codex or another coding agent.
- UACP discussion has accumulated architectural constraints and needs implementation.
- Telegram/Hermes chat should become the control plane, while Codex becomes the bounded implementation executor.

## Handoff Shape

A useful UACP Codex handoff should include:

1. **Read-first file list**
   - `UACP_ROOT/docs/index.md`
   - `UACP_ROOT/docs/constitution.md`
   - `UACP_ROOT/docs/lifecycle-reference.md`
   - `UACP_ROOT/config/state.yaml`
   - `HERMES_ROOT/skills/devops/uacp/SKILL.md`

2. **Stable architecture summary**
   - Lifecycle phases: `TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE`.
   - Phases are stable envelopes.
   - Gates are adaptive, selected by a meta-gate/gate-selection preflight.
   - Invariant gates are non-waivable.
   - Execution is decomposed and bounded through Hermes Kanban.
   - Heavy implementation goes to Codex/Claude Code/OpenCode or delegated workers.
   - Gate selection becomes closed-loop using similar scenarios and outcome-ranked prior gates.

3. **Implementation boundaries**
   - Keep initial writes inside `UACP_ROOT` unless explicitly approved.
   - Do not touch `/private`.
   - Do not hardcode model names.
   - Do not use fixed numbered gates.
   - Do not assume all tasks are software engineering.
   - Do not put gate-learning artifacts into Honcho memory.
   - Do not make Cortex the sole knowledge owner.

4. **First Codex task recommendation**
   - Implement Stage 1 and Stage 2 only:
     - Create UACP artifact directories.
     - Create initial config/docs files.
     - Define schemas/examples for gate-selection, evidence-cluster, learning, and phase-transition artifacts.
   - Do not implement the standalone Knowledge Bank service yet.

## Canonical First Prompt Skeleton

```text
You are continuing UACP development for Mike/Norty.

Read these files first:
<read-first file list>

Project: UACP — Universal Agent Control Plane for Hermes/Norty.

Key architecture:
- Lifecycle phases are PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE.
- Phases are stable envelopes.
- Gates are not fixed; each phase decision runs an adaptive meta-gate.
- The meta-gate selects required/optional/not_applicable/generated evidence clusters based on domain, artifact type, risk, side effects, prior scenarios, domain templates, and invariants.
- Invariant gates are non-waivable.
- Execution should be decomposed and bounded through Hermes Kanban.
- Software VERIFY gates are also adaptive; do not implement fixed software-only checklists.
- Gate selection should eventually be closed-loop via a Knowledge Bank.
   - Initial learning artifacts live under `UACP_ROOT/knowledge/`.
- Honcho is for personal/peer memory, not high-volume gate-learning artifacts.
- Cortex can consume/produce knowledge via API but should not be the sole owner.
- Do not hardcode model names.
- Do not touch /private.

Task:
Produce and implement Stage 1 and Stage 2 only.

Stage 1:
Create `UACP_ROOT` with `proposals/`, `plans/`, `executions/`, `verification/`, `.outputs/`, `knowledge/{scenarios,gate-templates,lessons,indexes}`, `config/`, and `docs/`.

Stage 2:
Create config/docs files for evidence clusters, gate selection, phase transitions, review routing, memory policy, constitution, first principles, alignment spec, and lifecycle reference.

Also define schemas/examples for gate-selection, evidence-cluster, learning, and phase-transition artifacts.

Constraints:
- Keep writes inside `UACP_ROOT` unless explicitly asked.
- Do not implement the full standalone Knowledge Bank service yet.
- Verify by listing created files and checking YAML parses.
```

## Pitfall

Do not compress the handoff into a vague instruction like “continue UACP.” Codex needs explicit read-first files, boundaries, staged scope, non-goals, and verification commands to avoid broad or destructive implementation.

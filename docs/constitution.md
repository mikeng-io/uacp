# UACP Constitution

UACP is a runtime-neutral governance framework for AI agent work. It provides stable lifecycle phases and adaptive evidence selection without turning every task into the same checklist.

## Scope

UACP governs work across domains: software, infrastructure, research, writing, marketing, productivity, lifestyle planning, creative work, operations, and mixed-domain tasks.

UACP does not assume all work is software engineering. Software checks are domain templates selected by context, not universal gates.

## Lifecycle Envelope

The workflow starts with `TRIAGE`, then enters the stable lifecycle phases when governance is warranted:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Triage is scope calibration, phase-local and composite granularity estimation, and governance routing. It can route `direct` work to action without a full governed run, or require human involvement when authority, side effects, or phase-local/composite granularity justify it. The evidence inside each later phase is adaptive. Before a phase transition, UACP runs a gate-selection preflight that selects required, optional, not applicable, or generated evidence clusters.

## Non-Waivable Invariants

These invariants cannot be waived by the meta-gate:

- Document authority: runtime behavior, skills, configs, and execution artifacts derive from governed documents.
- Explicit authority: requested work and side effects need clear authorization.
- Declared side effects: file, system, service, human, publication, and external effects must be stated.
- Write containment: writes remain inside declared workspaces and paths.
- Privacy and safety constraints: trust boundaries and sensitive data are respected.
- Traceable state: state changes trace to artifacts, authority, and phase decisions.
- Conservative failure: missing critical evidence blocks instead of being guessed around.
- Visible mutation: hidden state changes and unrecorded self-healing are forbidden.

## Decision Rule

A phase transition is permitted only when:

- the relevant active documents and configs agree,
- invariant checks are pass,
- required evidence clusters are pass or explicitly accepted warn,
- blockers are resolved or scope is changed,
- deferred work is accepted by the next phase with a recorded owner and condition,
- state and artifacts are traceable under the UACP artifact root.

## Knowledge Boundary

UACP learning artifacts belong under `knowledge/` within `UACP_ROOT` initially. Honcho is for personal and peer memory, not a high-volume store for gate outcomes. Cortex can consume or produce knowledge through an API, but it should not be the sole owner of the shared knowledge substrate.

Stage 1 and Stage 2 do not implement the standalone Knowledge Bank service.

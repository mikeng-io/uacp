# Frontmatter by skill `kind`

> **Read when** creating or refactoring a skill and you need the exact frontmatter
> fields for its `kind`. Companion to `../SKILL.md`.

Invocation name comes from the skill **directory** name, not `name:`; `name:` is a display label. Avoid Claude-Code-reserved frontmatter keys (`context`, `allowed-tools`, `model`, `effort`, `agent`, `hooks`, `paths`, …) except for their real CC meaning.

`name` and `description` are required for every kind. `description` is the trigger:
state what the skill does AND when to use it.

## `kind: kernel`
```yaml
name: uacp-core
description: >
  Runtime-neutral UACP core — policy, Guardian evaluation, Heartgate transitions,
  audit, shared filesystem utilities. Imported by runtime adapters; not invoked.
kind: kernel
version: 1.0.0
```

## `kind: lifecycle`
```yaml
name: uacp-execute
description: Use when dispatching bounded UACP work through Hermes Kanban or delegated workers.
kind: lifecycle
phase: execute
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
```
No `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` — codified grammar
is authoritative (see `../SKILL.md` → "no authority mirrors").

## `kind: reference`
```yaml
name: domain-registry
description: Reference library of domain definitions used by lifecycle and bridge skills to select expert agents. Read via the Read tool; not invocable standalone.
kind: reference
```

## `kind: orchestration`
```yaml
name: uacp-council
description: Use when convening an Agent Council for multi-lens review during any phase.
kind: orchestration
```

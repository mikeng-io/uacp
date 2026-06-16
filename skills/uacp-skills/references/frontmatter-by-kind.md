# Frontmatter by skill `kind`

> **Read when** creating or refactoring a skill and you need the exact frontmatter
> fields for its `kind`. Companion to `../SKILL.md`.

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
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read doctrine + artifact schemas only)"
```
No `allowed_tools` / `forbidden_tools` / `phase_exit_invariants` — codified grammar
is authoritative (see `../SKILL.md` → "no authority mirrors").

## `kind: reference`
```yaml
name: uacp-bridge
description: Reference adapter contract for dispatching to external runtimes. Read via the Read tool; not invocable standalone.
kind: reference
context: reference
```

## `kind: orchestration`
```yaml
name: uacp-council
description: Use when convening an Agent Council for multi-lens review during any phase.
kind: orchestration
```

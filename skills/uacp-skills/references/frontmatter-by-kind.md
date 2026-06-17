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

### Sanctioned variant: cross-phase lifecycle skill

A `lifecycle` skill that is **the** cross-phase state mutator (not bound to a
single phase) MAY use `phase: '*'` plus an optional `cross_phase: true` flag, and
MAY add a one-line `note:` justifying the wildcard. This is reserved for the
single skill that owns state mutation across every phase (`uacp-state`); ordinary
lifecycle skills stay bound to their one `phase`.

```yaml
name: uacp-state
description: Use when mutating UACP state, updating run manifests, current pointers, or tombstones.
kind: lifecycle
phase: '*'
cross_phase: true
note: single cross-phase state mutator; per-phase admissibility comes from the active phase's allowed_tools.
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
```

## `kind: reference`
```yaml
name: uacp-bridge
description: Per-runtime dispatch contract and adapter specs consumed by lifecycle and orchestration skills. Read via the Read tool; not invocable standalone.
kind: reference
```

## `kind: orchestration`
```yaml
name: uacp-council
description: Use when convening an Agent Council for multi-lens review during any phase.
kind: orchestration
```

---
name: uacp-council
description: Unified multi-agent orchestration skill for UACP. Takes a tier parameter (0/1/2/3) that scales from a single agent through in-runtime sub-agent dispatch up to cross-runtime councils with debate. Replaces the historical separate skills "agent-council", "runtime-council", and "deep-council" — all are tiers of the same operation. Supports review, audit, verify, research, planning, implementation, and brainstorm/design modes.
kind: orchestration
location: managed
dependencies:
  - uacp-council-taxonomy
  - domain-registry
  - uacp-bridge
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - Write
  - Bash(mkdir *)
  - Bash(ls *)
  - Bash(which *)
  - Bash(cat *)
  - Bash(python3 *)
---

# Agent Council: Unified Tier-Parameterized Council

Execute this skill to orchestrate agent work at any scale, from a single agent up to a cross-runtime council with debate. **The tier parameter selects the scale; `task_type` selects the authority profile.** Review, verification, planning, implementation, research, and future auto-orchestration are all routed through this same council surface. Do not invoke separate council skills — there is only one.

Guardian, when installed, enforces the council's registration manifest and output authority. It does not decide orchestration; it blocks malformed or unauthorized registrations before `uacp-council` dispatches work.

## Phase 0: Orientation
Read the vocabulary first:

```
Read: [skills-root]/uacp-council-taxonomy/SKILL.md
```

`uacp-council-taxonomy` is this suite's authoritative glossary — tier model, runtime vocabulary, diversity dimensions, and anti-patterns. Every step below assumes that vocabulary.

`[skills-root]` is the parent of this skill's directory — resolve with `ls ../` from this skill's location.

## Quick Start
1. **Register** — read `phase-1-registration.md` and build `council_manifest`.
2. **Route** — read `phase-2-routing.md` to select `tier` and `ic_tier`.
3. **Plan** — read `phase-3-domain-planning.md` to resolve domains and prompts.
4. **Dispatch** — read `phase-4-dispatch.md` to run Tier 0/1/2/3 or IC-hoist.
5. **Synthesize** — read `phase-7-synthesis.md` to merge outputs and apply verdicts.
6. **Save** — read `phase-8-artifact.md` and write the artifact to `.uacp/councils/`.

Also read `modes.md`, `finding-driven-mode.md`, `tier-reference.md`, `devils-advocate.md`, and `integration-checker.md` before constructing role prompts or interpreting results.
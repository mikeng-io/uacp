---
type: analysis
title: Blast radius — consumers that break if the fields are naively emptied, and the tests that lock the fix
description: The build-constraint map from the subagent audit. Enumerates every downstream consumer of task_description/context_summary, the two HARD breaks (debate phase-1 sole task line; deep-research/ultracode CLI query), the graceful degrades, the projection-not-manifest rule the whole split depends on, and the tests that must exist to lock separation. No schema/test currently requires these fields non-empty.
tags: [blast-radius, consumers, debate, deep-research, projection, tests, build-constraints]
timestamp: 2026-07-10
edges:
  - {dst: 10-minimal-non-leading-dispatch, rel: depends_on, provenance: derived}
---

# Blast radius

This node exists because the naive "empty the fields" patch would have silently broken things the
correctness fix ([[10-minimal-non-leading-dispatch]]) must handle. It is the build-constraint map:
what consumes these fields, what breaks, and the tests that lock the fix. Grounded in the
2026-07-10 subagent audit (independent grep + read of the skills tree).

## No schema/test currently guards these fields

A grep of `tests/`, `scripts/`, `config/` for `task_description` / `context_summary` returned **zero**
requiring-non-empty hits. Heartgate/Guardian pre-flight checks `scope_set`, `domains_set`, `task_type`,
`mode` — not these. So emptying will **not** fail CI — which is the danger: the breaks below are
silent (degraded LLM prompts), not loud (test failures). The tests at the end are what convert them to
loud.

## Two HARD breaks — must be fixed as part of the change

1. **Debate protocol's sole task line.** `skills/uacp-debate/references/phase-1-investigation.md` uses
   `Task: {context_summary}` as its *only* task line, and uacp-debate has **no `task_description`
   field at all**. When Claude's Tier >=2 Layer-2 runs as debate-protocol, emptying `context_summary`
   hands debate participants an empty **`Task:`** line. (Two precisions from the cross-provider council:
   (i) participants still receive `Scope:` / `Domains:` on adjacent lines, so this is an empty *objective*,
   not total starvation — but still a foot-gun; (ii) Claude's Layer-2 is **not always** debate-protocol —
   it is Workflows for tier >=3 / research / audit and falls back to the Task Tool otherwise
   (`claude.md`), so the break is real specifically on the debate-protocol path, which this claim should
   not overstate as "always.") **Fix:** the debate template must take a neutral task framing derived from
   `mode` + the engagement spec (the change pointer from [[10-minimal-non-leading-dispatch]]), surviving
   an empty narrative.

2. **deep-research / ultracode CLI query.** `skills/uacp-bridge/references/claude.md` passes
   `task_description` as the literal `/deep-research {task_description}` and `ultracode: {task_description}`
   query, and the workflow-selection condition keys on `task_description contains 'ultracode'`. At
   Tier >=3 / research / audit these fire with an **empty query**. **Fix:** for the workflow path,
   substitute the engagement spec (scope + change pointer) as the query; drop/replace the
   `task_description contains 'ultracode'` selection clause.

## Graceful degrades — survive if the engagement spec is preserved

These consumers lose the narrative but retain `scope` + domain + focus + the change pointer, which is
exactly the independence [[10-minimal-non-leading-dispatch]] wants — **provided** the change spec is
real (not blank):

- `uacp-bridge/SKILL.md` Agent Prompt Template (`TASK:` / `CONTEXT:` lines) and the newly-added-domain
  Round N prompt.
- `codex.md` multi-agent coordinator (`Context:` — retains scope + per-domain focus).
- `claude.md` teammate / DA / IC prompts (`Context:`); the domain-expert teammate's `Your task:` needs
  a scope-derived fallback so an empty line does not read as *withheld* narrative.
- `uacp-council/experts/devils-advocate.md`, the domain registry `## Context` sections — DA/IC work off
  other experts' findings; context loss is minor.

**Rendering rule (applies everywhere the narrative is stripped):** never emit a dangling empty
`TASK:` / `CONTEXT:` / `## Context` line — render an explicit *"(context withheld for reviewer
independence — derive from scope + diff)"* so a downstream model reads deliberate withholding, not
corrupted/missing input. (Stated once here; [[10-minimal-non-leading-dispatch]] references it.)

## Upstream origin (not a break — reinforces the projection rule)

The field is *produced* upstream, not only consumed: `skills/uacp-context/references/context-report-schema.md`
defines `context_report.context_summary`, which uacp-council reads to build the manifest. This is upstream
of the projection and unaffected by the change — it is noted only for completeness, and because it
*reinforces* the rule below: the narrative legitimately exists at the manifest/report layer; only the
external-runtime **projection** strips it.

## The projection-not-manifest rule (the split depends on it)

The `runtime_input` projection (`phase-4-dispatch.md` Step 6.2.3) is the **only** place these fields
cross into an external runtime; Tier 0/1 build prompts directly from the council manifest. Therefore:

> Empty/strip **only the projection**. Never empty `council_manifest.context_summary`
> (`phase-1-registration.md`) or the saved artifact frontmatter (`phase-8-artifact.md`,
> `artifact-output.md`).

If the manifest field is emptied, **provenance/audit trail degrades with no upside** (synthesis/dedup
do not depend on these fields — dedup keys on finding `domain`+`title`+`description` — but the artifact
loses its record of what was reviewed). The same prompt templates are reused by an external runtime's
*internal* Tier-1, so the emptiness must be carried by the projected data, not by editing shared
templates.

## Tests that must exist (none do today)

1. **Projection strips narrative, keeps spec:** a Tier >=2 `review`/`audit` `runtime_input` carries no
   leading narrative **and** a resolvable change pointer; a Tier 0/1 in-runtime prompt retains full
   context. Locks the separation the whole bundle depends on.
2. **Debate template survives empty narrative:** phase-1 debate task line is non-empty given an empty
   `context_summary` + a present engagement spec.
3. **Workflow query is non-empty:** deep-research/ultracode dispatch builds a non-empty query from the
   engagement spec when `task_description` is stripped.
4. **grounding_provenance fail-close** ([[11-grounding-provenance]]): a report with unresolvable
   provenance is rejected/downgraded at synthesis; a resolvable one passes.

These are the arbiters [[10-minimal-non-leading-dispatch]] defers build detail to — per the design
convention, the design states the model; the tests pin the exact behavior.

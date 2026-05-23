# Agent Council + UACP Integration Lessons

Use when evolving UACP doctrine, orchestration, lifecycle routing, or execution methodology.

## Planning artifact shape

Do not compress major UACP doctrine/integration work into one giant plan. Produce a split planning package under a directory, with separate files for:

- index / non-negotiables
- ground truth
- decisions
- requirements
- design
- execution plan
- verification / resolution

Keep a compiled reference packet only as a convenience pointer, not the primary review surface.

## Agent Council scope

Agent Council is not review-only. For non-trivial implementation, treat it as the deliberative execution topology:

- PLAN selects council mode/tier and execution topology.
- Agent Council handles decomposition, role assignment, critique, integration checking, and synthesis.
- Kanban records durable tasks, dependencies, status, and handoffs.
- Runtimes/tool adapters/evidence services perform bounded work and return evidence.

## Cognitive/control-plane separation

Clarify these layers explicitly when patching UACP:

- UACP = governance cognition: should/may/must, authority, risk, phase, side effects, human involvement, evidence obligations.
- Agent Council = deliberative cognition: think together, design, challenge, synthesize.
- Kanban = coordination memory: remember, coordinate, track, hand off.
- Runtimes = worker cognition/execution loops.
- Tool/evidence adapters = observe, act, scrape, search, compute, produce evidence.
- Guardian/Heartgate = enforce boundaries between planes.

Avoid the category error of making Kanban the thinker, Agent Council the state database, tools autonomous authorities, or phase labels a substitute for deliberation.

## Granularity model

Granularity should be phase-local and compositional, not only one intake score:

- Each phase records `entry_estimate`, `exit_actual`, `delta_reason`, and `downstream_projection`.
- Composite run granularity derives from max phase score, cumulative complexity, cross-phase coupling, carried findings/warnings, side effects, and runtime/domain diversity.
- TRIAGE creates an initial estimate, not final truth.
- Later phase reassessment can trigger human involvement, tier escalation, or re-plan/checkpoint.

## Human involvement

Human involvement can be selected by TRIAGE or by later phase-local reassessment. Trigger it for unclear authority, irreversible/external side effects, high phase-local/composite granularity, unresolved HIGH/CRITICAL findings, or Guardian/Heartgate inability to classify a protected action safely.

## Execution/evidence surfaces

Distinguish:

- `agent_runtime`: Hermes, Claude Code, Codex, OpenCode, Kimi, Gemini, etc.
- `tool_adapter`: browser automation, Puppeteer/Playwright, computer use, terminal, OCR, scripts.
- `evidence_service`: Firecrawl, Tavily, SearXNG, web search, scraping APIs, transcripts, domain data providers.
- `control_substrate`: Hermes Kanban.

Do not call every execution surface a runtime unless it hosts an autonomous agent loop.

## Context preservation and Kanban handoff

For long UACP integration programs, assume chat context will be lost. Do not rely on one mega-document to preserve context. Build a numbered package under `UACP_ROOT/plans/<topic>/` with:

- `00-index.md`
- `01-current-state.md`
- `02-cognitive-model.md`
- `03-open-risks-and-decisions.md`
- `04-task-breakdown.md`
- `05-kanban-delegation.md`
- `06-verification-and-measurement-gates.md`
- `07-session-resume-guide.md`

Then create or import a Kanban graph from that package when the remaining work is multi-session. Kanban is coordination memory only: store root/child task IDs, dependencies, allowed files, acceptance criteria, and verification gates. UACP artifacts remain the authority; Kanban tracks execution continuity.

## Skill and validator propagation

When UACP doctrine/config changes, check whether lifecycle skills and validators also need updates. Updating docs alone is incomplete if active skills still contain stale assumptions. Patch the relevant lifecycle skills and shared contract, then create or update lightweight validation scripts when artifact schemas changed.

At minimum, verify:

- lifecycle skills mention phase-local/composite granularity when relevant,
- PLAN/EXECUTE skills preserve the UACP / Agent Council / Kanban cognitive split,
- VERIFY checks canonical finding states and council synthesis artifacts,
- state skills preserve run-manifest fields without letting Kanban become phase state,
- validators catch missing phase-local granularity, invalid finding states, and missing council synthesis fields.

## Verification posture

For major UACP doctrine changes, run a local Agent Council before RESOLVE. Include at least:

- Primary Reviewer
- Devil's Advocate
- Integration Checker

Treat self-verification as provisional. If the same process wrote and verified the change, record that limitation and require council/human review before final RESOLVE.

## Common cleanup items after doctrine patches

Check for:

- stale council vocabulary in alignment docs (`local council`, `deep council`) and map it to tiers
- phase-transition schema/prose mismatches (`routing_outcome`, `terminal_kind`, disposition names)
- undefined `council_synthesis_artifact` schema
- config stubs accidentally described as implemented features
- non-standard finding states; use canonical states like `accepted_risk`
- Guardian bypasses under-rated as warnings rather than high accepted risk/blockers

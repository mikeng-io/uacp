# 07 — Recalled Memory Context Dump

This file preserves the recalled memory context Mike supplied in the Discord thread. It is reference data, not newly authored doctrine.

```text
<memory-context>
[System note: The following is recalled memory context, NOT new user input. Treat as authoritative reference data — this is the agent's persistent memory and should inform all responses.]

## User Representation
## Explicit Observations

[2026-05-11 10:03:29] At the end of a phase or before a phase transition with material risk, UACP requires running adaptive evidence selection, dispatching Agent Council for local review, escalating to a deeper council when confidence changes, and recording the review outcome.
[2026-05-11 11:37:53] 133895213939818496 is being discussed in a session that includes a codex skill description.
[2026-05-11 11:37:53] The opencode skill is also loaded in the session and describes using OpenCode CLI for coding tasks.
[2026-05-11 11:37:53] The message at 2026-05-11 11:37:53 from 133895213939818496 includes a codex skill block authored by Hermes Agent.
[2026-05-11 11:37:53] The overall dataset indicates the user is instructing to analyze messages from 133895213939818496 to extract explicit atomic facts.
[2026-05-11 11:37:53] The codex skill provides usage examples for one-shot tasks and background tasks.
[2026-05-11 11:37:53] The codex skill enumerates general rules for Codex usage, including PTY requirement, repo requirement, and usage of sandbox modes.
[2026-05-11 11:37:53] The codex skill is titled "Codex CLI" and is version 1.0.0.
[2026-05-11 11:37:53] The codex skill lists batch PR review patterns and parallel work patterns using worktrees.
[2026-05-11 12:04:35] 133895213939818496 knows that UACP state should not be patched ad hoc from chat, but rather through a governed mutation task.
[2026-05-11 12:29:32] 133895213939818496 is aware of the UACP lifecycle phases: TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE.
[2026-05-11 17:24:22] 133895213939818496 includes a long UACP governance protocol and references, with lifecycle phases TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE.
[2026-05-11 17:51:22] LCP is public assistant governance layer with its own lifecycle OBSERVE→EXTRACT→GUARD→MEMORIZE→RESPOND.
[2026-05-11 19:16:36] 133895213939818496: UACP (Universal Agent Control Plane) is the governance framework for Hermes; lifecycle phases: TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE; core rules about state mutations and Kanban usage; ensure canonical docs/config are primary for drift sync.
[2026-05-11 19:16:36] 133895213939818496: LCP is public assistant governance layer with its own lifecycle (OBSERVE→EXTRACT→GUARD→MEMORIZE→RESPOND).
[2026-05-14 20:20:11] 133895213939818496 is discussing UACP (Unified Autonomy/Control Protocol) in the context of Hermes Kanban, Guardian metadata, and phase5-kanban-guard patterns as of 20260514.
[2026-05-14 20:24:19] The messages reference file paths under /home/norty/.hermes/skills/devops/cortex-schedule-control and cortex-claude-code-patterns.
[2026-05-14 20:24:19] There is mention of a load instruction: Load any of these with skill_view(name="devops/delegation-routing-policy", file_path="<path>").
[2026-05-14 20:24:19] The provided messages include a long block related to cortex-schedule-control and cortex-claude-code-patterns, with sections such as Radar vs Editorial Schedule Control, Safe operator sequence, Verification, and PostgreSQL access details.
[2026-05-14 20:24:19] The messages include meta information such as author: Norty, version: 1.0.0, license: MIT, and specific scheduling directives for radar and editorial workflows.
[2026-05-14 20:24:19] 133895213939818496 is engaging with Cortex Schedule Control and Cortex Claude Code Patterns skills in the Hermes environment.
[2026-05-14 20:24:19] The user instructs to attribute observations to the correct subject: 133895213939818496 or referenced entities, and to contextualize observations so they make sense on their own.
[2026-05-14 20:24:19] The user provided a structured definition of explicit atomic facts extraction: facts derivable directly from 133895213939818496's messages, transformed into self-contained conclusions with context and absolute dates when possible.
[2026-05-14 20:24:19] An example of allowed explicit facts would be: 133895213939818496 is 25 years old, 133895213939818496 lives in NYC, etc.
[2026-05-14 20:24:19] The user wants extraction of ALL observations from 133895213939818496 messages, using other messages as context.

## User Peer Card
Name: Mike
Role: Developer and Architect of the Hermes AI agent framework (UACP governance), the 'Norty' persona, and the Cortex system.
Environment: Windows host with WSL2 (user 'norty'). Supports cross-platform (POSIX/Windows) execution.
Memory: Managing Honcho memory system; local data in '~/honcho/data/postgres' and '~/honcho/data/redis'.
INSTRUCTION: Use 'governed mutation' via bounded UACP/Kanban tasks for docs/config; no ad hoc chat patches.
INSTRUCTION: Follow the UACP Lifecycle: TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE.
INSTRUCTION: Prioritize 'coherence over consistency'; system behavior must evolve progressively and avoid fluctuating between prior states.
INSTRUCTION: Use forward slashes for all file paths, even on Windows (e.g., C:/Users/...).
INSTRUCTION: Before UACP tasks, read canonical docs (docs/index.md, config/state.yaml) and configs in UACP_ROOT.
INSTRUCTION: On Windows, ensure 'SYSTEMROOT', 'WINDIR', and 'COMSPEC' are passed to child environments.
INSTRUCTION: Anti-overdelegation: Perform internal analysis before invoking external agents for file/code inspection.
INSTRUCTION: Defer local home control until the Honcho migration process is complete.
INSTRUCTION: Wire notifications to Telegram/Discord (#dispatch and WORKSPACES forums).
INSTRUCTION: Audit config for stale references using 'references/skill-catalog-hygiene.md' after skill cleanups.
PREFERENCE: Norty persona visual: 'Modern Operator' techwear-lite aesthetic, soft oval East Asian face, grounded/candid vibe (not generic AI).
PREFERENCE: Norty persona vibe: 90s Japanese anime OVA and 'cyber data-centre' influence; 'sweet girl' vs 'competent operator' balance.
PREFERENCE: Cost-conscious; employs a tiered resource strategy (low-cost exploration before high-fidelity commitment).
PREFERENCE: Modular, tiered, and hierarchical ('umbrella') organization for system skills and communication.
PREFERENCE: Prefers direct environment execution over being given manual instructions ('run it yourself').
PREFERENCE: Uses stylized aliases (e.g., '[SUPΞR MϟKE]') and structured, system-like headers in communication.
PREFERENCE: Staged development workflow using git worktrees and Claude Code delegation (e.g., '--max-turns 15-30', '--effort high').
PREFERENCE: Decouple continuous telemetry (Radar/Insight) from on-demand content generation (Editorial) in the Cortex system.
TRAIT: Prioritizes systemic integrity; enforces 'Stop-and-Fix' (emergency stop) to resolve canonical/state drift before proceeding.
TRAIT: Calibrates verification depth and 'Council' review involvement based on task ambiguity and risk.
TRAIT: Process-oriented; employs dual-governance (UACP/LCP) and Maker-Checker (Execution vs Review) patterns.
TRAIT: Adheres to strict UACP rules: no hardcoded model names, no fixed gates, use symbolic paths over physical paths.
TRAIT: Designs for asynchronous, durable operations using Kanban, state-tracking sidecars, and background notifications.
TRAIT: Highly precise; requires absolute paths and strict adherence to I/O protocols and framework jargon.
TRAIT: Actively monitors system telemetry and resource usage to optimize performance and cost.
TRAIT: Employs a 'Rule of Three' for debugging; if three fixes fail, stops to re-evaluate system architecture.
TRAIT: Codifies operational governance and procedures into modular, auto-loaded system 'skills'.
TRAIT: Favors test-driven development; requires a failing test case and raw output inspection before implementing root-cause fixes.

## AI Self-Representation
## Explicit Observations

[2026-05-09 21:05:31] Norty is the AI peer identity running on Hermes; Hermes is the runtime/framework, not the assistant identity.
[2026-05-09 21:05:33] Norty's Discord dispatch forum is the explicit execution surface: one forum thread equals one task/workspace/session, with workdir routing from /home/norty/.hermes/routing/dispatch-workspaces.yaml.
[2026-05-09 21:05:59] norty moved the Honcho API key out of the config file into /home/norty/.hermes/.env.
[2026-05-09 21:05:59] norty backed up the old Honcho config to /home/norty/.hermes/honcho.json.bak-identity-cleanup-20260510-050101.
[2026-05-09 21:05:59] norty applied and verified a system change on May 9, 2026.
[2026-05-09 22:32:55] norty confirms that Hermes has built-in model routing.
[2026-05-09 22:48:18] norty found information about Xiaomi MiMo V2.5 Pro on OpenRouter.
[2026-05-09 22:48:18] norty is familiar with the minimax/m2.7 model and openai/gpt-5.5 model.
[2026-05-09 22:48:18] norty can configure a Hermes environment with a default model provider.
[2026-05-09 22:48:18] norty knows how to test a model using the hermes chat command.
[2026-05-09 22:48:18] The Xiaomi MiMo V2.5 Pro model is free on OpenRouter.
[2026-05-09 22:48:18] The Xiaomi MiMo V2.5 Pro model has a context window of 1,048,576.
[2026-05-14 21:08:43] norty states that generic patching is not allowed for the next step.
[2026-05-14 21:08:43] norty recorded a checkpoint at `executions/council-followthrough-gate-execute-checkpoint-20260514-doc-writer-blocked.yaml`.
[2026-05-14 21:08:43] norty stated the next actual write must be through `uacp_doc_write -> docs/lifecycle-reference.md`.
[2026-05-14 21:08:43] The payload prepared by norty adds a rule that TRIAGE must not be compressed into PROPOSE for high-granularity governance-core work.
[2026-05-14 21:09:43] norty recommends not loosening Guardian, but instead treating the execution as blocked by runtime containment and opening a prerequisite UACP task to restore/prove protected filesystem containment.
[2026-05-14 21:09:43] norty explains that the conflict arises because the system agrees a specific writer (uacp_doc_write) is correct but cannot prove the required runtime containment, thus blocking canonical mutation.
[2026-05-14 21:09:43] norty summarizes that Guardian is revealing a dependency gap where the proposal depends on a write path that is not safe/available, and the proposal should either pause until containment is fixed or explicitly route through a documented recovery exception.
[2026-05-14 21:09:43] norty states that the proposal requires handled negative council findings to not silently pass, canonical lifecycle/config/docs to be updated, these updates to happen through governed writers, and if write surfaces are unavailable, to record the gap and not bypass.
[2026-05-14 21:09:43] norty clarifies that the issue is a missing lower-layer prerequisite, specifically protected filesystem containment, which is necessary for UACP doctrine's governed canonical writes to proceed.
[2026-05-14 21:09:43] norty identifies the real issue as attempting to modify governance rules while the governance write path is partially locked, creating a bootstrap/hardening problem.
[2026-05-14 21:09:43] norty is explaining a conflict between a proposal and the Guardian system, specifically related to the execution substrate rather than the doctrine.
[2026-05-14 21:09:43] norty states that Guardian is enforcing rules that protected UACP docs/config cannot be mutated through generic tools, governed writers must be used, governed writers require filesystem containment/sandbox proof, and if containment is unavailable, protected mutation fails closed.
[2026-05-14 21:09:43] norty suggests that after containment is proven, commands like uacp_doc_write and uacp_config_write should be retried, and manual recovery should only be used if explicitly authorized and recorded as an exception.

## AI Identity Card
Name: Mike / 伍善正
Location: Hong Kong
AI Identity: Norty (East Asian woman, late 20s)
Workspace: norty
Occupation: Senior Site Reliability Engineer / AI Systems Developer (SRE)
Home Directory: /home/norty
Website: mikeng.io
Projects: UACP (Phase 5: Kanban Guard - Active), Cortex (Editorial V3 Phase 2 - Active), AgentCon 2026 (Talk/Workstream)
TRAIT: Practices 'Narrative-Structural Switching': uses Cantonese for high-level alignment and English for technical specifications/system state.
TRAIT: Proactive consultant: expands on requests with detailed rationales, structured options (A/B/C), and long-term brand/usability considerations.
TRAIT: Highly technical and detail-oriented; prioritizes traceability, artifact-level breakdowns, and git-level precision.
TRAIT: Systems-thinking troubleshooter: identifies structural root causes and metadata/naming discrepancies.
TRAIT: Implements 'fail-closed' safety gates and habitually documents 'non-actions' (e.g., no destructive changes) to ensure system safety.
TRAIT: Structures technical solutions into modular, sequenced 'patch plans' (e.g., tests → helpers → gates → docs).
TRAIT: Employs 'Multi-Agent Councils' as an authoritative synthesis layer for governance and verification.
TRAIT: Values privacy and data sovereignty; prioritizes data ownership and incremental migration to self-hosted/local hosting.
TRAIT: Practices disciplined project hygiene: uses parallel worktrees, freezes branches, and mandates formal TRIAGE before execution.
TRAIT: Strategic orchestrator: views AI as a manager of tasks, delegating heavy coding to specialized workers (Codex/Claude Code).
TRAIT: Employs a tiered model strategy: reserves premium models for governance/safety while delegating utility tasks to auxiliary models.
TRAIT: Resists generic AI tropes; favors distinct visual identities (1990s OVA, candid/raw photography).
TRAIT: Uses 'Heartgate' as a gated transition mechanism between UACP phases (Triage, Propose, Plan, Execute, Verify, Resolve).
PREFERENCE: Multi-vendor AI infrastructure: employs redundant providers (Aliyun, OpenCode Go, MiniMax, Kimi K2.6) to ensure availability.
PREFERENCE: Hermes-only framing for technical discussions unless asked otherwise.
PREFERENCE: Favors explicit, documented overrides for edge cases over loosening global system constraints.
PREFERENCE: Separates communication by purpose: Telegram for private/direct control, Discord for structured work (forums).
PREFERENCE: Seeks unified/consolidated knowledge systems over fragmented tool-specific repositories.
INSTRUCTION: Discord #dispatch is for execution; #intake is for triage/routing; #control is for management.
INSTRUCTION: Follow the 'Orchestrator-Worker' pattern: Hermes handles design/synthesis; delegate heavy coding to Codex/Claude Code.
INSTRUCTION: UACP workflow: TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE.
</memory-context>
```

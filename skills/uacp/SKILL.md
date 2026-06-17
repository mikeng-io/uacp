---
name: uacp
description: Router for Universal Agent Control Plane governance, lifecycle, and state work.
kind: orchestration
version: 2.1.0
metadata:
  hermes:
    tags:
      - governance
      - lifecycle
      - multi-agent
      - router
    related_skills:
      - uacp-triage
      - uacp-propose
      - uacp-plan
      - uacp-execute
      - uacp-verify
      - uacp-resolve
      - uacp-state
      - uacp-context
      - uacp-brainstorm
      - uacp-council
      - uacp-debate
      - uacp-parallel
---

# Universal Agent Control Plane — Router

UACP is the generic, unified, adaptive control-plane doctrine for governed agentic work. It decides whether work needs lightweight handling or a full lifecycle run, and then routes to the appropriate phase skills.

## Lifecycle semantic gate reference

For UACP lifecycle hardening, validator gates, or phase-skill repair, read `../uacp-core/references/lifecycle-semantic-gates.md` before claiming a phase chain is complete. It captures the PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE semantic-gate pattern, the PIV naming correction, and the VERIFY/RESOLVE pitfalls Mike corrected in-session.

## When to use

Use when the request explicitly names UACP, a UACP lifecycle phase/skill, UACP state, or asks to change UACP governance/routing behavior. The router does not define Guardian, Heartgate, or review policy semantics; it only routes to the appropriate owner skill or canonical UACP docs.

## Lifecycle

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Use `uacp-state` only for governed state mutation and state-authority questions.

## Route

Reference: `../uacp-core/references/lifecycle-semantic-gates.md` captures the preferred lifecycle hardening pattern from the PROPOSE/PLAN/EXECUTE/VERIFY/RESOLVE gate work: PIV means Phase Intent Verification, VERIFY and RESOLVE are first-class gates, and governance-core phase hardening should use retrieval-led gap audit, pre-design council when semantics are subtle, implementation, validation, post-council, remediation, and follow-up PASS before commit/push.

- unclear scope, granularity, or admission -> `uacp-triage`
- proposal, authority, side effects, or viability -> `uacp-propose`
- execution graph, artifacts, or verification plan -> `uacp-plan`
- dispatch, Kanban, or worker execution -> `uacp-execute`
- adaptive verification, council, or evidence -> `uacp-verify`
- closure, lessons, memory, or skill updates -> `uacp-resolve`
- governed state mutation, state authority, or state consistency -> `uacp-state`

## Composition rule

The router does not contain phase execution procedures. Load the phase skill and let that skill own its checklist, adaptive gates, support files, handoff rules, and operator-facing presentation.

Operator channel output should be summary-first: conclusion, rational intent, decision/status, invariants, material risks, next action, and evidence pointer. Do not dump raw file lists or artifact inventories by default; raw details belong in evidence artifacts and are provided on request.

When using UACP phase labels such as `PASS`, `VERIFY PASS`, or `RESOLVE`, qualify exactly what passed. For documentation/design runs, say `documentation hygiene passed`, `first review slice passed`, or `draft reset resolved`; do not imply the underlying system/product has been implemented, accepted, or completed. If a run only reviews docs, explicitly state what is still not true: no runtime, no API, no integration, no canonical acceptance unless the lifecycle artifact actually grants that status.

For short context-dependent commands inside UACP work, bind the task to the strongest explicit conversational anchor before acting: platform reply/quote/thread context, then latest user message, then active UACP run/topic. Do not let cwd, dirty repositories, loaded skills, memory, or tool state redefine the run scope. If the anchored context does not clearly authorize a side-effectful action such as file edits, commits, state writes, gateway restarts, or protected artifact mutation, stop and ask.

Trustless ACP is pattern evidence only. UACP remains universal/adaptive and must not inherit Trustless-specific fixed gates, domains, worktree paths, proposal topology, reviewer lists, or verification sequences.

## Operator phase-return presentation

When reporting UACP phase progress or completion back to Telegram/Discord, return information rather than raw audit data. Use a conclusion-first operator summary: conclusion/status, what changed at meaning level, why it matters, decision rationale, invariants preserved, material risks, next action, and compact evidence pointer. Do not dump full file lists, raw diff stats, validation logs, council transcripts, or artifact inventories by default.

Raw evidence still belongs in UACP artifacts, commits, gate ledgers, and verification records. Mention that details are available on request. Include specific paths only when a path is itself the decision subject, a blocker/error depends on it, rollback requires it, or Mike explicitly asks for audit detail.

See `../uacp-core/references/operator-phase-return-presentation.md` for the reusable summary schema and suppression rules.

## Documentation-authority reset pitfall

If Mike corrects that a documentation cleanup is actually in UACP lifecycle, especially for LEXA/MEMEX/Cortex/Nora/private-public boundary docs, stop treating it as informal Vault cleanup. Admit/reroute it through UACP at the appropriate granularity and record a compact lifecycle artifact. If he says to start over or that no document should be non-draft, demote even prior `accepted` decision notes to draft input and add explicit restart guards before content review.

## Granularity ownership and naming pitfall

If Mike asks whether a task should use “UACP Lite” versus “real UACP”, do not invent or preserve an informal UACP Lite track. The correct distinction is **UACP or no UACP**. Once UACP is selected, the lifecycle owns routing/granularity through TRIAGE (`direct`, `lightweight`, `standard_uacp`, `full_governance`, or `block_or_clarify`). Phrase it as “enter UACP; TRIAGE selected `<routing_outcome>`,” not “I chose UACP Lite.” This matters especially for public/private profile, identity-registry, runtime-plugin, or dispatch-control work where informal naming hides authority boundaries.

## Skill-library refactor protocol

When restructuring UACP skills, default to the fully autonomous self-closing loop once the operator authorizes it: work one skill at a time; dispatch Agent Council for brainstorming/debate until there is a solid PASS/no concerns outcome; save checkpoints; implement only after PASS; run deterministic audit; then run full-perspective Agent Council + Kimi Code/Kimi K2.6 verification after implementation. If any reviewer returns CONCERNS/BLOCK, patch the artifact or implementation, record the resolution, and rerun focused verification until PASS/no concerns before moving to the next skill.

Do not return to the operator between phases merely for ceremony. Stop only for a true authority boundary, destructive/external side effect, unresolved hard blocker, or missing context that cannot be recovered from checkpoints.

Patch existing artifacts where possible; do not predefine file trees before exploring intent and variants; keep UACP universal/adaptive rather than importing Trustless-specific fixed gates or domains.

Carry lessons forward between phases: resolve relative references from the target skill directory; preserve exact backups before edits; do not claim non-repo skill files were committed; compare against backups for removed protective semantics; do not equate shorter with safer; preserve phase-local anti-compression rules and audit-critical output fields.

When reviewing a Claude Code or external-agent restructure, verify the canonical UACP repo/docs and the active Hermes skill export as separate surfaces. A clean UACP repo validator or doc link scan does not prove the live `~/.hermes/skills/devops/uacp` export is current. Check phase skill directories, frontmatter, local Markdown reference resolution from each skill directory, UACP-root validator output, and git provenance separately; report repo/docs, validator, docs links, active skill export, and provenance as separate PASS/WARN/BLOCK lines.

## Self-repair warning

When repairing UACP skills, use normal file/git workflow. Do not use broken UACP protected writers, `uacp-verify`, or Heartgate as self-approval authority until the relevant skill has itself passed refactor verification.

## Commit documentation discipline

When settling a large UACP working tree, especially after governance/runtime/doc-package work, do not simply commit the dirty set. First ensure there is a durable explanation surface in the repo and in the commit message:

- a decision/architecture or equivalent artifact that states what changed, why it changed, invariants, enforcement details, and verification commands;
- index/command-doc updates when gates, validators, fixtures, or operational workflows changed;
- inline test comments when an old verification lane needs new fixture setup because an invariant changed;
- a self-contained commit message with `What changed`, `Why`, `Invariants and details`, and `Verification` sections.

See `../uacp-core/references/adaptive-package-gate-commit-pattern.md` for the concrete pattern, including validator command pitfalls and long commit-message handling.

## Adaptive package backfill pattern

When auditing an in-flight UACP run, distinguish machine lifecycle envelopes from human-readable adaptive packages. If a medium/high consequence run has `proposals/{run_id}-proposal.yaml`, `plans/{run_id}-plan.yaml`, or scope/gate-selection YAML but lacks `proposals/{run_id}/` or `plans/{run_id}/` Markdown packages, call that out directly and backfill the package directories plus package-selection/plan-selection bridge artifacts before claiming strict lifecycle completeness. See `../uacp-core/references/adaptive-package-backfill-pattern.md`.

## Architecture packet UACP-compatibility pattern

When Mike asks whether existing architecture/design documents need to be revisited to comply with UACP, first classify the surface. Draft Vault/project docs usually need **UACP-compatible documentation hygiene** — explicit authority, status, boundaries, promotion path, and implementation stop rules — not a forced full UACP lifecycle package. Use full lifecycle artifacts only when the work changes protected runtime, governance, public/private, memory, agent-control, or UACP surfaces. See `../uacp-core/references/architecture-packet-uacp-compatibility.md`.

## Lifecycle hardening pattern

For UACP self-patches, especially phase gates or truth/authority boundaries, use retrieval-led gap audit, pre-design council when appropriate, docs/config/validator/fixtures/skills patching, post-implementation adversarial audit, then commit/push. See `../uacp-core/references/lifecycle-semantic-gates.md` for the preferred hardening pattern.

For external audit remediation of lifecycle gates, do not stop at docs/config/offline validators. Check Heartgate runtime enforcement, root-confined artifact loading, runtime transition fixtures, PIV terminology/evidence semantics, and active skill-store sync. See `../uacp-core/references/external-audit-runtime-gate-remediation.md`.

When Mike asks for both Kimi Code and Codex to review UACP changes, launch them as bounded read-only external audits with explicit in-runtime Agent Council roles and command-level timeouts; see `../uacp-core/references/kimi-codex-agent-council-audit-loop.md` for the prompt skeleton, Kimi coding-model invocation, and contamination checks.

If Mike asks for a full review/audit, do **not** narrow the audit to the latest commit or immediate remediation unless explicitly instructed. Scope it to the full related change lineage and end-to-end lifecycle coherence across PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE, with devil's advocate, consistency historian, and dependency-readiness roles. After findings, patch all authoritative surfaces together — runtime, offline validator, config/schema, fixtures, active skill exports, state, and docs — and rerun adversarial follow-up until PASS. See `../uacp-core/references/full-lineage-audit-and-remediation-lessons.md` for the full-lineage audit and documentation aftermath pattern, including the anti-fracture guide package shape (`docs/guides/<topic>/00-index.md` conductor + modular human/agent/gate/history files), the need to avoid scattering doctrine across random docs, and the UACP git identity pitfall (`norty-dev <norty@nortrix.io>`; check local config before committing).

When LEXA documentation authority is being reset or promoted, treat it as UACP lifecycle work if it affects source registry contracts, private/public retrieval boundaries, Nora/Cortex integration, or future runtime readiness. Do not frame it as informal Vault cleanup. After the reset, use `../uacp-core/references/lexa-first-principles-review-sliced-continuation.md` for the sliced continuation pattern: review draft docs in bounded slices, write per-slice checkpoints, preserve draft posture, then VERIFY/RESOLVE the review scope without implying LEXA itself is canonical or implementation-ready.

## Legacy reference warning

`../uacp-core/references/` is the shared canonical reference home. Do not depend on shared references unless the active skill Decision justifies that dependency.

## Presentation and semantic package rule

Read `../uacp-core/references/semantic-package-and-operator-return-lessons.md` when a UACP task involves phase-return messaging, adaptive PROPOSE/PLAN packages, or a dispute about whether Markdown files are optional.

Durable rule: YAML lifecycle files are machine envelopes; Markdown package files are semantic substrate for future human/agent understanding; Telegram/Discord receives a short operator summary. Do not fix missing semantic context only at the proposal level — update skills and validators/schema behavior so the failure cannot recur.

When council review finds gaps in semantic package enforcement, use `../uacp-core/references/semantic-package-and-operator-return-lessons.md`: patch the systemic validator/skill contract, rerun focused council to PASS, and report conclusion -> patch -> rerun outcome without dumping raw inventories.

## Emergency stop

If UACP docs, config, or state disagree, stop. Route to `uacp-state` only for state mutation/authority/consistency; otherwise escalate to the operator or canonical UACP docs. If authority is unavailable, stop rather than inventing authority.

# UACP Decision Log

This file is the durable record of UACP **operational** governance decisions. Each entry records a decision, rationale, status, and canonical targets affected. Decisions are listed most-recent first within the file but ordered chronologically. This log is maintained by the document registry in `docs/INDEX.md`.

> **As of 2026-05-17, architectural decisions live in [`../architecture/`](../architecture/INDEX.md) as numbered ADRs.** Operational decisions continue to land here. The split was established by [ADR-0001](../architecture/0001-record-architecture-decisions.md). When in doubt, see [`../decisions/INDEX.md`](INDEX.md) for the "when to log here vs author an ADR" criteria.

## Decision Log

### 2026-06-15 — Computed Heartgate Engines Supersede Self-Attested Coherence

Decision: Run coherence and adjacent run-integrity checks as **deterministic computed engines** that Heartgate executes at RESOLVE (`Heartgate.validate_closure`), turning `block`-severity findings into real Heartgate blockers. The self-attested `heartgate_coherence.status` flag (`core.py:_validate_heartgate_coherence`) is **superseded** and advisory only — the computed `coherence` engine is authoritative. Five engines ship: `coherence`, `ledger_integrity`, `scope_conformance`, `evidence_completeness`, `deferral_completeness`, organized as a hexagonal-lite package (`engines/{base,domain,io,<engine>}`) with one shared `Violation` type and one `ENGINES` registry.

Rationale: the prior coherence "lens" trusted an agent-supplied `status: pass/block` and only checked that lens *names* were listed — self-attestation, violating "no self-attesting closures." The engines compute each dimension (ids/ledger/history/artifacts/scope/evidence/deferrals actually agree) instead of trusting a flag. `validate_closure` is decoupled (NOT auto-called in `state_machine.handle_finalize`); the RESOLVE flow / future MCP `uacp_validate_closure` tool invokes it. It expects a finalized run (terminal checks require the closed state). Architecture is hexagonal-lite + DDD vocabulary; tooling adds ruff (strict on `engines/`) and Pydantic domain models.

Status: accepted.

Canonical targets:

- `skills/uacp-core/scripts/engines/**` (the five engines + base/domain/io)
- `skills/uacp-core/scripts/core.py` (`Heartgate.validate_closure`; `_validate_heartgate_coherence` marked superseded)
- `config/phase-transitions.yaml` and config layer (F-EV-01 fix, below)
- `docs/plans/2026-06-15-computed-heartgate-engines-design.md`

Follow-up: (1) deliver the engines into Claude Code as a plugin (MCP server exposing governed writers + `uacp_validate_closure` as tools, PreToolUse Guardian hook) — the "Claude Code adapter." (2) Dedupe the `C2`/`LI` ledger-malformed overlap at the reporting layer (one finding per corrupt line), as done for `SC`/`C6`. (3) Phase 2: apply the F-T3-01 fail-closed normalization when gate grammar moves to Python.

### 2026-06-15 — F-EV-01: Config-Wide `..outputs` Typo Corrected to `.outputs`

Decision: The config layer referenced `..outputs/` (a non-existent directory) in ~6 files while the executable kernel writes and reads `.outputs/`. Corrected all `..outputs` → `.outputs` (57 occurrences across 25 config/script/skill files) so governance points at the directory the kernel actually uses. Source of truth = the executable kernel.

Rationale: surfaced by `evidence_completeness` — the resolve-phase exit invariant glob `..outputs/{run_id}*` would never match, so the computed gate would have false-blocked **every** real resolved run. A latent, scattered inconsistency invisible until something computed against those paths. The three-dot `...outputs` token in `bridge-commons` is a separate construct, left untouched.

Status: accepted.

Canonical targets:

- `config/phase-transitions.yaml`, `config/state.yaml`, `config/roots.yaml`, `config/guardian-policy.yaml`, `config/artifact-schemas.yaml`, and affected `scripts/`/`skills/`.

Follow-up: review the `bridge-commons` three-dot `...outputs` token separately.

### 2026-06-15 — Adaptive Gates Are Fail-Closed on Absent Config (F-T3-01)

Decision: When an adaptive gate's configuration key is absent, the gate MUST enforce (demand its evidence), not silently self-disable. This fail-closed default is the canonical behavior. The kernel change is deferred to the Phase 2 config collapse (which moves gate grammar from YAML into Python), rather than patched into the current YAML-loading code that Phase 2 will replace.

Rationale: The E2E transition + per-phase matrices (`tests/e2e/`) surfaced that `core.py` handles a missing gate-config key two ways — proposal/plan gates enforce on absent config (`self.config.get(key) or {}`, ~line 950) while execute/verify/resolve gates self-disable (`if not isinstance(self.config.get(key), Mapping): return`, ~line 1202). An adaptive gate that silently does nothing when its config is missing is the "advisory-in-disguise" failure (F4): governance that looks enforced but isn't. Fail-closed is the only default consistent with the no-silent-skip invariant. Fixing the idiom now would be throwaway work since Phase 2 rewrites this code; the durable move is to lock the principle and apply it during the rewrite.

Status: accepted.

Canonical targets:

- `skills/uacp-core/scripts/core.py` (Phase 2: normalize both gate families to enforce-on-absent)
- `docs/plans/2026-06-14-uacp-cc-hardening.md` (Phase 2 section + findings log F-T3-01)

Follow-up: Phase 2 implementation must make all adaptive gates enforce-on-absent-config and add a regression test asserting an absent gate key enforces. Until then, the inconsistency stands but is harmless in practice because the production `config/phase-transitions.yaml` defines all gate keys explicitly.

### 2026-05-17 — UACP Patch Plan Run uacp-patch-plan-20260515: Phases 0–4 + Global Review

Decision: A 5-phase UACP patch plan (`proposals/uacp-patch-plan-20260515.yaml`) was authored, council-reviewed, and merged in 7 commits between 2026-05-15 and 2026-05-17, mechanically hardening the governance plane against the original Phase 0 audit findings and propagating constraints forward through each phase. A final cross-phase global review surfaced 14 high-consensus material findings; 10 batched as in-scope R1 remediation, 4+minor propagated to Phase 5.

Rationale: The pre-Phase-0 Guardian had three latent enforcement gaps (filesystem_guard_verified unused, policy.mode unread, governed writers unclassified) that made the rest of the framework's policy claims unverifiable. The patch plan delivered each phase atomically with a two-pass Codex council review gate (three-pass for Phase 3, which introduced a new enforcement category). The global review then validated cross-phase coherence.

Status: accepted; patch-plan run RESOLVED. Each phase has its own ADR for stable reference. The aggregate run completes the "mechanical governance" thesis for Phases 0–4; Phase 5 (full autonomous mode) remains a reserved_slot with a propagated-constraint backlog.

Canonical targets:

- **Architectural decisions per phase**: see ADRs [ADR-0002](../architecture/0002-phase0-policy-mode-and-classification.md) through [ADR-0007](../architecture/0007-global-review-cross-phase-remediation.md) for per-phase rationale, decision drivers, options, consequences, and validation pointers.
- **Phase 5 backlog**: [`/ROADMAP.md`](../../ROADMAP.md), [`../plans/phase5-reserved-slot.md`](../plans/phase5-reserved-slot.md), and the propagated-constraint blocks in the three Codex-review verification YAMLs — `verification/uacp-patch-plan-20260515-phase3-codex-review.yaml#propagated_constraints.to_phase_4` (18 pc_p3_* items), `verification/uacp-patch-plan-20260515-phase4-codex-review.yaml#propagated_constraints.to_phase_5` (19 pc_p4_* items), and `verification/uacp-patch-plan-20260515-global-review.yaml#deferred_to_phase_5_with_evidence_pointer` (15 items).
- **Bootstrap-posture honest disclosure**: `.outputs/uacp-patch-plan-20260515-{lessons,resolve}.yaml` carry the disclosure that the run authored governed writers without itself flowing through them; ledger_citations are tagged `_advisory`.
- **Doc restructure** (concurrent with run RESOLVE): subdirectory + ADR adoption per [ADR-0008](../architecture/0008-doc-structure-and-adr-adoption.md).

### 2026-05-15 — Documentation Hardening: Runtime-Neutral Framing And Human-Readable Entry Points

Decision: UACP documentation is hardened to be runtime-neutral, comprehensive, and human-readable. Changes include: (1) new `README.md` at `UACP_ROOT` with lifecycle and cognitive-plane Mermaid diagrams; (2) new `docs/runtime-integration-guide.md` with the complete integration contract for building a new runtime adapter; (3) new `docs/decision-log.md` extracted from `docs/index.md`; (4) decoupled the Hermes/Norty coupling from core doctrine: `docs/constitution.md` first sentence now describes UACP as a runtime-neutral framework rather than "the governance layer for Hermes/Norty work"; (5) `docs/alignment-spec.md` operator preferences section renamed and labeled as Hermes/Norty deployment-specific, not generic UACP policy; (6) `docs/lifecycle-reference.md` adds a lifecycle flow diagram and renames the "Hermes Kanban Binding" section to "Coordination Adapter Binding" with runtime-neutral framing; (7) `docs/orchestration-model.md` adds a cognitive-plane Mermaid diagram, neutralizes Hermes-specific vocabulary (`delegate_task` → `same-runtime branch` with Hermes noted as the current implementation), and labels the "Locked Current Operating Mode" and "Current-Stage Profile Policy" sections as Hermes-specific deployment notes; (8) `docs/runtime-enforcement.md` adds a Guardian decision flow diagram; (9) `docs/runtime-porting-and-version-control.md` adds a runtime adapter authority chain diagram, removes retrospective metadata, and adds a "Future Runtime Targets" table; (10) `config/phase-transitions.yaml` replaces "Hermes Kanban coordination" with "coordination adapter".

Rationale: UACP claims to be runtime-neutral but the doctrine and documentation frequently named Hermes as if it were conceptually required. Human readers had no entry point; the only starting document was `docs/index.md`, a document registry aimed at agent consumption. The documentation hardening makes UACP's actual design (runtime-neutral governance framework, replaceable coordination adapter, future multi-runtime support) visible and actionable, while preserving all existing governed behavior.

Status: accepted. No canonical doc content was removed; only framing, coupling language, and new human-readable entry points were changed. YAML config changes are backward-compatible.

Canonical targets:

- `README.md` (new)
- `docs/runtime-integration-guide.md` (new)
- `docs/decision-log.md` (new, extracted from `docs/index.md`)
- `docs/constitution.md` (first sentence decoupled)
- `docs/alignment-spec.md` (operator prefs section renamed and labeled deployment-specific)
- `docs/lifecycle-reference.md` (diagram added, Hermes Kanban section renamed and reframed)
- `docs/orchestration-model.md` (diagram added, Hermes vocab neutralized, deployment notes labeled)
- `docs/runtime-enforcement.md` (Guardian diagram added)
- `docs/runtime-porting-and-version-control.md` (diagram added, future runtimes table added, retrospective metadata removed)
- `docs/index.md` (inventory updated, decision log content replaced with pointer)
- `config/phase-transitions.yaml` (Hermes Kanban reference neutralized)

Follow-up: update `.outputs/uacp-current-status.yaml` to reflect this documentation milestone; keep `docs/runtime-integration-guide.md` aligned when the Guardian event schema or Heartgate contract changes.

### 2026-05-14 — Harden Canonical Writers And Expose Heartgate Check Tool

Decision: Phase 2 governed canonical writer concerns are resolved by hardening path validation, adding symlink/absolute/root/directory negative tests, and splitting canonical writer policy into `docs.uacp` and `config.uacp`. The UACP-owned Hermes Guardian adapter also exposes `uacp_heartgate_check` as the first callable Heartgate transition validation tool.

Rationale: Phase-end Agent Council found that canonical writer boundaries should not remain generic `file.write` and needed stronger negative proof coverage before Phase 3. Heartgate already existed as a neutral kernel, but lifecycle wiring needed a callable runtime boundary before phase transitions can be mechanically checked.

Status: accepted and verified by `verification/live-guardian-proof-20260514-phase2-hardening.yaml`, `verification/phase2-hardening-20260514.yaml`, `verification/live-guardian-proof-20260514-phase3-heartgate.yaml`, `verification/containment-fail-closed-20260514.yaml`, and `verification/runtime-tool-schema-reload-20260514.yaml`. Fresh-session reload verification confirms the UACP tools are exposed in a new Hermes session.

Canonical targets:

- `runtime-adapters/hermes/plugins/uacp_guardian/`
- `config/guardian-policy.yaml`
- `scripts/live_guardian_probe.py`
- `verification/phase2-agent-council-retrospective-20260514.yaml`
- `verification/phase2-hardening-20260514.yaml`
- `verification/live-guardian-proof-20260514-phase3-heartgate.yaml`

Follow-up: lifecycle skills now reference `uacp_heartgate_check`, `uacp_doc_write`, and `uacp_config_write`; remaining work is fresh-session/runtime reload verification for exposed tool schemas and any final containment hardening before broad activation.

### 2026-05-14 — Add Governed Docs And Config Writer Boundary

Decision: UACP-owned Hermes Guardian now provides `uacp_doc_write` for canonical Markdown docs under `docs/` and `uacp_config_write` for canonical YAML config under `config/`. Known plugin writer tools are classified by tool-specific policy; unknown plugin mutators remain blocked as `runtime.extension`.

Rationale: After bootstrap closure, canonical docs/config changes need a governed mutation path. `uacp_artifact_write` intentionally refuses `docs/` and `config/`, while direct file writes are Guardian-blocked. Dedicated writer surfaces remove the manual accepted-risk path for normal doc/config synchronization.

Status: implemented in the UACP-owned Hermes runtime adapter and verified with safe temporary-root positive/negative probes. Active long-running sessions may require runtime reload before the new tools appear in tool schemas.

Canonical targets:

- `runtime-adapters/hermes/plugins/uacp_guardian/`
- `config/guardian-policy.yaml`
- `.outputs/uacp-current-status.yaml`
- `.outputs/uacp-operational-dashboard.yaml`
- `verification/live-guardian-proof-20260514-phase2-writers.yaml`

Follow-up: writer hardening is complete and `uacp_heartgate_check` is implemented. Remaining work is lifecycle-skill adoption plus fresh-session/runtime reload verification.

### 2026-05-14 — Confirm Live Hermes Runtime Adapter Bindings And Cleanup Lane

Decision: `thread_title_sync` and `uacp_guardian` are active Hermes user-plugin bindings sourced from `UACP_ROOT/runtime-adapters/hermes/plugins/`. Hermes Agent local plugin copies are transitional duplicates and may be removed after verifying the user-plugin bindings remain active. The temporary `uacp_symlink_probe` adapter is no longer an active runtime artifact and should be removed after cleanup verification.

Rationale: UACP-owned runtime adapters should remain in UACP, with Hermes Agent as a downstream host runtime. Keeping identical plugin copies in the Hermes Agent checkout creates source-of-truth drift now that user-plugin symlink bindings are active.

Status: accepted for local cleanup and documentation/config synchronization. No remote push is authorized by this entry.

Canonical targets:

- `docs/index.md`
- `config/runtime-bindings.yaml`
- `config/state.yaml`
- `.outputs/uacp-current-status.yaml`
- `runtime-adapters/hermes/plugins/`
- `verification/runtime-porting-20260514-cleanup-doc-sync.yaml`

Follow-up: run post-cleanup loader verification and keep production-complete claims blocked until lifecycle wiring, containment hardening, and governed docs/config writer support are complete.

### 2026-05-13 — Establish Runtime Porting And Version-Control Binding Policy

Decision: UACP owns governed runtime adapter source under `runtime-adapters/`, records runtime binding targets in `config/runtime-bindings.yaml`, and records repository/branch/worktree/backup policy in `config/version-control.yaml`. Hermes Agent remains the first downstream runtime target, not the long-term authority root for UACP-owned plugin source.

Rationale: Keeping UACP-specific plugins only inside the Hermes Agent repository couples governance authority to an upstream runtime checkout and makes backup/portability fragile. UACP needs its own Git-controlled source boundary plus runtime-specific symlink/install/export bindings.

Status: accepted as a runtime-porting policy seed after non-destructive Hermes symlink discovery proof.

Canonical targets:

- `docs/runtime-porting-and-version-control.md`
- `config/runtime-bindings.yaml`
- `config/version-control.yaml`
- `runtime-adapters/hermes/plugins/`
- `executions/runtime-porting-20260513-symlink-proof.yaml`

Follow-up status: real `uacp_guardian` and `thread_title_sync` are now live-bound through `HERMES_ROOT/plugins/` as user plugins with loader evidence recorded. Remaining work is duplicate Hermes Agent source reduction, temporary probe cleanup, continued live proof tests, and production hardening before claiming Guardian complete.

### 2026-05-13 — Integrate Agent-Skills Branch Concepts Into UACP Doctrine

Decision: UACP absorbs the useful doctrine from `mikeng-io/agent-skills` branch `origin/codex/guardian-agent-council-uacp` and remains the single canonical source of truth. The branch is source material, not competing authority. Downstream agent-skills should later be re-extracted from stabilized UACP doctrine.

Rationale: The branch introduced useful Guardian, council, runtime adapter, and domain concepts, but UACP must remain one integrated doctrine for governance, execution, verification, orchestration, and enforcement. Keeping parallel agent-skills doctrine would create drift.

Status: accepted for canonical doc/config integration after review of `plans/agent-skills-branch-integration/`.

Canonical targets:

- `docs/index.md`
- `docs/orchestration-model.md`
- `docs/lifecycle-reference.md`
- `docs/runtime-enforcement.md`
- `config/review-routing.yaml`
- `config/evidence-clusters.yaml`

Follow-up: Do not port `guardian.py`, runtime adapter scripts, or other implementation code until the doctrine stabilizes and an implementation phase is explicitly approved. Keep symbolic paths such as `UACP_ROOT/verification/` in canonical docs/config.

### 2026-05-10 — Add TRIAGE Before PROPOSE

Decision: UACP starts with `TRIAGE`, then enters `PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE` when governance is warranted.

Rationale: `PROPOSE` was too heavy as the first step. Simple work needs a way to exit without a full UACP run, while strategic work needs early governance-intensity scoring.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/gate-selection.yaml`
- `config/phase-transitions.yaml`
- `config/review-routing.yaml`

Follow-up: complete. The temporary working note was deleted after canonical docs and configs captured the decision.

### 2026-05-10 — Derive Granularity From Multiple Factors

Decision: TRIAGE does not use depth alone. It scores impact, reversibility, domain count, runtime count, and verification difficulty, then derives granularity and routing.

Rationale: A shallow task can be high impact or irreversible. A deep task can be low risk when reversible and easy to verify.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/gate-selection.yaml`
- `config/review-routing.yaml`

### 2026-05-10 — Establish Document Control Before More Design Expansion

Decision: `docs/index.md` becomes the document registry, read-order guide, and decision log for UACP documentation.

Rationale: UACP should not accumulate unmanaged docs, configs, working notes, and decision files. Document governance must exist before continuing broader workflow design.

Status: accepted.

Canonical target:

- `docs/index.md`

### 2026-05-10 — Delete Temporary TRIAGE Working Note

Decision: Delete `docs/triage-and-workflow-execution.md` instead of keeping it as an archived document.

Rationale: The file was a short-lived working note. Its durable decisions are now represented in `docs/index.md`, `docs/lifecycle-reference.md`, `config/gate-selection.yaml`, `config/phase-transitions.yaml`, and `config/review-routing.yaml`.

Status: accepted.

Canonical targets:

- `docs/index.md`

### 2026-05-11 — Establish Active Hermes Kanban Binding

Decision: UACP now records an active Hermes Kanban binding in `state/kanban.yaml` with board slug `uacp` and a root task id anchor for PLAN/EXECUTE traceability.

Rationale: Kanban binding was previously deferred. A real board now exists, so UACP should keep Kanban task graph traceability in state rather than treating the binding as hypothetical.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `state/current.yaml`
- `state/kanban.yaml`
- `config/state.yaml`

### 2026-05-11 — Activate Lifecycle Skill Family And Governed Mutation

Decision: The UACP lifecycle skill family exists under `HERMES_ROOT/skills/devops/uacp/`, bootstrap direct state edits are closed, and governed mutation through `uacp-state` is active for runtime state changes.

Rationale: The pre-lifecycle-skill checkpoint has been satisfied by the implemented skill family, state/current.yaml records `mutation_policy: uacp_state_required`, and bootstrap closure is now a current operational fact rather than a future condition.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `docs/lifecycle-reference.md`
- `config/state.yaml`
- `state/current.yaml`

Follow-up: superseded by the later runtime Guardian/Heartgate checkpoint. Current remaining work is live activation, proof testing, lifecycle-skill wiring to Heartgate, and `uacp_state_write` adoption.

### 2026-05-11 — Define Runtime Guardian And Heartgate Design

Decision: Add `docs/runtime-enforcement.md` as the canonical runtime-enforcement design and `config/guardian-policy.yaml` as the machine-readable Guardian/Heartgate policy seed.

Rationale: UACP runtime enforcement has a distinct long-term reader, implementation boundary, and adapter contract. It cannot be safely buried in lifecycle prose or Hermes plugin code. The design records that production enforcement requires both tool-call Guardian enforcement and Kanban/control-plane enforcement.

Status: council reviewed; ready for runtime implementation planning/execution.

Canonical targets:

- `docs/runtime-enforcement.md`
- `config/guardian-policy.yaml`
- `plans/uacp-runtime-guardian-implementation-plan.md`
- `verification/uacp-runtime-guardian-design-council.yaml`

Follow-up: implement Guardian core, Heartgate core, Hermes adapter, state mutation tool, audit, and Kanban/control-plane enforcement after the design checkpoint passes.

### 2026-05-11 — Record Runtime Prototype Status

Decision: UACP is now an early runtime prototype, not only a document/specification project. The first Hermes Guardian/Heartgate runtime enforcement checkpoint has been implemented and merged in the Hermes Agent runtime, with durable UACP verification recorded.

Rationale: The governance root, state layer, lifecycle skills, Kanban binding, and runtime Guardian checkpoint now exist. Remaining work should focus on live runtime activation, proof testing, lifecycle wiring, containment hardening, and governed doc synchronization rather than continuing to treat runtime enforcement as purely future design.

Status: accepted as current checkpoint summary.

Canonical targets:

- `docs/index.md`
- `docs/runtime-enforcement.md`
- `.outputs/uacp-current-status.yaml`
- `verification/uacp-runtime-guardian-implementation-checkpoint-1.yaml`

Implementation references:

- UACP governance commit: `2f9fad1`
- Hermes Agent runtime commit: `a07da521a`

Follow-up: live runtime proof tests are still required before calling the Guardian production-complete.

### 2026-05-11 — Wire UACP Into Hermes Instruction Surfaces

Decision: Add minimal pointer-level UACP wiring to the active Hermes instruction and dispatch surfaces.

Rationale: UACP existed in docs, state, skills, Kanban, and runtime code, but the core Hermes startup/dispatch surfaces did not clearly route UACP-bound work through the UACP lifecycle. The correct fix is a small pointer to UACP authority, not copying the full UACP constitution into global persona files.

Status: accepted as minimal wiring checkpoint.

Changed surfaces:

- `HERMES_ROOT/SOUL.md`
- `HERMES_ROOT/workspace/SOUL.md`
- `HERMES_ROOT/workspace/AGENTS.md`
- `HERMES_ROOT/routing/dispatch-workspaces.yaml`
- `HERMES_ROOT/config.yaml`
- `.outputs/uacp-current-status.yaml`

Follow-up: restart/reload Hermes and run a live UACP-bound dispatch test.

### 2026-05-10 — Clarify Hermes Kanban Binding

Decision: UACP treats Hermes Kanban as a durable task substrate, not as the UACP lifecycle state machine.

Rationale: Hermes Kanban has its own statuses, boards, dispatcher, parent gating, workers, and workspace model. UACP must record phase state in UACP artifacts and use Kanban task IDs for execution traceability. UACP `TRIAGE` must not be confused with Hermes Kanban `triage` task status.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- future PLAN/EXECUTE binding artifacts

### 2026-05-10 — Close Stage 1/2 Foundation

Decision: Stage 1/2 foundation is closed with deferred implementation items.

Rationale: UACP now has its artifact directories, canonical docs, seed config, document registry, symbolic root policy, TRIAGE model, bootstrap triage artifact, verification artifact, and clarified Hermes Kanban boundary. Further work should move to state/version design and later implementation rather than continuing to expand Stage 1/2.

Status: accepted.

Deferred items at the time:

- version-control binding,
- state model implementation,
- lifecycle skill skeletons,
- Hermes Kanban binding,
- standalone Knowledge Bank service.

Current status: version-control binding, state model, lifecycle skill skeletons, and Hermes Kanban binding have since been implemented. The standalone Knowledge Bank service remains deferred.

Canonical targets:

- `docs/index.md`
- `docs/lifecycle-reference.md`
- `verification/uacp-bootstrap-stage-1-2-verification.yaml`

### 2026-05-10 — Design State And Version-Control Layer

Decision: UACP should use a `state/` layer with file-based YAML run manifests first, governed mutation through `uacp-state`, and git versioning for governance/history artifacts. SQLite or service-backed state is deferred until query or concurrency needs justify it.

Rationale: UACP phase state must be explicit and separate from Hermes Kanban task status. File-based YAML is inspectable, portable, and sufficient for bootstrap. Git should preserve governance and tombstone history, but runtime state should not require committing every mutation.

Status: accepted. Initial implementation is active; SQLite/service-backed state remains deferred.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/state.yaml`

### 2026-05-10 — Seed File-Based State Layer

Decision: Create the initial file-based state contract and bootstrap run state under `state/`.

Rationale: UACP needs explicit lifecycle state before lifecycle skills or Kanban integration can be safe. The first implementation should remain inspectable and portable: a `state/current.yaml` pointer plus run manifests under `state/runs/`, governed by `config/state.yaml`.

Status: accepted.

Canonical targets:

- `config/state.yaml`
- `state/current.yaml`
- `state/runs/uacp-bootstrap-stage-3-state-binding.yaml`

### 2026-05-10 — Require Agent Council At State/Version Checkpoint

Decision: The state/version-control checkpoint requires a full-dimension local Agent Council review before the milestone can close or lifecycle skills can be created.

Rationale: State and version-control decisions define UACP's mutation boundary. A single orchestrator pass is not enough; the checkpoint needs role-diverse review across document authority, state traceability, versioning, Kanban boundary, adaptive gates, memory/knowledge boundaries, path containment, non-software coverage, and operational feasibility.

Status: accepted.

Canonical targets:

- `config/review-routing.yaml`
- current checkpoint council artifact under `verification/`

### 2026-05-10 — Register Runtime State In The Active Inventory

Decision: `state/`, `state/current.yaml`, and `state/runs/` are part of the governed UACP artifact root and must be enumerated in the active inventory.

Rationale: The lifecycle reference now treats runtime state as first-class, so the registry must expose it rather than leaving it implicit.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `docs/alignment-spec.md`
- `config/state.yaml`
- `state/current.yaml`
- `state/runs/uacp-bootstrap-stage-3-state-binding.yaml`

Follow-up: complete. `state/` is no longer bootstrap-only; governed mutation is active through `uacp-state`.

### 2026-05-10 — Tighten Tombstone And Path Rules

Decision: Canonical docs, config, and runtime-state artifacts must use `UACP_ROOT`-relative paths by default, and tombstones using `unavailable-no-git-worktree` must be revisited after version-control binding exists.

Rationale: Context hygiene is better when the active tree is portable, and placeholder tombstone provenance should not become permanent after the artifact root is versioned.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `config/roots.yaml`

### 2026-05-10 — Establish UACP_ROOT Git Binding

Decision: `UACP_ROOT` is a standalone git repository for UACP governance, state, and durable audit artifacts.

Rationale: UACP needs an explicit commit boundary for tombstones, durable audit records, and version-linked governance. A standalone repository keeps that boundary visible and avoids coupling UACP history to unrelated runtime repos.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `config/state.yaml`
- `state/current.yaml`
- `state/runs/`

Follow-up: active runtime-state commit cadence remains unresolved now that `uacp-state` exists.

### 2026-05-10 — Define Lifecycle Skill Contracts Before Skill Creation

Decision: Lifecycle skill files must follow the canonical skill contract in `docs/lifecycle-reference.md` and must not be created before the pre-lifecycle-skill council checkpoint is satisfied.

Rationale: `uacp-state` and the lifecycle skills are the next implementation boundary, but they should not be improvised. The contract keeps the skills aligned with the document registry, state mutation boundary, and Kanban distinction.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/state.yaml`

Follow-up: complete. Lifecycle skill files have been created after checkpoint review.

### 2026-05-10 — Enforce Machine-Readable Lifecycle Control

Decision: The lifecycle boundary must carry machine-readable bootstrap closure, triage routing persistence, checkpoint artifact references, and structured Kanban binding fields before lifecycle skill files are created.

Rationale: Prose alone is not enough to govern mutation boundaries. At the time, the next implementation step needed fields that a state mutator and then-future lifecycle skills could validate directly.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/state.yaml`
- `config/phase-transitions.yaml`
- `config/review-routing.yaml`

Follow-up: complete for `uacp-state` and lifecycle skill creation. Runtime Guardian/Heartgate checkpoint 1 has since been implemented; live activation and proof testing remain open.

### 2026-05-14 — Clarify Runtime Trust Boundary

Decision: UACP governs declared runtime execution and evidence. It does not claim to prevent arbitrary operator or host-side mutation outside the controlled runtime boundary, such as editing files manually, changing plugin bindings from an editor, or running an external runtime without UACP integration enabled.

Rationale: Treating mutable user files as impossible to change would push UACP outside its intended framework and create circular enforcement assumptions. The durable rule is to verify runtime posture and revalidate out-of-band changes before trusting them, not to pretend that UACP can police all human behavior.

Status: accepted.

Canonical targets:

- `docs/runtime-enforcement.md`
- `.outputs/uacp-current-status.yaml`
- `.outputs/uacp-operational-dashboard.yaml`

Follow-up: containment design should proceed from this boundary: UACP declares required execution posture, Guardian verifies runtime-provided evidence, and shell/code remains fail-closed when the host/runtime cannot prove containment.

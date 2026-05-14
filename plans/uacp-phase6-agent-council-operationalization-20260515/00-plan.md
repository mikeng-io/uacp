# Phase 6 Agent Council Operationalization — Plan

## Objective

Make existing canonical Agent Council doctrine operationally executable inside UACP without creating parallel doctrine.

Phase 6 turns the current council model into concrete artifacts, validation rules, and runbook/skill behavior for:

- retrieval-led council dispatch,
- phase-local council synthesis artifacts,
- Heartgate Council/coherence separation,
- blocker/concern patch + rerun handling,
- prior plan-set reconciliation,
- proposal/triage validation decision,
- evidence-domain-registry include/defer decision.

## Authority and boundaries

- Authority: Mike's private Telegram instruction, "continue".
- UACP source of truth: `UACP_ROOT` docs/config/state/artifacts.
- State mutation: `uacp-state` / governed state writer only.
- Docs/config mutation: governed UACP writer tools only.
- Public Hermes Agent upstream changes: out of scope without explicit approval.
- Private UACP push: ask/confirm at checkpoint unless Mike gives broad push approval.
- Current execution posture: `manual_semi_auto`; Kanban-backed council automation remains deferred unless explicitly reopened by evidence.

## Baseline sources to reconcile

PLAN/EXECUTE must ground changes in these existing sources:

- `docs/orchestration-model.md`
- `docs/lifecycle-reference.md`
- `docs/runtime-enforcement.md`
- `config/review-routing.yaml`
- `config/phase-transitions.yaml`
- `config/evidence-clusters.yaml`
- `config/state.yaml`
- `plans/uacp-agent-council-followthrough/`
- `knowledge/phase5-kanban-guard-resolve-lessons-20260514.md`

## Work packages

### WP0 — Plan-council remediation and rollback checkpoint

Before PLAN→EXECUTE:

- Patch the PROPOSE→PLAN transition artifact so validator returns `RESULT PASS`:
  - `terminal_kind` must use a valid transition enum.
  - `heartgate_coherence` must be present when policy requires it.
- Record plan-council findings as a `uacp.council_synthesis` artifact.
- Confirm `uacp_doc_write` and `uacp_config_write` are exposed as governed writer tools before EXECUTE attempts canonical doc/config mutation.
- Confirm skill alignment scope:
  - UACP canonical docs/config/script changes are in this run.
  - Hermes skill files under `HERMES_ROOT/skills/...` are conditional and may be patched only after canonical changes if stale.

Rollback checkpoint:

- Create/keep a local git commit before EXECUTE begins.
- If EXECUTE doc/config/script patches regress validation, rollback with `git revert <checkpoint..HEAD>` or reset only under explicit operator approval.
- Rollback verification command: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_uacp_artifacts.py` must return `RESULT PASS` after rollback.
- Human approval is required before destructive rollback, force push, public upstream action, or private remote push.

### WP1 — Surface inventory and gap map

Create `verification/uacp-phase6-agent-council-surface-inventory-20260515.yaml`.

Must include:

- existing council doctrine surfaces,
- existing schema/config surfaces,
- existing skill/runbook surfaces,
- prior `plans/uacp-agent-council-followthrough/` document inventory,
- gaps classified as `reuse`, `patch`, `defer`, or `out_of_scope`.

Acceptance:

- No Phase 6 doc/config change happens until this inventory exists.
- Prior plan-set items are not silently ignored.

### WP2 — Retrieval-led council protocol

Patch or create the minimal canonical surface needed to require retrieval-led councils for governance/runtime/artifact-management claims.

Required semantics:

- Council prompts must include concrete paths/artifacts to inspect.
- Council synthesis artifacts must record `inspected_paths` or equivalent path evidence.
- Findings must include file/path evidence where applicable.
- Summary-only review is insufficient for runtime/governance correctness claims.

Likely target surfaces:

- `docs/orchestration-model.md`
- `config/phase-transitions.yaml` council synthesis schema
- UACP skill references if stale

### WP3 — Council artifact separation contract

Define explicit artifact convention:

- phase-local Agent Council synthesis: `verification/<run/topic>-<phase>-council-synthesis-<date>.yaml`, kind `uacp.council_synthesis`.
- Heartgate/transition coherence evidence: `verification/<run/topic>-heartgate-coherence-<date>.yaml`, referenced by `heartgate_coherence.artifact_path`.
- Transition artifacts must not substitute one for the other unless the artifact explicitly covers both roles and states the dual scope.

Likely target surfaces:

- `docs/lifecycle-reference.md`
- `docs/orchestration-model.md`
- `config/phase-transitions.yaml`
- relevant UACP lifecycle skills if they encode stale behavior

### WP4 — Blocker/concern rerun protocol

Create a compact operational protocol for council findings:

- `blocker`: cannot transition until patched or rescoped.
- `concern`: must be patched, accepted risk, or deferred with owner/condition.
- `rerun_required`: true when the concern touches a boundary the next phase depends on.
- Rerun synthesis must cite the original finding IDs and updated evidence.

Likely target surfaces:

- `docs/orchestration-model.md`
- `config/review-routing.yaml`
- UACP verify/resolve skill references if stale

### WP5 — Validator coverage decision

Preferred and selected for EXECUTE: extend `scripts/validate_uacp_artifacts.py` to validate basic `uacp.proposal` and `uacp.triage` shapes.

Minimum if implementation proves unsafe:

- record accepted risk with owner, condition, and later phase target before VERIFY.

Acceptance:

- PLAN must not leave proposal/triage validation gap unnamed.
- VERIFY must include at least one valid proposal and one valid triage validation path, either from live artifacts or lightweight fixtures.

### WP6 — Evidence Domain Registry decision

Decision for Phase 6: defer runtime selector activation.

Phase 6 may add wording that:

- `evidence_domain_registry` remains not runtime-active,
- retrieval-led council protocol must not claim runtime selector activation,
- future registry/selector activation requires a separate implementation phase.

Acceptance:

- The plan or verification artifact explicitly states defer and why.

## Execution topology

- Main session orchestrates UACP state/artifact mutations.
- `delegate_task` local role-diverse council is used for review/audit when selected.
- No Kanban graph for this phase unless execution expands into durable multi-worker work; current posture remains manual/semi-auto.
- No external runtime escalation unless PLAN or council finds runtime/tool diversity materially necessary.

## Verification plan

Deterministic checks:

- UACP artifact validator returns `RESULT PASS`.
- Python syntax parse for modified scripts if validator changes.
- Search/read verification that no canonical docs hardcode transient model names.
- Check that council synthesis schema and transition artifacts preserve `council_synthesis_artifact` vs `heartgate_coherence` distinction.
- Verify `uacp_doc_write` and `uacp_config_write` are available as governed writer tools before/while using them.

Council checks:

- Plan council after WP1 surface inventory.
- Execute/verify council if docs/config/validator changes are made.
- Heartgate checks before PLAN→EXECUTE, EXECUTE→VERIFY, and VERIFY→RESOLVE as applicable.

## Rollback

- UACP changes are committed locally at checkpoints.
- Revert latest UACP commits if artifacts/config/docs regress.
- Before EXECUTE, record the checkpoint commit hash in the PLAN_TO_EXECUTE transition artifact.
- Rollback verification command: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_uacp_artifacts.py` must return `RESULT PASS` after rollback.
- No public upstream, private push, destructive rollback, or force operation unless explicitly approved.

## Phase-local granularity

- PLAN entry estimate: 7
- PLAN exit target: 7 or lower if exact surfaces remain bounded
- EXECUTE projection: 8 if validator/config/docs/skills all change
- VERIFY projection: 8 due to governance/runtime confidence checks
- RESOLVE projection: 5

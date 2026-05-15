# Execution plan — Cortex x-draft revamp

Run: `cortex-x-draft-revamp-20260514`
Target workflow: `XCasualComposerWorkflow`
Schedule id: `x-casual-composer`

## Execution authority

Authorized now:

- Create UACP plan artifacts.
- Inspect Cortex files.
- Prepare bounded implementation plan.

Not yet authorized until EXECUTE transition:

- Modify Cortex code/docs/tests.
- Create or apply DB migrations.
- Change live Temporal schedules.
- Post publicly to X.

## Worktree / branch strategy

Implementation should use a Cortex git worktree from `main` unless current branch policy says otherwise:

```text
CORTEX_ROOT=/home/norty/cortex
worktree=/tmp/cortex-x-draft-revamp
branch=feat/x-draft-coherent-hybrid-stream
```

Before creating the worktree in EXECUTE:

1. Check `git status --short --branch` in `CORTEX_ROOT`.
2. Confirm `main` is current enough or fetch/pull only if safe.
3. Create worktree from `main`.
4. Keep changes staged/committed per work package.

## Allowed files for initial EXECUTE

Likely allowed after EXECUTE approval:

```text
src/cortex/activities/casual_compose.py
src/cortex/activities/casual_approvals.py
src/cortex/models/x_original.py
config/x_casual.yaml
tests/test_activities/test_x_casual_*.py
tests/test_workflows/test_x_casual_composer_dry_run.py
docs/08-FAST-LANE.md or docs/10-APPROVALS.md if docs need update
```

Conditionally allowed:

```text
src/cortex/activities/casual_state.py
src/cortex/db/migrations/*.sql
src/cortex/worker.py
```

Only if implementation proves necessary.

Out of scope unless explicitly approved:

```text
src/cortex/workflows/x_interaction.py
src/cortex/workflows/x_news_poller.py
src/cortex/workflows/editorial/*
src/cortex/scheduler.py      # read-only unless schedule behavior needs explicit change
production DB state
```

## Work packages

### WP0 — Out-of-band file disposition

Input: `CORTEX_ROOT/docs/design/editorial-mass-restructure/x-draft-verification-review.md`

Actions:

- Inspect content.
- Decide one of:
  - adopt into Cortex docs under a better path,
  - extract useful points into UACP/Cortex plan then delete untracked file,
  - leave untracked until branch cleanup.

No deletion without explicit operator approval if outside worktree.

### WP1 — Surface inventory and hardcoded language map

Inventory all hardcoded `zh-hk`, `draft_lang`, HK written register prompt, CJK length, zh-specific lint, Discord language display, and persistence surfaces.

Output: implementation checklist and target patch list.

### WP2 — Add ContentIntentContract helpers behind feature flag

Add pure functions/dataclasses:

- `ContentIntentContract`
- `build_content_intent_contract(bundle, angle_contract, config)`
- `format_content_intent_contract(intent, prior_stance)`
- language/register selection helpers

Feature flag default should preserve existing behavior.

### WP3 — Add prior stance context / coherence helper

Start read-only and derived from existing records if feasible.

- Query recent `x_originals` and/or editorial index.
- Extract simple subject/stance metadata when available.
- Return no-history pass when insufficient evidence.
- Do not add DB migration unless necessary.

### WP4 — Integrate prompt contract and conditional gates

- Render ContentIntentContract into prompt.
- Adjust `_COMPOSE_SYSTEM` away from one hardcoded register when feature flag enabled.
- Keep current `zh_hk_written` path intact.
- Make zh-specific lint conditional by language mode.
- Add per-language length caps.

### WP5 — Discord metadata update

Show compact metadata in `#x-drafts`:

- content type
- language mode
- stance
- coherence result
- why-share / why-now
- existing source/fact/drift/dedup flags

### WP6 — Tests and dry-run fixtures

Add tests before live enablement:

- contract builder tests
- language mode examples
- stance contradiction/evolution cases
- conditional zh lint behavior
- Discord formatting metadata
- dry_run side-effect isolation
- regression tests for existing gates

### WP7 — Dry-run proof

Run targeted unit tests, then run manual dry-run:

```text
uv run python scripts/fire_x_casual_composer.py
```

or lower-level gather/compose dry-run if Temporal worker state makes full workflow inappropriate.

No `--live` until verification passes and Mike approves.

## Execution topology

Initial EXECUTE can be main-orchestrator + bounded subagents or one external coding agent if implementation spans many files.

Recommended:

```text
- Main Norty: orchestration, UACP artifacts, final verification.
- One coding worker in worktree: implement WP1-WP5.
- Main Norty or verification subagent: WP6/WP7 tests and review.
```

External runtime justification if used:

```text
Multi-file implementation with prompt/config/tests and risk of breaking current x-draft path.
```

If using Codex/OpenCode/Claude Code, pass only Cortex-specific context and the UACP plan. Do not pass private memory/doctrine dumps.

## Rollback

- Worktree branch can be abandoned before merge.
- Feature flags default off/current behavior preserved.
- No live schedule changes in initial execution.
- No DB migration unless separate plan/approval; if migration is added, include down/rollback or idempotent no-op strategy.

## PLAN exit requirements before EXECUTE

- Plan package exists and parses/reads.
- Target Temporal workflow explicitly named: `XCasualComposerWorkflow`.
- Allowed/forbidden files are declared.
- Verification plan exists.
- Out-of-band file disposition is recorded or deferred explicitly.
- Mike accepts entering EXECUTE or UACP Heartgate transition passes with accepted warnings.

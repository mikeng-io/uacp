# Verification plan — Cortex x-draft revamp

Run: `cortex-x-draft-revamp-20260514`
Target workflow: `XCasualComposerWorkflow`

## Verification goals

Prove the revamp:

1. Targets the correct Temporal workflow.
2. Preserves existing source-grounding and safety gates.
3. Adds content diversity without forcing fake depth.
4. Adds hybrid language support without bilingual slop.
5. Prevents fake/contradictory stance reversals.
6. Keeps dry-run and no-auto-post boundaries intact.

## Required static checks

Before tests:

```text
git status --short --branch
python -m pytest --collect-only targeted tests if useful
```

For UACP artifacts:

```text
python3 YAML parse for all plan/proposal/verification artifacts under UACP containment
```

## Required unit tests

### Contract tests

- `build_content_intent_contract()` returns stable content type/language defaults.
- `format_content_intent_contract()` includes required fields and avoids raw private context.
- Existing `build_angle_contract()` behavior remains unchanged for x_news/signals/pulses priority.

### Language/register tests

Fixtures for:

- `zh_hk_written`
- `cantonese_english`
- `traditional_chinese_english`
- `english_led_hybrid`
- `cantonese_led`
- `plain_english`

Assertions:

- Chinese output contains Traditional, not Simplified.
- Plain English path does not trigger zh-only lint failures.
- Hybrid examples are concept-driven, not random bilingual garnish.
- Per-language length caps use CJK-aware density where applicable.

### Stance/coherence tests

Fixtures:

1. Prior stance: "Tool X weak as full agent"; new draft: "Tool X useful for repo indexing" → pass as scoped praise.
2. Prior stance: "Tool X weak as full agent"; new draft: "Tool X is great and we should use it" → block or rewrite.
3. Prior use exists; new draft claims fresh discovery → flag.
4. Prior negative stance; new draft explicitly says condition changed → pass as evolution.
5. No prior stance → pass with `no_history`.

### Existing gate regression tests

Continue proving:

- Simplified leak blocks/regens.
- fabricated model version/proper noun blocks.
- URL phantom gate blocks.
- dedup reject blocks.
- contract drift still flags wrong source.
- zh AI-tell hard/regen behavior remains.

### Discord formatting tests

`_format_original_message()` should include compact metadata:

```text
content type
language mode
stance/coherence
why-share/why-now
source/fact
flags/dedup/drift
```

Must remain under Discord content limits.

### Dry-run isolation tests

Improve beyond current `_is_dry_run` test:

- In `dry_run=True`, workflow returns draft/quality metadata.
- In `dry_run=True`, it must not call `persist_original`, `post_casual_to_discord`, or `update_original_thread`.
- If candidate is dropped, no persistence/posting calls happen.

## Runtime dry-run proof

After unit tests pass, run either:

```text
uv run python scripts/fire_x_casual_composer.py
```

or lower-level gather/compose script:

```text
uv run python scripts/fire_x_casual.py --compose --json
```

Select based on worker/Temporal availability.

Dry-run acceptance output must show:

- `status: dry_run_complete` or controlled `gate_skip/dropped`
- content intent metadata if compose occurs
- language mode
- stance/coherence result
- no Discord post if dry-run path is used

## Manual review samples

Before live enablement, produce a small sample pack with at least:

- one useful repo share
- one useful article share
- one simple Purpose Agent/Norty observation
- one scoped tool evaluation
- one Trustless/UACP/Cortex governance note
- at least one plain English draft
- at least one Cantonese-English draft

These samples may be dry-run/generated fixtures if live source material is insufficient.

## Acceptance criteria for EXECUTE completion

- Targeted pytest commands pass.
- Existing x-casual safety tests pass.
- No unplanned DB migration or live schedule change occurred.
- Current default behavior remains available via config/fallback.
- Discord metadata output is reviewable and compact.
- Coherence guard blocks the unscoped reversal fixture.
- Dry-run proof is recorded.
- Mike reviews sample pack before enabling live behavior changes.

## Failure handling

If hybrid output becomes generic bilingual slop:

- keep feature flag off,
- tighten register examples,
- add negative fixtures,
- rerun tests before retrying.

If stance guard over-blocks nuanced evolution:

- downgrade to advisory mode,
- require explicit evolution framing,
- collect more examples before hard-blocking.

If implementation requires DB migration:

- stop EXECUTE subtask,
- create migration-specific mini-plan with rollback/idempotency,
- verify via Docker Postgres only after approval.

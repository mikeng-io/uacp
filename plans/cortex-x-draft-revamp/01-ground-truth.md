# Ground truth — current Cortex x-draft workflow

Run: `cortex-x-draft-revamp-20260514`

## Inspected surfaces

Current workflow and code surfaces inspected before planning:

- `CORTEX_ROOT/src/cortex/workflows/x_casual_composer.py`
- `CORTEX_ROOT/src/cortex/activities/casual_gather.py`
- `CORTEX_ROOT/src/cortex/activities/casual_compose.py`
- `CORTEX_ROOT/src/cortex/activities/casual_approvals.py`
- `CORTEX_ROOT/config/x_casual.yaml`
- `CORTEX_ROOT/src/cortex/models/x_original.py`
- `CORTEX_ROOT/tests/test_workflows/test_x_casual_composer_dry_run.py`

## Current workflow shape

`XCasualComposerWorkflow` is a single-shot read-only approval lane:

```text
is_casual_channel_configured
→ gather_casual_materials
→ bundle_score gate
→ casual_compose_one
→ blocking flag drop
→ dry_run result OR persist_original
→ post_casual_to_discord
→ update_original_thread
→ exit
```

The workflow posts drafts to Discord `#x-drafts`; Mike manually copies anything worth posting to X. It does not run an approval reaction loop and does not auto-post to X.

## Current gather sources

`casual_gather.py` gathers:

- Source A: `signals`, last 24h, high priority only
- Source B: `news_moments`, last 12h, P0/P1 only
- Source C1: `radar_pulses`, last 7d

Source C2 git activity is intentionally dropped because it produced incoherent internal-jargon tweets.

Current bundle score:

```text
max(
  source_a_signals * 1.0,
  source_b_x_news  * 0.9,
  source_c1_pulse  * 0.7
)
```

Current threshold: `0.75`.

Implication: pulses alone should normally not trigger compose.

## Current compose behavior

`casual_compose_one()` currently performs:

```text
build_angle_contract(bundle)
→ pick_tone()
→ _llm_compose()
→ Simplified lint + one regen
→ humanize_text()
→ zh/HK AI-tell lint + one regen
→ check_contract_drift()
→ length flags
→ post-humanize Simplified check
→ fabricated version check
→ fabricated proper-noun check
→ URL phantom gate
→ embedding dedup
→ return candidate
```

Current `AngleContract` is deterministic and chooses:

1. `x_news[0]`
2. `signals[0]`
3. `pulses[0]`
4. none

It records `source_ref`, `source_kind`, `actor`, `concrete_fact`, `allowed_claims`, `forbidden_claims`, `consequence`, `source_priority`, `source_text`, and `other_actors`.

## Existing strengths to preserve

- Source-first AngleContract before loose bundle context
- Primary-source preference over pulses
- Simplified-character hard gate
- zh/HK AI-tell lint and bounded regen
- Fabricated specific/version checks
- Fabricated proper-noun checks
- Contract drift flags
- URL phantom gate
- Embedding dedup against recent x_originals and editorial articles
- Discord metadata showing source/fact/drift/dedup flags

## Existing gaps

- `draft_lang` is hardcoded to `zh-hk`.
- Prompt hardcodes HK Traditional written register and forbids Cantonese vernacular.
- No content-type contract exists.
- No context-selected language/register selector exists.
- No stance/coherence ledger exists.
- Dedup is semantic similarity, not stance continuity.
- Discord metadata does not expose content type, language profile, stance, contradiction result, or why-share rationale.
- Current dry-run test only checks `_is_dry_run`; it does not prove full side-effect isolation.

## Parallel workflow note

`XInteractionWorkflow` / reply-quote lane uses separate drafting logic. Initial revamp scope keeps it out of EXECUTE unless PLAN explicitly expands scope. A later convergence pass may align both lanes after original-new x-draft is stable.

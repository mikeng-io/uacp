# Design — Cortex x-draft revamp

Run: `cortex-x-draft-revamp-20260514`
Target Temporal workflow: `XCasualComposerWorkflow`
Schedule id: `x-casual-composer`
Manual trigger: `scripts/fire_x_casual_composer.py`

## Target lane

This plan targets the original/new X tweet draft lane only:

```text
src/cortex/workflows/x_casual_composer.py::XCasualComposerWorkflow.run
```

Direct workflow activities in scope:

```text
casual_approvals.is_casual_channel_configured
casual_gather.gather_casual_materials
casual_compose.casual_compose_one
casual_state.persist_original
casual_approvals.post_casual_to_discord
casual_state.update_original_thread
```

Scheduler binding in scope only for verification/read-only inspection:

```text
src/cortex/scheduler.py schedule id x-casual-composer
```

Not in initial implementation scope:

- `XInteractionWorkflow`
- `XNewsPollerWorkflow`
- `EditorialWorkflow`
- `DraftPipelineWorkflow`
- live Temporal schedule mutation
- public X posting

## Architecture principle

Do not replace the existing lane. Add a planning/coherence layer around the current source-grounded compose path.

Current preserved core:

```text
MaterialBundle
→ AngleContract
→ Compose
→ existing gates
→ Discord #x-drafts
```

Target core:

```text
MaterialBundle
→ AngleContract
→ ContentIntentContract / DraftPlan
→ PriorStanceContext
→ Compose
→ StanceCoherenceCheck
→ existing gates
→ Discord #x-drafts metadata
```

## New contract: ContentIntentContract / DraftPlan

Purpose: decide what kind of public thought this candidate is and how it should speak.

Proposed shape:

```python
@dataclass
class ContentIntentContract:
    content_type: str
    subject: str
    scoped_stance: str
    why_share: str
    why_now: str
    language_mode: str
    register_notes: list[str]
    tone: str
    allowed_framing: list[str]
    forbidden_framing: list[str]
    coherence_query: str
```

Allowed `content_type` values:

```text
purpose_agent_observation
useful_repo_share
useful_article_share
tool_evaluation
build_note
governance_note
simple_reaction
technical_explainer
trustless_uacp_cortex_note
```

Allowed `language_mode` values:

```text
zh_hk_written          # existing default/fallback
cantonese_english
traditional_chinese_english
english_led_hybrid
cantonese_led
plain_english
```

## Register selector

The register selector should be deterministic/config-assisted first, LLM-assisted only if needed.

Initial mapping:

| Content type | Default language/register | Notes |
|---|---|---|
| `purpose_agent_observation` | `cantonese_english` | Natural Mike/Norty operational observation. |
| `useful_repo_share` | `cantonese_english` or `plain_english` | Depends on whether source/audience is local-HK or broader technical. |
| `useful_article_share` | `traditional_chinese_english` or `plain_english` | Use English if the article/audience is global technical. |
| `tool_evaluation` | `cantonese_english` or `english_led_hybrid` | Must be scoped and non-fake. |
| `build_note` | `cantonese_english` | Avoid internal jargon unless public-framed. |
| `governance_note` | `plain_english` or `english_led_hybrid` | Technical precision matters. |
| `simple_reaction` | `cantonese_led` or `cantonese_english` | Light vernacular allowed. |
| `technical_explainer` | `plain_english` or `english_led_hybrid` | Avoid translationese. |
| `trustless_uacp_cortex_note` | `english_led_hybrid` or `traditional_chinese_english` | Expose concepts through public consequences, not raw doctrine. |

## Language mode examples

### `cantonese_english`

```text
呢個 repo 好睇嘅位唔係 UI，而係佢將 planning、execution、verification 分得乾淨。好多 agent framework 最大問題就係三樣嘢混埋，debug 起上嚟冇 receipt。
```

### `traditional_chinese_english`

```text
這篇值得看，因為它沒有停在「AI 會改變一切」那層，而是直接拆 deployment friction：權限、成本、latency、ownership。
```

### `english_led_hybrid`

```text
The useful part is the boundary: plan, execute, verify. Agent systems break fastest when those three states collapse into one prompt blob.
```

### `cantonese_led`

```text
講真，呢類 agent demo 最有用通常唔係 demo 本身，而係你睇到佢邊個位開始需要 state、rollback 同 ownership。
```

### `plain_english`

```text
This repo is useful because it treats agent execution as a state problem, not just a prompting problem. The implementation is rough, but the boundary is worth studying.
```

## Stance/coherence guard

Initial implementation should avoid a new DB table unless PLAN execution proves it necessary.

Phase 1 stance context source:

```text
recent x_originals + editorial_articles_index + available metadata
```

Derived fields:

```python
@dataclass
class PriorStanceContext:
    subject: str
    matched_prior_outputs: list[dict]
    prior_stance_summary: str | None
    contradiction_risk: str  # none | low | medium | high
    allowed_evolution: str | None
    forbidden_reversal: str | None
```

Stance rules:

- Praise/criticism must be scoped.
- If prior stance exists, new stance must be compatible or explicitly evolutionary.
- Prior use of a tool/repo must not be represented as first discovery.
- Mixed stance is preferred when source evidence is partial.

Examples:

```text
Bad: Tool X is great; we should use it.
Good: Tool X is weak as a general agent, but its repo indexing is useful as a narrow reference pattern.
```

```text
Bad: This repo solves agent execution.
Good: This repo has a useful boundary between planning and verification; I would not adopt the whole stack unchanged.
```

## Gate ordering

Recommended initial ordering inside `casual_compose_one()`:

```text
1. build_angle_contract(bundle)                         # existing
2. build_content_intent_contract(bundle, angle_contract) # new
3. fetch_prior_stance_context(intent, angle_contract)    # new, read-only
4. _llm_compose(bundle, tone, angle_contract, intent, prior_stance)
5. post-compose stance_coherence_check(humanized, prior_stance, intent)
6. existing Simplified/zh/fabrication/URL/dedup gates
```

A later implementation may move some stance checks before humanization if needed, but the initial plan should minimize disruption.

## Config changes

Add to `config/x_casual.yaml`:

```yaml
content_intent:
  enabled: false       # start false or dry-run-only until verified
  mode: auto
  allowed_content_types: [...]
  language_modes: [...]
  default_language_mode: zh_hk_written
  expose_metadata_in_discord: true

coherence:
  enabled: false       # start false or advisory until tests pass
  lookback_days: 30
  contradiction_threshold: medium
  block_unscoped_reversal: true
  derived_from: [x_originals, editorial_articles_index]
```

Feature flags should allow current behavior to remain available.

## Persistence strategy

Initial implementation can store additional metadata in existing JSON-ish fields if available, or return it in candidate dict and Discord display only. If durable analysis proves necessary, add a migration in a later subtask.

Do not introduce a DB migration in the first implementation unless the code inventory shows no safe place to persist metadata.

## Discord surface

`post_casual_to_discord()` should display compact metadata:

```text
type useful_repo_share · lang cantonese_english · stance mixed-positive
source x_news:0 · actor ... · coherence compatible
why: ...
```

Keep source/fact/drift/dedup flags visible.

## Prompt strategy

Do not create 100+ prompt variants. Render the intent contract as a structured block, same pattern as `format_angle_contract()`.

Add:

```text
### CONTENT INTENT CONTRACT
content_type: ...
language_mode: ...
scoped_stance: ...
why_share: ...
prior_stance: ...
forbidden_reversal: ...
```

Then instruct: compose natively in the selected register; do not translate after writing.

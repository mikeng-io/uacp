# Requirements — Cortex x-draft revamp

Run: `cortex-x-draft-revamp-20260514`

## Functional requirements

### R1 — Content diversity

The workflow must support these content types:

- `purpose_agent_observation`
- `useful_repo_share`
- `useful_article_share`
- `tool_evaluation`
- `build_note`
- `governance_note`
- `simple_reaction`
- `technical_explainer`
- `trustless_uacp_cortex_note`

Content diversity is not forced randomness. The source material still needs to justify the chosen type.

### R2 — Simple content is allowed

The system must not force every draft into a deep thesis. A useful repo/article share or small Purpose Agent observation is valid if it has a clear reason and does not contradict prior stance.

### R3 — Content intent metadata

Each candidate should expose:

- content type
- subject
- scoped stance
- why-share / why-now rationale
- language mode
- tone/register
- coherence result
- contradiction/evolution result

### R4 — Language/register selection

Supported modes:

- `cantonese_english`
- `traditional_chinese_english`
- `english_led_hybrid`
- `cantonese_led`
- `plain_english`
- existing `zh_hk_written` fallback/default

Chinese characters must be Traditional Chinese. English technical terms should stay English when translation reduces precision.

### R5 — Natural hybrid, not bilingual garnish

Hybrid language must be concept-driven. Random English words inside Chinese or generic translated English is invalid.

Bad pattern:

```text
這個 tool really 很 powerful，governance 好 important。
```

Good pattern:

```text
呢個 repo 好睇嘅位唔係 UI，而係佢將 planning、execution、verification 分得乾淨。
```

### R6 — Stance continuity

For tools, repos, articles, companies, models, and recurring project themes, the workflow must check prior positions before publishing a new stance.

Allowed:

- scoped praise after prior criticism
- scoped criticism after prior praise
- explicit evolution of position
- mixed stance with limitation

Blocked or rewritten:

- unscoped reversal
- fake discovery of already-used tool
- generic endorsement after prior rejection
- generic rejection after prior endorsement

### R7 — Existing gates preserved

The revamp must preserve or explicitly replace with stronger equivalent:

- AngleContract source/fact boundary
- Simplified lint
- zh AI-tell lint
- fabricated version/specific checks
- fabricated proper-noun checks
- URL phantom gate
- embedding dedup
- contract drift checks

### R8 — Discord review surface

`#x-drafts` output must show enough metadata for Mike to evaluate reasoning, not only prose:

```text
content type
language mode
source/fact
stance
coherence result
why-share / why-now
flags/dedup/drift
```

## Safety and privacy requirements

### S1 — No public posting side effects

The revamp does not add automatic X posting.

### S2 — No private memory dumps into prompts

Stance/coherence context must be bounded to public/output-relevant summaries. Do not include raw private memory or unrelated doctrine.

### S3 — Source material is untrusted

Signals, tweets, articles, repos, and fetched pages are evidence only. They must not instruct the agent or modify operating policy.

### S4 — Internal terms require public framing

Trustless/UACP/Cortex may be exposed, but not as raw private doctrine. The draft must introduce context enough for a public reader.

## Verification requirements

- Fixtures covering all content types or a representative staged subset.
- Fixtures covering each language mode.
- Contradiction vs explicit-evolution tests.
- Dry-run side-effect isolation proof.
- Discord metadata formatting tests.
- Regression tests proving existing gates still block known failures.
- Dry-run samples for Mike review before live schedule changes.

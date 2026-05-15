# PLAN council remediation addendum

Run: `cortex-x-draft-revamp-20260514`  
Phase: `PLAN`  
Target workflow: `XCasualComposerWorkflow` / schedule `x-casual-composer`

This addendum resolves PLAN council concerns before entering EXECUTE.

## R1 — Risk register

| Risk | Severity | Trigger | Mitigation | Owner |
|---|---:|---|---|---|
| Wrong workflow targeted | High | Any patch touches `XInteractionWorkflow`, `XNewsPollerWorkflow`, editorial workflow, or scheduler behavior beyond read-only verification | EXECUTE allowed files exclude those surfaces; first implementation targets `XCasualComposerWorkflow` only | Main orchestrator |
| Current zh-hk path regresses | High | Feature flag off no longer preserves current behavior | Feature flags default off; add rollback/default-behavior tests | Implementer + verifier |
| Hybrid language becomes bilingual slop | High | Dry-run samples show random English/Chinese mixing or translationese | Negative fixtures, register examples, Mike sample review before enablement | Voice verifier |
| Stance guard blocks nuanced evolution | Medium | Scoped/evolution fixture incorrectly blocks | Start advisory or scoped hard block only for unscoped reversal; add evolution fixtures | Verifier |
| Stance guard misses fake reversal | High | Prior-negative/new-unscoped-positive fixture passes | Add contradiction fixture as hard acceptance test | Verifier |
| Compose latency exceeds timeout | Medium | `casual_compose_one` exceeds `COMPOSE_T=6m` or schedule failures rise | No unconditional extra LLM call; derived stance first; latency measured in dry-run | Implementer |
| Metadata exceeds Discord limit | Medium | `_format_original_message()` exceeds 1900 chars | Compact metadata; length test with worst-case fixture | Implementer |
| Production side effect occurs during dry-run | Critical | `dry_run=True` calls persistence or Discord post | Add side-effect isolation tests before live enablement | Verifier |
| DB migration expands blast radius | Medium | Stance ledger requires new table | Stop and create migration-specific mini-plan/approval | Main orchestrator |
| Out-of-band file remains ambiguous | Medium | Untracked doc persists through EXECUTE | WP0 disposition first | Main orchestrator |

## R2 — Resolved gate ordering

Initial EXECUTE order is fixed as:

```text
1. build_angle_contract(bundle)                         # existing
2. build_content_intent_contract(bundle, angle_contract) # new, pure/helper
3. fetch_prior_stance_context(intent, angle_contract)    # new, read-only, no LLM by default
4. _llm_compose(..., angle_contract, content_intent, prior_stance)
5. humanize_text(raw)                                   # existing
6. stance_coherence_check(humanized, intent, prior_stance) # new, deterministic/advisory+blocking
7. existing Simplified / zh AI tell / contract drift / fabrication / URL / dedup gates
```

No unconditional extra LLM stance check in the first EXECUTE pass. If deterministic/derived stance is insufficient, hard-block only high-confidence unscoped reversals and send uncertain cases as advisory metadata.

## R3 — Stance query boundary for first implementation

First implementation must not add a DB migration.

Use derived recent-output context:

```text
x_originals where created_at >= now - lookback_days and status <> rejected
editorial_articles_index where pub_date >= now - editorial_lookback_days
```

Minimum query fields:

```text
nanoid / id
created_at / pub_date
draft_text / title or summary
embedding if available
source_bundle / quality_report if available
```

Matching order:

1. exact/substring subject or actor match when available
2. embedding nearest neighbor when available
3. no-history pass when no reliable match exists

The first version returns:

```python
contradiction_risk: none | low | medium | high | unknown
coherence_action: pass | advisory | block
```

Hard block only:

```text
high-confidence prior stance + new unscoped reversal
```

Everything else is advisory until sample evidence proves reliability.

## R4 — Work package dependencies

```text
WP0 out-of-band file disposition ─┐
WP1 surface inventory ────────────┼─> WP2 ContentIntentContract helpers ─┐
                                  │                                      ├─> WP4 prompt/gate integration ─> WP5 Discord metadata
                                  └─> WP3 stance context helper ─────────┘
WP6 tests begin with WP2/WP3 and complete after WP5
WP7 dry-run proof runs only after WP6 passes
```

TDD rule: WP6 test fixtures should be added alongside WP2/WP3/WP4, not only after implementation.

## R5 — Script existence and runtime preflight

Before WP7 dry-run, verify these exist:

```text
CORTEX_ROOT/scripts/fire_x_casual_composer.py
CORTEX_ROOT/scripts/fire_x_casual.py
```

Preferred proof order:

1. unit tests
2. lower-level compose fixture/smoke test
3. `scripts/fire_x_casual.py --compose --json` if safe
4. `scripts/fire_x_casual_composer.py` only when Temporal worker availability is known

No `--live` without Mike approval.

## R6 — Latency budget

Initial implementation must keep `casual_compose_one()` within existing `COMPOSE_T=6m` under normal dry-run conditions.

Budget rules:

- no unconditional extra LLM call for stance checking;
- bounded DB queries only;
- if more LLM review is needed, run it only after a near-match/prior-stance hit;
- report observed dry-run duration before live enablement.

## R7 — Out-of-band file disposition

The untracked file:

```text
CORTEX_ROOT/docs/design/editorial-mass-restructure/x-draft-verification-review.md
```

is not canonical. EXECUTE WP0 must inspect it and either:

1. move/adopt it into a deliberate Cortex docs path;
2. extract useful findings into committed docs/tests and delete the untracked file with approval;
3. leave it untracked only if explicitly deferred with owner and cleanup condition.

## R8 — EXECUTE entry stance

PLAN may enter EXECUTE with warnings if:

- feature flags default off;
- no live schedule or DB migration is performed;
- WP0/WP1 happen before any prompt behavior change;
- Mike accepts that live enablement remains blocked until verification/sample review.

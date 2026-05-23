# Operator Returns and Semantic Package Artifacts — 2026-05-19

## Trigger

During UACP work, Mike corrected two related failure modes:

1. Operator-channel returns were dumping raw file lists, diff stats, and artifact inventories instead of giving decision-grade information.
2. A Discord UACP task treated Markdown proposal/plan files as optional and created only YAML envelopes, which was insufficient for future semantic recovery.

## Durable rule

Separate three surfaces:

- **Machine lifecycle envelope:** YAML files that carry structured lifecycle state and validator/Heartgate fields.
- **Semantic package substrate:** Markdown package files that explain why the work exists, how it works, intention, rationale, decision, authority, scope, containment, risks, verification, rollback, and transition readiness. These are for humans *and future agents*.
- **Operator phase return:** short Telegram/Discord summary that gives conclusion, meaning, decision/status, invariants, material risks, next action, and evidence pointer.

Do not confuse these surfaces. A YAML envelope is not enough for standard/full governance work when adaptive package selection applies. A Markdown package is not an excuse to spam the operator channel. Operator chat receives the summary layer; package Markdown preserves semantic recoverability; raw evidence stays in artifacts/logs/commits.

## Required semantic recovery test

For selected PROPOSE/PLAN packages, ask:

> If Mike or a future agent returns one month later with no chat history, can they recover why we did this, how it works, the rational intent, and the decision boundary from the package Markdown?

If not, the package is incomplete, even if YAML validates.

## Presentation rule

Default phase returns must suppress:

- full edited-file/new-file lists
- raw diff stats
- raw validator logs
- raw council transcripts
- full artifact inventories

Include paths only when needed for a blocker, rollback, explicit decision, or requested audit detail.

## Implementation surfaces

When this class of issue appears, patch the governing UACP skills and validator/schema behavior, not only the affected run artifacts. One-off proposal repair fixes the symptom; skill + validator enforcement fixes the system.

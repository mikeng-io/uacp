## Phase 2: Routing

The `tier` parameter determines the council's scale and dispatch mechanism.

### Inputs to tier selection

1. **Explicit user input** — if the invocation specified `tier: N`, use it.
2. **Derived from working_scope** if unspecified:

| Signal | Suggested tier |
|--------|---------------|
| `domains_count == 1` AND trivial scope AND no integration concerns | 0 |
| `domains_count <= 5` AND no high-stakes signals AND `intensity != thorough` | 1 |
| `domains_count > 5` OR explicit cross-runtime / multi-model request OR `intensity == thorough` AND domain count moderate | 2 |
| `domains_count >= 9` OR security/compliance signal OR explicit "deep" / "highest confidence" request OR irreversible decision | 3 |

High-stakes signals (from the user prompt or scope): `critical`, `security`, `compliance`, `production`, `cryptographic`, `financial`, `audit`, `irreversible`.

### Tier-up rule (post-dispatch escalation)

If a Tier 1 council completes with:
- 3+ `disputed` findings, OR
- aggregate confidence `low`, OR
- a domain expert explicitly flagged "needs cross-runtime verification"

→ Re-dispatch at Tier 2 (or Tier 3 for high-stakes). Record the escalation in the final artifact's `tier_history` field. Do not silently swallow the lower-tier output — include it as `prior_tier_report` for transparency.

### Tier-down rule (don't inflate)

Do not run Tier 3 for ≤2-domain routine reviews. Tier inflation wastes context and time. If in doubt, start at Tier 1 and let the tier-up rule escalate.

Record the selected tier in `council_manifest.tier`.

### Finding-driven mode: IC-tier asymmetry

When `mode == "finding-driven"` with `fixes_applied` containing ≥2 fixes AND at least one **signal-gating trigger** fires, the **Integration Checker may run at a higher tier than the rest of the council**. Fix-interaction analysis (Check #4 in Finding-Driven Mode) is where runtime diversity helps most — but only when the interaction is non-obvious. When the interaction is encoded directly in the diff, a Tier-1 IC will catch it; running cross-runtime IC adds N× context for the same finding.

**Signal-gating triggers (raise IC tier when one or more is present):**

- Concurrency / locks / mutexes / shared state across goroutines or threads
- Persistent storage migrations or schema changes
- Security-sensitive code (auth, crypto, session handling, secret material)
- Cross-component invariants (e.g., shared cache key, distributed lock, API contract)
- Reordering of side effects across components
- More than 5 fixes (combinatorial blast — pairs × triples grow fast)

**Without any trigger, keep IC at the council tier.** Fix count alone is not enough.

| Council intent | Council tier | IC tier |
|---------------|--------------|---------|
| Multi-fix re-review, no signal-gating trigger | 1 | 1 |
| Multi-fix re-review with concurrency / shared state / security signal | 1 | **2** |
| Critical-proposal multi-fix re-review, signal-gated | 2 | **3** |

Record both as `council_manifest.tier` and `council_manifest.ic_tier`. The actual hoist is executed in Phase 4 Dispatch (see `[skills-root]/uacp-council/references/phase-4-dispatch.md`). See Finding-Driven Mode (see `[skills-root]/uacp-council/references/finding-driven-mode.md`) for the four-check framework.
## Finding-Driven Mode

A `finding-driven` council is anchored to a specific findings list — the "lens" through which it views the artifact. Use it whenever the council should assess the artifact **in relation to known concerns**, not as an open exploration.

### Use cases

| Use case | What the `findings` list contains |
|----------|----------------------------------|
| **Post-fix re-review** | Prior council's findings (Stage 1 findings being re-checked after fixes) |
| **Spec compliance check** | Requirements from the spec (each requirement is a "finding to verify") |
| **Regression check after a change** | Known historical bugs or behaviors that must not regress |
| **Targeted review** | User-listed concerns ("review around these 4 things") |
| **Threat-model assessment** | Listed threats from a STRIDE/PASTA exercise |

### Required inputs

```yaml
finding_driven_input:
  mode: "finding-driven"
  findings: []                  # the findings list (the lens) — see Finding Object Schema below
  fixes_applied: ""             # OPTIONAL — diff/description of changes since findings were surfaced
  original_proposal: ""         # OPTIONAL — the design/spec/intent being upheld
  prior_session_id: ""          # OPTIONAL — if findings came from a prior council session
  # ... + standard fields (scope, domains, tier, intensity)
```

**Finding object schema** (canonical definition in `uacp-bridge/SKILL.md` "Finding Object Schema"):

Each item in `findings` must have `{id, title, description, severity, domain, source}`. Items can be lifted directly from a prior `uacp-council` artifact's `outputs[]` array — they already conform. For spec-compliance use, each spec requirement becomes one finding (with `source: "spec:<path>"`).

The three optional inputs unlock additional checks:
- Without `fixes_applied` → only resolution check runs (verify each finding against the artifact)
- With `fixes_applied` → resolution + regression + fix-interaction checks
- With `original_proposal` → design-drift check is added

### The four checks

A finding-driven council performs up to four checks, depending on inputs provided:

| # | Check | Question | Requires |
|---|-------|----------|----------|
| 1 | **Resolution** | Did each finding get addressed? | always |
| 2 | **Regression** | Did the fix introduce new issues in the same domain? | `fixes_applied` |
| 3 | **Design drift** | Did the fix subtly violate the original proposal's intent? | `fixes_applied` + `original_proposal` |
| 4 | **Fix interaction** | Do *combinations* of fixes create new issues that no single fix would alone? | `fixes_applied` (≥2 fixes) |

Check #4 is the most commonly missed: naive re-review treats each fix as isolated. Real systems have invariants that span fixes, and fix(F1) + fix(F2) together can break what fix(F1) alone preserves.

### Tier interaction (important asymmetry)

Finding-driven councils may dispatch the **Integration Checker at a higher tier than the rest of the council**, because fix-interaction (Check #4) is exactly where runtime diversity helps catch shared-blind-spot misses.

| Council intent | Rest of council | Integration Checker |
|-----------------|---------------------|
| Trivial fix re-review (1 finding, 1 fix) | Tier 1 | Tier 1 |
| Multi-fix re-review (≥2 fixes interact) | Tier 1 | **Tier 2** (cross-runtime IC) |
| Critical proposal, multi-fix re-review | Tier 2 | **Tier 3** (cross-runtime IC + debate) |

Record this in the artifact as `ic_tier`: the tier the Integration Checker actually ran at.

### Domain expert prompt (re-review with fixes)

```
This is a finding-driven council. You are a {expert_role}.

You are NOT doing an open review. You are assessing the artifact through the lens
of specific findings.

SCOPE: {scope}
DOMAINS: {domains}
INTENSITY: {intensity}

Prior findings (the lens):
{findings filtered to your domain — and findings in adjacent domains for cross-checks}

Fixes applied since findings were surfaced:
{fixes_applied}

Original proposal (must be upheld):
{original_proposal — only if provided}

Run up to four checks (skip the ones whose inputs are missing):

1. RESOLUTION
   For each prior finding in your domain, report:
   - status: addressed | partially-addressed | not-addressed | superseded | obsolete
   - evidence: specific reference to the fix (or note why not addressed)

2. REGRESSION (only if fixes_applied)
   Did the fixes introduce new issues in YOUR domain that didn't exist before the fix?
   Produce findings with type: "regression-finding".

3. DESIGN DRIFT (only if fixes_applied AND original_proposal)
   Where did the fix subtly diverge from the proposal's stated intent?
   Look for: changed contracts, weakened invariants, scope creep, removed behaviors
   that the proposal required. Produce findings with type: "design-drift-finding".
   These are often more important than the original findings because they're invisible
   to the person who applied the fix.

4. CROSS-DOMAIN IMPACT
   Where did a fix in ANOTHER domain affect your domain? (You are positioned to see
   this; the other domain's expert is not.) Produce findings with type: "cross-domain-impact".

Return outputs in the standard council schema. Tag each output by `type`:
- `resolution` — status check for a prior finding. MUST include `target_finding_id` (referencing the input finding's id) and `resolution_status` (`addressed | partially-addressed | not-addressed | superseded | obsolete`). Severity is `null`.
- `regression-finding` — new issue introduced by a fix in your domain.
- `design-drift-finding` — fix-vs-proposal divergence.
- `cross-domain-impact` — finding where a fix in another domain affects yours.

All items go into the single `outputs[]` array — consumers filter by `type`. Do NOT emit parallel arrays.
```

For the Integration Checker prompt used in Check #4, read:

```
Read: [skills-root]/uacp-council/experts/integration-checker.md
```

### Output

Finding-driven mode does NOT introduce new top-level arrays. All items go into the canonical `outputs[]` array, tagged by `type`. The council-level schema gains only two finding-driven-specific fields (in addition to the always-present `ic_tier`):

```json
{
  "mode": "finding-driven",
  "prior_session_id": "...",       // already in the council report schema
  "input_findings_count": 5,        // already in the council report schema
  "ic_tier": 2                      // already in the council report schema; documents actual IC tier
}
```

Consumer-side filtering (examples):
- Resolution checks: `outputs.filter(o => o.type === "resolution")`
- Regression findings: `outputs.filter(o => o.type === "regression-finding")`
- Design-drift findings: `outputs.filter(o => o.type === "design-drift-finding")`
- Fix-interaction findings: `outputs.filter(o => o.type === "fix-interaction-finding")`

### Verdict logic for finding-driven mode

Defined canonically in `uacp-bridge/SKILL.md` "Verdict Logic" → "For `mode == finding-driven`". Do not duplicate the table here. The short version: any unaddressed CRITICAL/HIGH or any CRITICAL new-issue (regression/drift/interaction) → `FAIL`. Any HIGH new-issue → `CONCERNS`. Otherwise → `PASS`.

A re-review that says "all fixes addressed their findings" but introduces design drift is still `CONCERNS` — that's the point of the mode.

### Adversarial posture — verification-gate mode (default-to-refute, majority-clear)

When a finding-driven council runs as a **verification gate** — the council as the generative gate run as a panel (`design/verification-method/14-council-method.md`) — invert the default and raise the bar to clear. This is the posture, not a new schema: it changes the *prior* and the *clearing threshold*.

- **Default-to-refute.** Each verifier starts from *the claim is unproven* and must be argued INTO a clear by evidence bound to the real artifact — never the reverse. "No objection found" is **not** a clear: absence of evidence is a refutation, not a pass (fail-closed — the #503 class-A failure, treating a check that found nothing as PASS). State the refutation you could not overturn, with its grounding.
- **Majority-clear.** A claim clears only when a **majority** of the dispatched verifiers affirm it on grounded evidence; a tie, or a lone affirmation against silence, does **not** clear it. This is where cross-runtime diversity (the higher-tier Integration Checker, above) earns its keep — a shared blind spot cannot manufacture a majority.
- **Serialize the verdicts.** Each verifier's refute/affirm + its evidence ref is written to the investigation ledger (`design/verification-method/13-investigation-ledger.md`) as the auditable trail — not collapsed into the council's single PASS/CONCERNS/FAIL.

Net effect: the gate **fails closed when the panel is uncertain**. Use this posture for verification/phase-end councils; the open and standard finding-driven defaults (above) are unchanged for non-gate reviews.
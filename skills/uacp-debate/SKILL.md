---
name: uacp-debate
description: Generic structured adversarial protocol for review, audit, research synthesis, and brainstorm/design councils within UACP. Supports finding validation plus proposal brainstorming lifecycles, packetized exchanges, and auditable manifests for nested councils.
kind: orchestration
location: managed
dependencies:
  - uacp-core   # domain registry: uacp-core/references/domains/
  - uacp-bridge
allowed-tools:
  - Read
  - Task
  - Write
  - Bash(mkdir *)
---

# Debate Protocol: Generic 5-Phase Adversarial Analysis

Execute this skill to run structured adversarial analysis among domain experts and structural challengers. The protocol produces high-confidence findings through independent investigation, publication, challenge, synthesis, and final verdict.

## When to Use This Skill

Use debate when you need adversarial validation — the structured attempt to disprove each finding before accepting it as real. It is not brainstorming and not round-table discussion.

- Use `review` or `audit` mode to validate existing findings under challenge.
- Use `brainstorm` or `design` mode for divergent proposal generation followed by adversarial convergence.
- Use `research` or `synthesis` mode to validate evidence quality and conclusion validity across sources.

Read `references/what-debate-is-for.md` for scope, mode selection, and how brainstorm mode differs.

## Input Contract

Accept the following input from conversation context or caller:

```yaml
debate_input:
  review_id: ""          # Unique ID for this debate session (generate UUID if not provided)
  review_scope: ""       # What is being reviewed, researched, or designed
  mode: "review"         # review | audit | brainstorm | design | research | synthesis
  domains: []            # Domains selected (from the domain registry or caller)
  intensity: "standard"  # quick | standard | thorough
  context_summary: ""    # Neutral context summary
  context_policy: "minimal-non-leading" # Round 1 policy for discovery/brainstorm
```

## Orchestration Flow

Run the phases below in order. At each phase, Read the corresponding reference file before constructing participant prompts.

### Setup

1. **Read `references/what-debate-is-for.md`** — confirm mode and whether brainstorm or review lifecycle applies.
2. **Read `references/valid-challenge.md`** — load challenge validity rules and DA obligations.
3. **Read `references/intensity-modes.md`** — select phase set, `max_rounds`, and parameter preset (`default` or `security-elevated`).

### Execution

4. **Phase 1 — Independent Investigation:** Read `references/phase-1-investigation.md`. Spawn one domain expert per domain (from `uacp-core/references/domains/`), one Devil's Advocate, and one Integration Checker in isolated parallel Task agents. No participant sees another's work.
5. **Phase 2 — Finding Publication:** Read `references/phase-2-publication.md`. Collect findings, assign unique IDs (F001, F002, ...), and broadcast the complete inventory to all participants. No responses yet.
6. **Phase 3 — Challenge Round:** Read `references/phase-3-challenge.md`. Run up to `max_rounds` of adversarial challenge. Devil's Advocate MUST challenge every CRITICAL/HIGH finding not originated by DA. Valid challenges must identify a missing assumption, propose an alternative explanation, or surface a non-applicability scenario.
7. **Phase 4 — Synthesis:** Read `references/phase-4-synthesis.md`. Merge findings with >70% description overlap, update states (`confirmed`, `withdrawn`, `disputed`, `merged`, `discovered`), and resolve cross-domain duplicates.
8. **Phase 5 — Final Verdict:** Read `references/phase-5-verdict.md`. Collect final positions from all participants, record dissent, and compute PASS / CONCERNS / FAIL from confirmed findings.

## Expert Files

Load these before spawning Phase 1 participants:

- `experts/devils-advocate.md` — adversarial challenge obligations, valid challenge types, and message formats
- `experts/integration-checker.md` — cross-domain coupling checks and integration-specific response guidance

## Fallback and Packet Contracts

- If TeamCreate is unavailable, Read `references/fallback-mode.md` and run parallel Task sub-agents. Emit `"mode": "adversarial_subagents"` and omit or null `team_session_id`. Never label a fallback run as `"mode": "debate"`.
- For nested councils or auditability requirements, Read `references/packet-contract.md` for `CouncilTaskPacket`, `ExchangeEnvelope`, and brainstorm proposal schemas. Round 1 discovery/brainstorm must use `context_policy: minimal-non-leading`.

## Output

Save two artifacts per run. Read `references/artifact-output.md` for the full contract, schema requirements, and frontmatter format.

- JSON log: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.json`
  - MUST conform to `.agents/skills/state/schemas/gate_1_debate_log.schema.json` (v1.0)
  - Consumed by `record_gate_1_result`; do not recompute derived fields downstream
- Markdown summary: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.md`

Do not fabricate participant voices. Every `messages[]` entry must correspond to a real Task-agent or TeamCreate-session message that actually happened.

## Integration Notes

- Domain experts are resolved through the domain registry (`uacp-core/references/domains/`) using exact match, adapted match, or session-based virtual expert selection.
- Council taxonomy and role contracts are sourced from `../uacp-core/references/council-taxonomy.md`.
- Shared bridge conventions (packet schemas, envelope formats) are inherited from `uacp-bridge`.
- Do not change existing path references (`.agents/skills/state/schemas/gate_1_debate_log.schema.json`, `.uacp/debate/`, etc.).

## Verification Checklist

Before finishing a debate run, confirm:
- [ ] `review_id` is set and consistent across both artifacts
- [ ] `mode` is correctly labelled (`debate` vs `adversarial_subagents`)
- [ ] `team_session_id` matches the TeamCreate session when `mode: debate`
- [ ] `messages[]` contains only real participant messages
- [ ] JSON log conforms to `gate_1_debate_log.schema.json` v1.0
- [ ] Markdown frontmatter includes all required fields

**No symlinks.** To find the latest artifact:
```bash
ls -t .uacp/debate/ | head -1
```

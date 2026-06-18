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

4. **Phase 1 — Independent Investigation:** Read `references/phase-1-investigation.md`. Spawn one domain expert per domain (from `uacp-core/references/domains/`), one Devil's Advocate, and one Integration Checker in isolated, concurrent sub-agents (via the runtime's native sub-agent dispatch — see `uacp-bridge`). No participant sees another's work.
5. **Phase 2 — Finding Publication:** Read `references/phase-2-publication.md`. Collect findings, assign unique IDs (F001, F002, ...), and broadcast the complete inventory to all participants. No responses yet.
6. **Phase 3 — Challenge Round:** Read `references/phase-3-challenge.md`. Run up to `max_rounds` of adversarial challenge. Devil's Advocate MUST challenge every CRITICAL/HIGH finding not originated by DA. Valid challenges must identify a missing assumption, propose an alternative explanation, or surface a non-applicability scenario.
7. **Phase 4 — Synthesis:** Read `references/phase-4-synthesis.md`. Merge findings with >70% description overlap, update states (`confirmed`, `withdrawn`, `disputed`, `merged`, `discovered`), and resolve cross-domain duplicates.
8. **Phase 5 — Final Verdict:** Read `references/phase-5-verdict.md`. Collect final positions from all participants, record dissent, and compute PASS / CONCERNS / FAIL from confirmed findings.

## Expert Files

Load these before spawning Phase 1 participants:

- `experts/devils-advocate.md` — adversarial challenge obligations, valid challenge types, and message formats
- `experts/integration-checker.md` — cross-domain coupling checks and integration-specific response guidance

## Dispatch and Packet Contracts

- **Default path:** run the protocol on the runtime's native sub-agent dispatch (see `uacp-bridge`). Read `references/fallback-mode.md` for the per-phase sub-agent flow. Emit `"mode": "independent_subagents"` and omit `session_id`.
- **Optional enhancement:** if the runtime offers a shared live multi-agent session (Claude Code TeamCreate / Hermes·Kimi Swarm), it MAY use that for richer multi-turn exchange. When one is used, emit `"mode": "shared_session"` and record its `session_id`.
- `mode` records WHICH mechanism actually ran — neither is "the real one"; both must honestly reflect what happened.
- For nested councils or auditability requirements, Read `references/packet-contract.md` for `CouncilTaskPacket`, `ExchangeEnvelope`, and brainstorm proposal schemas. Round 1 discovery/brainstorm must use `context_policy: minimal-non-leading`.

## Output

Save two artifacts per run. Read `references/artifact-output.md` for the full field contract and frontmatter format.

- JSON log: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.json`
  - MUST carry the fields defined in `references/artifact-output.md` (the authoritative debate-log contract).
- Markdown summary: `.uacp/debate/{YYYYMMDD-HHMMSS}-debate-{review_id}.md`

Do not fabricate participant voices. Every `messages[]` entry must correspond to a real sub-agent (or shared-session) message that actually happened.

## Integration Notes

- Domain experts are resolved through the domain registry (`uacp-core/references/domains/`) using exact match, adapted match, or session-based virtual expert selection.
- Council taxonomy and role contracts are sourced from `../uacp-core/references/council-taxonomy.md`.
- Shared bridge conventions (packet schemas, envelope formats) are inherited from `uacp-bridge`.
- Artifact paths under `.uacp/debate/` are canonical; the debate-log field contract lives in `references/artifact-output.md`.

## Verification Checklist

Before finishing a debate run, confirm:
- [ ] `review_id` is set and consistent across both artifacts
- [ ] `mode` honestly records which mechanism ran (`independent_subagents` vs `shared_session`)
- [ ] `session_id` matches the shared live session when one was used (absent otherwise)
- [ ] `messages[]` contains only real participant messages
- [ ] JSON log carries all fields defined in `references/artifact-output.md`
- [ ] Markdown frontmatter includes all required fields

**No symlinks.** To find the latest artifact:
```bash
ls -t .uacp/debate/ | head -1
```

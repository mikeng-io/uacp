# Trustless ACP → UACP: Source Analysis

Historical reference only. This file explains what was extracted from Trustless ACP; it is not current UACP authority.

## What Was Analyzed

Three parallel delegate tasks read the complete Trustless ACP implementation:

1. **ACP Lifecycle** — `agent-control-plane.md`, `proposal-schema.md`, `lifecycle-trace.md`, `component-map.md`
2. **Guardian & Constitution** — `guardian.py` (989 lines), `first-principles.md`, `trustless-constitution.md`, `alignment-spec.md`
3. **Skills & Review** — All skills in `.agents/skills/`, workflow docs, quick-reference docs, CLAUDE.md, AGENTS.md

## Trustless ACP: What It Is

A 5-phase governance system for AI-assisted financial platform development:

```
propose → plan → implement → verify → resolve
```

### Key Components
- **9 proposal gates (G0-G8)** — G4 (Feasibility) and G8 (Approval) are non-skippable
- **Guardian** — standalone Python CLI, agent-neutral, enforces phase transitions
- **State skill** — sole authority for state mutations (`.trustless/state/`)
- **External reviewer routing** — centralized config + resolver script
- **Worktree isolation** — implementation writes contained to `.trustless/worktrees/<spec-id>/`

### Review Architecture
- **Gate 0** — Operational Testing
- **Gate 0.5** — Conditional Visual (UI specs)
- **Gate 1** — Agent Council (multi-expert adversarial debate)
- **Gate 2** — External Alignment Review
- **Gate 3** — Lessons Extraction

### Agent Council (5-phase debate)
1. Independent Investigation (parallel, no communication)
2. Finding Publication (broadcast all findings)
3. Challenge Rounds (DA challenges, authors defend)
4. Synthesis (merge overlapping findings)
5. Final Verdict (all submit final positions)

Expert tiers:
- Tier 1 (Core): Devil's Advocate (40% weight), Integration Checker, Test Architect
- Tier 2 (Domain): Database, API, Blockchain, etc. — selected from changed files
- Tier 3 (Dynamic): generated when context needs unlisted expertise

## What's Trustless-Specific (Leave Behind)

| Element | Why Domain-Specific |
|---------|-------------------|
| G0-G8 concrete gates | Financial platform specific gate names and rules |
| proposal.yaml schema | Financial platform fields (topology, implementation_units) |
| Constitutional articles §I-VIII | Financial platform invariants |
| Cross-Spec Awareness | File overlap detection for Trustless modules |
| state.py CLI | Trustless state commands |
| Allowed base refs (develop/master/main/release/hotfix) | Project-specific git workflow |
| Legacy OpenSpec handling | Trustless-specific import/evidence retention |
| Domain experts (blockchain-fabric, regulatory, multi-tenancy) | Financial platform domains |

## What's Universal (Extract to UACP)

| Pattern | How It Manifests |
|---------|-----------------|
| Phase-gate enforcement | Preflight before transition — if check fails, phase blocked |
| Explicit state ownership | State owned by dedicated skill, not agents |
| Constitutional rule hierarchy | Axioms → invariants → specs → execution |
| Spec supremacy | Code bows to approved specification |
| Conservative failure | Missing → hard BLOCK, no silent fallback |
| Actor-indifferent rules | Same rules apply to all agents |
| Write containment | Implementation writes contained to designated workspace |
| Mandatory escalation stops | Defined stop conditions require human clarification |
| Immutable audit trail | Gate results in JSONL ledger with timestamps |
| Multi-agent adversarial council | DA 40% + experts, 5-phase debate |
| Retrieval-led reasoning | Oracle query 8 layers, decision tree before reasoning |
| Gate-based verification pipeline | Sequential gates, each must pass before next |
| Expert tier architecture | core/domain/dynamic |
| Provider-neutral external reviewer dispatch | YAML config + fallback chain |

## Council Skills Inventory (in OpenClaw, not yet in Hermes)

All at `/home/norty/.openclaw/.agents/skills/`:

| Skill | Purpose | Dependencies |
|-------|---------|-------------|
| `deep-council` | Council-of-councils orchestrator | context, preflight, bridge-*, domain-registry |
| `agent-council` | Role-diverse local council | context, preflight, debate-protocol, domain-registry |
| `debate-protocol` | 5-phase adversarial protocol | (standalone) |
| `bridge-claude` | Claude Code bridge adapter | bridge-commons |
| `bridge-codex` | Codex CLI bridge adapter | bridge-commons |
| `bridge-opencode` | OpenCode bridge adapter | bridge-commons |
| `bridge-gemini` | Gemini CLI bridge adapter | bridge-commons |
| `bridge-commons` | Shared bridge utilities | (standalone) |
| `domain-registry` | Domain taxonomy | (standalone) |
| `council-taxonomy` | Council terminology | (standalone) |
| `context` | Artifact classification | domain-registry |
| `preflight` | Scope clarification | context |
| `deep-research` | Research mode council | (needs investigation) |
| `deep-verify` | Verification mode council | (needs investigation) |
| `deep-review` | Review mode council | (needs investigation) |
| `deep-audit` | Audit mode council | (needs investigation) |
| `deep-explorer` | Exploration mode council | (needs investigation) |

## Key Architectural Decisions for UACP

1. **Guardian = skill hooks, not standalone CLI** — preflight checks integrated into lifecycle skills
2. **State = uacp-state skill** — Hermes-native, not a Python CLI
3. **Review = agent-council + deep-council** — adaptive based on context/scope/intensity
4. **Constitution = universal axioms** — not financial platform specific
5. **Workspace = Hermes workspace routing** — worktree/scratch/dir: (not `.trustless/worktrees/`)
6. **Kanban integration** — lifecycle phases map to Kanban tasks with dependency gates

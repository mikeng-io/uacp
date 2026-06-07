# Bridge: Claude

Reference adapter for Claude Code sub-agent dispatch. Part of the Deep Skills Suite bridge layer.

## What is this?

This is a **reference document**, not a runnable skill. Any orchestrating skill reads `SKILL.md` via the `Read` tool and embeds its instructions into Task agent prompts. The bridge defines how to spawn Claude sub-agents as internal reviewers.

## How it works

1. An orchestrating skill reads `bridge-claude/SKILL.md`
2. Spawns a Task agent (the "bridge executor") with these instructions embedded
3. Bridge executor spawns parallel domain expert sub-agents + DA + Integration Checker
4. Bridge executor collects findings and returns a `bridge_claude_report`
5. The calling skill receives the report for synthesis

## Why context: reference?

Claude bridges work via the Task tool — they spawn sub-agents internally. There's no CLI to invoke. The bridge is instructions, not a skill that needs to be "called" separately.

## Availability

Conditional — depends on what's available to the executor:

1. **Task tool** — when Claude Code is the executor (native sub-agent dispatch)
2. **Claude Code CLI** (`which claude`) — when any other executor can shell out to `claude -p`
3. **Anthropic API** — `ANTHROPIC_API_KEY` in environment
4. **SKIPPED** — none of the above available

Bridge-claude is non-blocking — it returns SKIPPED if no Anthropic access is available.

## Output

Returns a `bridge_claude_report` JSON with findings, verdict, and confidence level.

## Part of

- Deep Skills Suite
- Consumed by: any orchestrating skill (e.g., `deep-council`, `deep-review`, `deep-audit`, or custom skills)
- Depends on: `domain-registry` (for expert role selection)

@AGENTS.md

---

## Claude Code — Runtime-Specific

**Preferred dispatch: Task tool** — spawn parallel sub-agents (one per domain + Devil's Advocate + Integration Checker). Always available as fallback.

**Agent Teams** (complex multi-domain work — 3+ domains, thorough intensity):
Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in environment.
Guard: attempt `TeamCreate` first — fall back to Task tool immediately if it fails. Never retry.

**Workflows** (tier ≥3, research/audit, or `ultracode` keyword):
- `/deep-research` — deep multi-step research with recursive subagent dispatch
- `ultracode: <task>` — large-scale coding orchestration (up to 16 concurrent agents, 1,000 total)
- Custom JS: `.claude/workflows/`
Guard: always fall back to Agent Teams or Task tool if workflows are unavailable.

**Worktree isolation:** For parallel file mutations across agents, use `isolation: "worktree"` on the Agent tool. Each agent gets a clean working copy; unchanged worktrees are auto-removed.

**Non-interactive (`claude -p`) mode:** Add `--dangerously-skip-permissions` for file writes — no user is present to approve tool calls.

Full dispatch contract: `skills/bridge-claude/SKILL.md`

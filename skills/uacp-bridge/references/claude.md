# Bridge: Claude (Anthropic) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/), debate-protocol (Claude-only Layer-2 supersession of the Post-Analysis Protocol).*

---

## Bridge Identity

```yaml
bridge: claude
model_family: anthropic/claude
availability: conditional   # Depends on executor — not always available
connection_preference:
  1: native-dispatch  # Executor is Claude Code — Task tool / Agent Teams / Workflows
  2: cli              # Any other executor — invoke `claude -p` CLI
  3: api              # Last resort — Anthropic HTTP API via ANTHROPIC_API_KEY
  4: skip             # None available — return SKIPPED (non-blocking)
```

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.claude]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.claude]` | float | `1.0` | Multiplier applied to the uacp-bridge base timeout estimate. |
| `workflows_enabled` | `[bridges.claude]` | boolean | `true` | Enable dynamic workflow dispatch (`/workflows`, `/deep-research`, `ultracode`). |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- `agent_teams_env` — hardcoded as `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`

---

## Tier Resolution

Claude bridge resolves the model alias and reasoning level from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this file does not hardcode it.

The general tier resolution protocol is defined in [uacp-bridge/SKILL.md](../SKILL.md). Claude-specific steps:

1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.claude.{tier}]` → get `alias` + `reasoning`
3. Look up `[models.providers.anthropic.models.{alias}]` → `concrete_id` → get resolved model ID
4. Apply reasoning level to `--effort`

The alias is stable; the `concrete_id` is updated in the registry when Anthropic releases new models. No bridge reference changes required.

**Effort mapping (Claude-specific — maps reasoning level to `--effort` flag value):**
- `quick` / `medium` → `--effort medium`
- `high` → `--effort high`
- `xhigh` → `--effort max` (Claude Code's maximum reasoning effort; note the flag value is `max`, not `xhigh`)

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per uacp-bridge rules (see [uacp-bridge/SKILL.md](../SKILL.md)).

---

## Step 1: Pre-Flight — Connection Detection

### Check A: Task Tool Available?

If the executor is Claude Code (or any agent with native Task tool access), this is the preferred path. No external process needed.

If Task tool available → **use native-dispatch path** (Steps 3A–3C).

---

### Check B: Claude Code CLI Installed?

```bash
which claude
```

If found → **use CLI path** (Step 3D). Any external executor (OpenCode, Codex, Gemini, custom agents) can invoke `claude -p` to get Claude's analysis without API keys.

---

### Check C: Anthropic API Accessible?

```bash
echo ${ANTHROPIC_API_KEY:+found}
```

If `ANTHROPIC_API_KEY` is set → **use API path** (Step 3E).

---

### Neither available → SKIPPED

```json
{
  "bridge": "claude",
  "status": "SKIPPED",
  "skip_reason": "No Anthropic access — Task tool unavailable, claude CLI not found, ANTHROPIC_API_KEY not set",
  "outputs": []
}
```

Claude bridge is non-blocking when unavailable. SKIPPED is a valid outcome.

---

## Step 2: Select Dispatch Mode

Claude bridge has three native-dispatch modes. Select based on task complexity, tier, and environment:

```yaml
dispatch_mode:
  workflows:
    condition: "tier >= 3 OR mode in [research, audit] OR task_description contains 'ultracode'"
    description: "Dynamic JavaScript workflows — orchestrate subagents at scale via Claude Code /workflows"
    preferred: true
    capabilities:
      - "Up to 16 concurrent agents (fewer on limited CPU)"
      - "Up to 1,000 agents total per run"
      - "JavaScript orchestration scripts in .claude/workflows/"
    caveat: "Only available when executing inside Claude Code with workflow support enabled"

  agent_teams:
    condition: "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 AND (domains >= 3 OR intensity = thorough) AND tier >= 2"
    description: "Teammates share a task list and communicate directly — best for complex multi-domain work"
    preferred: false
    caveat: "Env var is necessary but not sufficient — TeamCreate may still fail if this bridge
             is executing as a nested sub-agent (Task → Task). Always guard with a fallback."

  task_tool:
    condition: "Default — always available as fallback"
    description: "Sub-agents report results to parent — best for focused, independent tasks"
    preferred: false
```

**Dispatch mode selection priority:**

1. **Workflows** — highest capability, use for tier ≥3, research, audit, or when `ultracode` is requested
2. **Agent Teams** — use for complex multi-domain work (3+ domains, thorough intensity, tier ≥2)
3. **Task Tool** — fallback for all other cases

**Workflows vs Agent Teams vs Task Tool:**

| | Task Tool | Agent Teams | Workflows |
|---|-----------|------------|-----------|
| Communication | Sub-agents report to parent only | Teammates message each other directly | JavaScript orchestrator dispatches and coordinates |
| Coordination | Parent manages all | Shared task list, self-coordinating | Script-driven, can branch/loop/condition |
| Concurrency | Sequential or limited parallel | Parallel (team size) | Up to 16 concurrent, 1,000 total |
| Best for | Quick focused tasks | Multi-domain debate, complex analysis | Large-scale research, audit, synthesis |
| Availability | Always | Requires env var + top-level context | Requires Claude Code + workflow scripts |

---

## Step 3A: Execute via Workflows (preferred for high-tier tasks)

When `workflows_enabled = true` in `config/uacp.toml` and the task warrants it (tier ≥3, research mode, or `ultracode` requested), use Claude Code's dynamic workflow system.

### Workflow overview

Claude Code workflows are JavaScript scripts that orchestrate subagents at scale. They are saved to `.claude/workflows/` (project-scoped) or `~/.claude/workflows/` (personal).

**Key commands:**
- `/workflows` — list available workflows and recent runs
- `/deep-research` — bundled research workflow (deep, multi-step research with subagents)
- Type `ultracode` or `/effort ultracode` — triggers automatic workflow orchestration for coding tasks

**Capabilities:**
- Up to 16 concurrent agents (fewer on machines with limited CPU)
- Up to 1,000 agents total per workflow run
- Dynamic branching, looping, and conditional logic
- Access to all Claude Code tools (Read, Edit, Bash, etc.) within subagents

### Built-in workflows

| Workflow | Trigger | Use case |
|----------|---------|----------|
| `/deep-research` | Command | Deep multi-step research with recursive subagent dispatch |
| `ultracode` | Keyword or `/effort ultracode` | Automatic workflow orchestration for large-scale coding tasks |
| Custom JS | `/workflows` → select | Project-specific orchestration (e.g., batch refactor, multi-file audit) |

### Execution path

**For `/deep-research` (built-in):**
```
1. Verify workflow is available: claude -p "list workflows" or check /workflows
2. Invoke: claude -p "/deep-research {task_description}" \
     --model {resolved_model} --effort {resolved_effort}
3. Capture output (structured JSON if available, else markdown)
4. Parse findings into uacp-bridge output format
```

**For `ultracode` (keyword-triggered):**
```
1. Include "ultracode" in the prompt or use `/effort ultracode`
2. Claude Code automatically selects and runs the appropriate workflow
3. Example: claude -p "ultracode: refactor the authentication module to use OAuth2" \
     --model {resolved_model} --effort max
```

**For custom JavaScript workflows:**
```javascript
// .claude/workflows/uacp-council.js
// Example: dispatch domain experts in parallel, then synthesize

const { $, sleep } = require("@anthropic-ai/claude-code");

async function main() {
  const domains = $.input.domains;
  const tasks = domains.map(domain => ({
    name: `${domain}-expert`,
    prompt: `You are a ${domain} expert. Analyze: ${$.input.task_description}`,
    model: $.input.model,
    effort: $.input.effort
  }));

  // Spawn up to 16 concurrent agents
  const results = await Promise.all(tasks.map(t => $.agent(t)));

  // Synthesis agent
  const synthesis = await $.agent({
    name: "synthesis",
    prompt: `Synthesize these findings: ${JSON.stringify(results)}`,
    model: $.input.model
  });

  return synthesis;
}

module.exports = { main };
```

Invoke custom workflow:
```bash
claude -p "run workflow uacp-council" \
  --model {resolved_model} \
  --effort {resolved_effort} \
  --input '{"domains": [...], "task_description": "..."}'
```

### Workflow fallback (degrade-at-depth-2 guard)

If workflows are not available (older Claude Code version, not in Claude Code context, workflow scripts missing, or depth ≥2 where Workflows degrade to single-agent mode) → fall back to Step 3B (Agent Teams) or Step 3C (Task Tool).

---

## Step 3B: Execute via Agent Teams (complex multi-domain tasks)

When `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set and task complexity warrants it (3+ domains or thorough intensity), attempt Agent Teams. Teammates share a task list and can message each other directly — enabling real-time debate between domain experts.

### Failure guard — TeamCreate-FIRST, fail-closed

Before executing the full flow, attempt `TeamCreate`. If it fails for any reason (not available in this execution context, naming collision, experimental feature restricted at current depth) → **immediately fall back to Step 3C**. Do not retry Agent Teams.

```
0. ATTEMPT TeamCreate → "bridge-claude-{session_id}"
   IF TeamCreate fails → go to Step 3C (Task Tool fallback)

1. TeamCreate succeeded → continue
2. Spawn teammates:
   - One per domain from bridge_input.domains
   - Devil's Advocate (always)
   - Integration Checker (always)
3. Create tasks in shared task list — one per teammate
4. Teammates self-coordinate: domain experts complete their analysis,
   Devil's Advocate challenges findings via direct messages,
   Integration Checker surfaces cross-component issues
5. Wait for all tasks complete
6. Synthesize via TaskList
7. TeamDelete → clean up
   IF any step 2–6 fails → call TeamDelete before returning SKIPPED
```

Teammates communicate findings and challenges directly without routing through the parent. This supersedes the uacp-bridge Post-Analysis Protocol for Claude — debate-protocol provides the full Layer-2 protocol instead.

### Teammate prompts

**Domain expert:**
```
You are a {expert_role}. Your task: {task_description}
Scope: {scope} | Context: {context_summary} | Intensity: {intensity} | Tier: {tier}
Focus: {focus_areas from the domain registry}
Return your output as the JSON structure defined in uacp-bridge/SKILL.md Agent Prompt Template.
```

**Devil's Advocate (EXTENDED — richer than uacp-bridge generic Challenger):**
```
You are a Devil's Advocate for this analysis session.
Scope: {scope} | Context: {context_summary} | Intensity: {intensity} | Tier: {tier}

Your obligations (read debate-protocol/experts/devils-advocate.md for full protocol):
- MUST challenge every CRITICAL and HIGH finding not originated by you, via direct teammate messages
- SHOULD challenge MEDIUM findings when you detect a pattern across multiple findings
- Cross-domain synthesis: actively look for findings whose combination implies a new, higher-severity issue not caught by any single domain expert
- Pre-mortem focus: for each component in scope, ask "what would cause this to fail in production?"

Challenge quality standard: a valid challenge must either (a) identify a missing assumption, (b) propose an alternative explanation that lowers severity, or (c) surface a scenario where the finding does not apply.

Message domain expert teammates directly to challenge their findings. Do not wait for them to send to you first.

Return outputs JSON with domain: "cross-domain". Include both challenge outcomes (findings you successfully challenged/withdrew) and new findings you discovered.
```

**Integration Checker (EXTENDED — richer than uacp-bridge generic Integration Checker):**
```
You are an Integration Checker for this analysis session.
Scope: {scope} | Context: {context_summary} | Intensity: {intensity} | Tier: {tier}

Focus areas (read debate-protocol/experts/integration-checker.md for full protocol):
- Interface mismatches: where does component A assume something about component B that isn't guaranteed?
- Undocumented contracts: implicit dependencies that work by accident, not by design
- Error propagation gaps: errors that one component produces but callers don't handle
- Timing and ordering dependencies: race conditions, initialization ordering, cascading failures
- Cross-cutting assumptions: things that must be true globally but are only enforced locally

For each finding from domain experts: does it have cross-component implications beyond its stated scope?
If yes, surface those as integration findings even if the original finding is withdrawn.

Return outputs JSON with domain: "integration".
```

---

## Step 3C: Execute via Task Tool (fallback)

When Agent Teams is not available, spawn parallel Task sub-agents — one per domain + Devil's Advocate + Integration Checker. Sub-agents report results to parent only (no direct inter-agent communication). Build prompts using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md).

```
Task 1: {domain_1} expert — focus: {focus_areas}, scope: {scope}
Task 2: {domain_2} expert — focus: {focus_areas}, scope: {scope}
...
Task N:   Devil's Advocate — challenge assumptions, find failure modes (domain: "cross-domain")
Task N+1: Integration Checker — cross-component impacts, implicit contracts (domain: "integration")
```

All tasks run in parallel. After all complete, run the uacp-bridge Post-Analysis Protocol (see [uacp-bridge/SKILL.md](../SKILL.md)). For subsequent rounds, spawn new Task sub-agents with the context packet embedded in their prompts — the parent agent holds all state between rounds and manages the orchestrator synthesis step.

---

## Step 3D: Execute via CLI (external executors)

When any non-Claude-Code executor can call the `claude` CLI:

**Resolve tier first** (see Tier Resolution above and [uacp-bridge/SKILL.md](../SKILL.md)):
```bash
# Read tier from bridge_input or derive from task_type + intensity
# Look up model and reasoning from config/uacp.toml
# Resolved values: RESOLVED_MODEL, RESOLVED_EFFORT
```

**Read-only analysis (research, review, audit) — `capability_profile: inspect`:**
```bash
# run_to = OS-portable timeout helper from uacp-bridge/SKILL.md. Run with cwd at the provisioned
# review sandbox (Review Containment). `--allowedTools` (read-only) = read_only_enforcement: tool-mode.
run_to {final_timeout} claude -p "{constructed_prompt}" \
  --model {RESOLVED_MODEL} \
  --effort {RESOLVED_EFFORT} \
  --output-format json \
  --allowedTools "Read,Grep,Glob,Bash(ls *)"
```

**Implementation tasks (writes files, runs git, generates artifacts) — `capability_profile: modify`:**
```bash
timeout {final_timeout} claude -p "{constructed_prompt}" \
  --model {RESOLVED_MODEL} \
  --effort {RESOLVED_EFFORT} \
  --dangerously-skip-permissions \
  --output-format json
```

**Workflow-triggered tasks (tier ≥3 or ultracode requested):**
```bash
# Trigger built-in deep-research workflow
timeout {final_timeout} claude -p "/deep-research {task_description}" \
  --model {RESOLVED_MODEL} \
  --effort {RESOLVED_EFFORT} \
  --output-format json

# Or trigger ultracode workflow
timeout {final_timeout} claude -p "ultracode: {task_description}" \
  --model {RESOLVED_MODEL} \
  --effort max \
  --dangerously-skip-permissions \
  --output-format json
```

`--dangerously-skip-permissions` is required for implementation tasks — without it, Write and Bash write operations are blocked in non-interactive `-p` mode because there is no user present to approve them.

**Last verified:** 2026-06-07

**Key flags:**

| Flag | Purpose |
|------|---------|
| `-p "prompt"` | Prompt string — non-interactive mode |
| `--model` | Model to use (resolved from tier mapping) |
| `--effort` | Reasoning effort: medium, high, max |
| `--dangerously-skip-permissions` | Required for file writes in `-p` mode (no user to approve) |
| `--output-format json` | Structured JSON output for parsing |
| `--output-format stream-json` | Streaming JSON for real-time processing |
| `--allowedTools` | Restrict what Claude can do (read-only tasks only) |
| `--continue` | Resume the most recent session |

For read-only analysis (`capability_profile: inspect`), scope tools to `Read,Grep,Glob,Bash(ls *)`. For implementation tasks (`capability_profile: modify`), use `--dangerously-skip-permissions` with no `--allowedTools` restriction.

---

## Step 3E: Execute via Anthropic API (last resort)

```bash
# Discover latest model at runtime — never hardcode the model ID
CLAUDE_MODEL=$(curl -s -H "x-api-key: $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/models | python3 -c \
  "import sys,json; models=json.load(sys.stdin)['data']; print(models[0]['id'])")

curl -s -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$CLAUDE_MODEL\",
    \"max_tokens\": 8096,
    \"messages\": [{\"role\": \"user\", \"content\": \"{constructed_prompt}\"}]
  }"
```

Single API call covers all domains in one prompt. Less parallelism than native-dispatch paths.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "claude",
  "model_family": "anthropic/claude",
  "connection_used": "native-dispatch | cli | api",
  "dispatch_mode": "workflows | agent-teams | task-tool",
  "tier": 2,
  "resolved_model": "<resolved from registry>",
  "resolved_reasoning": "high",
  "agents_spawned": 4,
  "workflow_used": null
}
```

Output ID prefix: `C` (e.g., `C001`, `C002`).

---

## Notes

- **Not always available** — check Task tool access or `ANTHROPIC_API_KEY` before using
- **SKIPPED is non-blocking** — if unavailable, other bridges continue
- **native-dispatch is preferred** — richer parallel dispatch when running in Claude Code
- **Workflows are the highest-capability mode** — use for tier ≥3, research, audit, or when scale matters (16 concurrent agents, 1,000 total)
- **Agent Teams supersedes Post-Analysis Protocol** — when available, debate-protocol Layer-2 runs instead of the uacp-bridge consolidation pass
- **Agent Teams guard is mandatory** — `TeamCreate` can fail even when the env var is set (nested sub-agent context, depth limit, naming collision); always fall back to Task Tool on failure; no retries
- **Workflows guard is mandatory** — workflows require Claude Code context and may not be available in nested execution; always fall back to Agent Teams or Task Tool
- **Sub-agent recursion depth** — Task → Task works reliably; Agent Teams inside a Task agent (Task → TeamCreate) is experimental and context-dependent; Workflows at depth 2+ may degrade to single-agent mode
- **TeamDelete on failure** — if any step between TeamCreate and synthesis fails, call TeamDelete before returning SKIPPED to avoid orphaned teams
- **API path works from any executor** — fallback for non-Claude orchestrators
- **Task type drives framing** — the same bridge handles review, planning, research, etc. (see uacp-bridge/SKILL.md for capability_profile derivation)
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when Anthropic releases new models

---

## CLI Reference

Complete reference for `claude` CLI non-interactive usage. Used when this bridge runs via an external executor (OpenCode, Codex, Gemini, or any agent that can shell out to `claude`).

### Non-Interactive Mode

```bash
claude -p "prompt"
```

The `-p` flag runs Claude non-interactively without opening an interactive session.

### Key Flags

| Flag | Values | Purpose |
|------|--------|---------|
| `-p`, `--print` | string | Prompt string — enables non-interactive mode |
| `--output-format` | `text`, `json`, `stream-json` | Output format |
| `--allowedTools` | comma-separated tool names | Restrict available tools |
| `--continue` | — | Resume most recent session |
| `--resume` | session ID | Resume a specific session |
| `--model` | model ID | Override model |
| `--verbose` | — | Debug output (remove in production) |
| `--dangerously-skip-permissions` | — | Skip all permission checks (use in sandboxed env only) |

### Output Formats

| Format | Description | Use Case |
|--------|-------------|---------|
| `text` | Plain text (default) | Human-readable output |
| `json` | Structured JSON result | Programmatic parsing |
| `stream-json` | Streaming JSON events | Real-time processing, long tasks |

### Tool Scoping for Read-Only Analysis

```bash
claude -p "{prompt}" \
  --output-format json \
  --allowedTools "Read,Grep,Glob,Bash(ls *),Bash(cat *)"
```

Restricts Claude to reading files only — appropriate for review, analysis, planning tasks where no writes should occur.

### Piping Input

```bash
# Pipe file contents as context
cat error.log | claude -p "Analyze this log for errors"

# Pipe from another command
git diff | claude -p "Summarize what changed"
```

### Agent Teams (Claude Code native, not CLI-invocable)

Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in environment and are only available when Claude Code is the executor. They cannot be triggered via `claude -p`.

Enable in `settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### Sub-Agent Definitions (`.claude/agents/`)

Define specialized sub-agents in `.claude/agents/`:

```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a security engineer. Review for injection vulnerabilities,
auth flaws, secrets in code, and insecure data handling.
```

Invoke: `"Use a security-reviewer subagent to analyze src/auth/"`

### Anthropic API Fallback

When `claude` CLI is not available, fall back to the Anthropic API directly (see Step 3E above for the full invocation pattern with runtime model discovery).

### Installation

```bash
# Via npm
npm install -g @anthropic-ai/claude-code

# Check version
claude --version
```

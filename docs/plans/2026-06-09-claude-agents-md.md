# CLAUDE.md and AGENTS.md Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two runtime instruction files at the UACP root so Claude Code and Codex have governance orientation before doing any work in this repo.

**Architecture:** `AGENTS.md` is the canonical file holding all governance rules. `CLAUDE.md` is a thin adapter: `@AGENTS.md` import at the top followed by Claude Code-specific dispatch notes. Single source of truth — update `AGENTS.md` only.

**Tech Stack:** Markdown only. No code changes. Additive — no existing files modified.

---

### Task 1: Create AGENTS.md

**Files:**
- Create: `AGENTS.md` (repo root)

---

**Step 1: Create the file with this exact content**

```markdown
# UACP — Universal Agent Control Plane

Runtime-neutral governance framework for AI agent work. Six-phase lifecycle: **TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE**.

---

## Authority Chain

When layers conflict, earlier layers win. An explicit entry in `docs/decisions/decision-log.md` is the only mechanism to override this order.

| Priority | Layer | Role |
|---|---|---|
| 1 | `docs/INDEX.md` | Document registry and canonical agent read order |
| 2 | `docs/` | Intent, principles, lifecycle, policy |
| 3 | `config/` | Machine-readable rules derived from docs |
| 4 | `state/` | Current lifecycle position and run pointers |
| 5 | Skills and runtime behavior | Implement the documented rules |

**Start here as an agent:** `docs/INDEX.md`

---

## Lifecycle

| Phase | Responsibility |
|---|---|
| TRIAGE | Scope calibration, granularity scoring, governance routing |
| PROPOSE | Declare intent, authority, constraints, evidence obligations |
| PLAN | Produce a council-reviewed execution plan with PLAN_VALIDATION ledger entry |
| EXECUTE | Perform bounded work within Guardian policy using governed writers |
| VERIFY | Produce evidence that the plan was executed correctly |
| RESOLVE | Close the run, record lessons, release held state |

Every transition is validated by **Heartgate**. Direct phase-skipping is a blocker, not a warning.

---

## Key Invariants

These rules are non-negotiable. Violations are Heartgate blockers or Guardian blocks.

1. **TRIAGE-first** — All non-trivial work enters via TRIAGE. No phase-skipping.
2. **No main writes** — No active run writes directly to `main`/`master`. Use `worktree` or `branch` (see `docs/lifecycle/worktree-protocol.md`).
3. **Governed writers only** — No raw filesystem writes during a run. Use:
   - `uacp_doc_write` — canonical docs (`docs/`)
   - `uacp_config_write` — policy YAML (`config/`)
   - `uacp_state_write` — runtime state (`state/current.yaml`)
   - `uacp_gate_ledger_append` — gate ledger (`state/gate-ledger/`)
   - `uacp_run_registry_update` — run registry (`state/run-registry.yaml`)
   - `uacp_escalation_event` — escalations (`state/escalations/`)
4. **Council gate** — Any change to kernel code, policy YAML, or canonical docs requires council review before PLAN exits. Zero material findings unresolved.
5. **Evidence must be produced** — "Done" without a backing artifact and ledger entry is a Heartgate blocker. No self-attesting closures.

---

## Skill Map

| Phase | Skill | Purpose |
|---|---|---|
| TRIAGE | `uacp-triage` | Route the request, calibrate scope |
| PROPOSE | `uacp-propose` | Author the proposal artifact |
| PLAN | `uacp-plan` | Produce plan + scope + PLAN_VALIDATION ledger |
| EXECUTE | `uacp-execute` | Bounded work with PIV evidence |
| VERIFY | `uacp-verify` | Evidence synthesis, gate checklist |
| RESOLVE | `uacp-resolve` | Lessons, closure, state release |
| Guardian | `uacp-guardian` | Pre-tool-call policy enforcement |
| Council | `uacp-council` | Multi-agent deliberation (any phase) |

---

## Cognitive Planes

UACP enforces strict separation between five planes. Mixing planes causes category errors — do not use Agent Council as a state database, do not let worker runtimes silently mutate UACP phase state, do not use a Coordination Adapter to decide policy.

| Plane | Role |
|---|---|
| UACP | Governance cognition — authority, side effects, policy |
| Agent Council | Deliberative cognition — strategy, design, challenge, synthesis |
| Coordination Adapter | Coordination memory — durable task state (e.g., Kanban) |
| Agent Runtimes | Worker cognition — bounded execution (Claude Code, Codex, Gemini, Kimi, OpenCode) |
| Tool Adapters | Actuation and observation — web search, browser, scraping |
| Guardian + Heartgate | Boundary enforcement — tool calls and phase transitions |

---

## Codex Dispatch

**Native dispatch (preferred when executor is Codex with multi-agent enabled):**
```bash
echo ${CODEX_SESSION_ID:+found}
codex features list 2>/dev/null | grep -q "multi_agent" && echo "enabled"
```
If both true → use native multi-agent dispatch (one sub-agent per domain).

**MCP server (preferred for non-Codex executors):**
```
mcp__codex__codex       — start session (returns threadId)
mcp__codex__codex-reply — continue session
```
Auto-setup: write to `.mcp.json`:
```json
{"mcpServers": {"codex": {"command": "npx", "args": ["-y", "codex", "mcp-server"]}}}
```

**CLI fallback:**
```bash
timeout <n> codex exec "<prompt>" \
  --sandbox read-only \
  --ask-for-approval never \
  --json \
  --output-last-message /tmp/codex-out.json \
  --ephemeral \
  --skip-git-repo-check
```

Full dispatch contract: `skills/bridge-codex/SKILL.md`

---

## Further Reading

- Full authoring contract: `CONTRIBUTING.md`
- Canonical agent read order: `docs/INDEX.md`
- Proposal schema: `docs/reference/proposal-schema.md`
- Guardian + Heartgate: `docs/runtime/runtime-enforcement.md`
- Worktree isolation: `docs/lifecycle/worktree-protocol.md`
```

---

**Step 2: Verify**

Check the file was created:
```bash
ls -la AGENTS.md
wc -l AGENTS.md
```
Expected: file exists, ~90 lines.

Spot-check section headers are present:
```bash
grep "^## " AGENTS.md
```
Expected output:
```
## Authority Chain
## Lifecycle
## Key Invariants
## Skill Map
## Cognitive Planes
## Codex Dispatch
## Further Reading
```

---

**Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "feat: add AGENTS.md — canonical runtime instruction file for Codex"
```

---

### Task 2: Create CLAUDE.md

**Files:**
- Create: `CLAUDE.md` (repo root)

---

**Step 1: Create the file with this exact content**

```markdown
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
```

---

**Step 2: Verify**

Check the file:
```bash
ls -la CLAUDE.md
head -3 CLAUDE.md
```
Expected first line: `@AGENTS.md`

Verify the @import reference target exists:
```bash
test -f AGENTS.md && echo "import target exists"
```
Expected: `import target exists`

---

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md — thin Claude Code adapter over AGENTS.md"
```

---

### Task 3: Final verification

**Step 1: Confirm both files are tracked**

```bash
git log --oneline -3
```
Expected: two new commits above the design doc commit.

**Step 2: Confirm root-level instruction files are present**

```bash
ls AGENTS.md CLAUDE.md
```
Expected: both files listed with no errors.

**Step 3: Confirm CLAUDE.md imports AGENTS.md**

```bash
head -1 CLAUDE.md
```
Expected: `@AGENTS.md`

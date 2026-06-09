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
| 5 | `skills/` (esp. `skills/state/` for state mutation contracts) | Implement the documented rules |

> **Note:** `state/` is runtime-created — it does not exist in a fresh clone. An agent bootstrapping cold should treat a missing `state/` as "no active run" rather than an error.

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
   - `uacp_kanban_write` — coordination adapter state (`state/kanban.yaml`)
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
| Heartgate | `uacp-heartgate` | Phase-transition validation |

---

## Cognitive Planes

UACP enforces strict separation between six planes. Mixing planes causes category errors — do not use Agent Council as a state database, do not let worker runtimes silently mutate UACP phase state, do not use a Coordination Adapter to decide policy.

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
  --json \                                   # structured JSON output for parsing
  --output-last-message /tmp/codex-bridge-$(date +%s).json \
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

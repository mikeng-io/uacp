# Bridge: Hermes (Nous Research hermes-agent) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/).*

> **Host-can-also-be-a-bridge.** Hermes (Nous Research's `hermes-agent`) is UACP's **host runtime** — UACP's Guardian/Heartgate kernel ships as a hermes-agent *plugin* (`runtime-adapters/hermes/plugins/uacp_guardian/`). This file is the **bridge** for dispatching a review *to* hermes-agent as a reviewer runtime, exactly as `claude.md` dispatches to Claude even though Claude Code is also a host. The two roles are distinct: `runtime-adapters/hermes/` = UACP running *inside* Hermes; this file = UACP dispatching a council task *to* Hermes. Do not conflate them.

---

## Bridge Identity

```yaml
bridge: hermes
model_family: multi-provider   # hermes-agent is provider-agnostic (OpenRouter/Anthropic/OpenAI/Gemini/Kimi/Ollama/OpenCode-Go/local)
availability: conditional
connection_preference:
  1: native-dispatch  # Executor IS hermes-agent — delegate_task / Swarm (Kanban board)
  2: cli              # Any other executor — `hermes -z "<prompt>"` (one-shot, non-interactive)
  3: acp-server       # Editor/IDE integration — `hermes acp` stdio JSON-RPC
  4: skip             # None available — return SKIPPED (non-blocking)
```

Terminal failure state: **SKIPPED only** — no HALT path. If Hermes is unavailable or unauthenticated, return SKIPPED and continue. Never block the calling orchestrator.

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.hermes]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.hermes]` | float | `1.0` | Multiplier applied to the uacp-bridge base timeout estimate. |
| `model` | `[bridges.hermes]` | string | `""` (empty) | Optional model override passed to `-m`/`--model` (and `--provider`), e.g. `anthropic/claude-sonnet-4.6`. Empty = use hermes-agent's configured default (`hermes status` shows it). |
| `read_only_toolset` | `[bridges.hermes]` | string | `""` (empty) | Comma-separated `-t/--toolsets` value for `inspect` tasks (e.g. `web,file,vision`). NOTE: the built-in `file` toolset bundles read **and** write — toolset gating alone cannot give read-without-write, so this MUST be paired with `--worktree` (see Read-Only Enforcement). Empty = bridge composes a minimal read set + `--worktree`. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- `native_dispatch` capability — auto-detected (is the executor hermes-agent?)

### Multi-provider exception (like OpenCode)

hermes-agent is **provider-agnostic** (OpenRouter, native Anthropic/OpenAI/Gemini/Kimi/Ollama, OpenCode-Go, local). Like OpenCode, it is **intentionally absent from `config/uacp.toml` `[models]`** — there is no `[models.tier_mappings.hermes]`. Model selection is delegated to hermes-agent's own config (`hermes model` / `hermes setup`; inspect via `hermes status`), or overridden per-run via `[bridges.hermes].model`. UACP does not validate Hermes model identifiers. Because hermes is multi-provider, the `[bridges.hermes].allowed_models` authorization gate applies (see uacp-bridge/SKILL.md Model authorization).

---

## Tier Resolution

Because Hermes is the multi-provider exception, tier does not resolve to a UACP-registry model. Instead:

1. Accept `bridge_input.tier` (or derive from `task_type` + `intensity` per [uacp-bridge/SKILL.md](../SKILL.md)) — used for **timeout estimation** and to pick a stronger model when `[bridges.hermes].model` encodes a tier ladder.
2. If `[bridges.hermes].model` is set → pass it as `-m` (+ `--provider` if needed). Otherwise omit and let hermes use its configured default.
3. Record `resolved_model` as whatever was passed (or `"hermes:default"` when delegated).

There is **no per-invocation reasoning/effort flag**; reasoning depth is a property of the chosen model. Record `reasoning_applied_per_invocation: false`.

---

## Pre-Flight — Connection Detection

### Check A: Native Dispatch? (executor is hermes-agent)

If this bridge is executing *inside* a hermes-agent session, prefer its native sub-agent dispatch (`delegate_task`) over shelling out.

```bash
echo ${HERMES_ROOT:+found}${HERMES_SESSION_ID:+found}   # hermes-agent session markers
```

If running inside hermes-agent → **use native-dispatch** (delegate_task / Swarm). Otherwise → Check B.

### Check B: CLI Available?

```bash
which hermes && hermes --version    # e.g. "Hermes Agent v0.17.0"
```

If the `hermes` CLI is found → **use CLI path**. Else → Check C.

### Check C: ACP?

`hermes acp` exposes a stdio JSON-RPC agent (editor integration: VS Code, Zed, JetBrains). Usable as a programmatic channel but higher friction than `hermes -z` — only attempt if an ACP client harness is already available. Else → SKIPPED:

```json
{
  "bridge": "hermes",
  "status": "SKIPPED",
  "skip_reason": "hermes-agent not available (no in-session dispatch, no `hermes` CLI, no ACP harness)",
  "outputs": [],
  "verdict": null
}
```

### Check D: Auth

hermes-agent needs a configured provider. Probe:

```bash
hermes status      # shows Model, Provider, and which API keys are set
hermes doctor      # config + dependency + provider-credential health check
```

If no provider key resolves → SKIPPED (`skip_reason: "hermes-agent not configured: no provider key"`).

---

## Step: Native-Dispatch (preferred — executor is hermes-agent)

Use the `delegate_task` tool to spawn one read-only sub-agent per domain in `bridge_input.domains`, in parallel. Sub-agents inherit a restricted toolset and **cannot** recursively delegate, write memory, send messages, or run `code_execution` (the harness blocks `delegate_task`, `clarify`, `memory`, `send_message`, `code_execution`/`execute_code`, `cronjob` inside sub-agents).

```
delegate_task(
  role="orchestrator",
  parallel=true,
  timeout={final_timeout},
  tasks=[
    {"prompt": "{Agent Prompt Template for domain_1}", "toolsets": ["{read_only_toolset}"]},
    {"prompt": "{Agent Prompt Template for domain_2}", "toolsets": ["{read_only_toolset}"]},
    ...
  ]
)
```

This is the Layer-2 intra-bridge analysis. For the Post-Analysis Protocol, the orchestrating agent re-delegates Round N sub-agents with the context packet embedded. When a Kanban board is present (`HERMES_KANBAN_TASK`), the Swarm coordinates via the board.

---

## Step: Execute via CLI (external executors) — `hermes -z`

Build one prompt per domain using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md), and **append the JSON-output contract explicitly** (hermes emits assistant text on stdout, not findings-JSON — see caveat).

```bash
# run_to = the OS-portable timeout helper from uacp-bridge/SKILL.md (timeout|gtimeout|perl-alarm).
# `-z`/`--oneshot` = non-interactive one-shot; assistant text goes to stdout.
run_to {final_timeout} hermes -z "{constructed_prompt}" \
  --worktree \
  -t "{read_only_toolset}" \
  ${HERMES_BRIDGE_MODEL:+-m "$HERMES_BRIDGE_MODEL"}   # from [bridges.hermes].model, if set
```

- `-z "..."` is the prompt (one positional one-shot; pass as the arg).
- `--worktree`/`-w` runs hermes in an **isolated git worktree** — hermes's *built-in* Tier-2 containment (see Read-Only Enforcement). Prefer this; if the orchestrator already provisioned a sandbox, run with cwd there instead.
- `-t/--toolsets` is a comma-separated enabled set for this invocation (e.g. `web,file,vision`).
- `-m/--model` (+ `--provider`) overrides the configured default for this invocation.
- **No `--max-turns`/budget flag** on `hermes -z`; bound via the timeout. (Step limits live in config.)
- **Do NOT pass `--yolo`** for `inspect` — it bypasses dangerous-command approval.

> `run_agent.py` / `batch_runner.py` / `mini_swe_runner.py` exist in the repo as **internal/dev runners**, not the user CLI — do not target them from the bridge. The supported non-interactive entry is `hermes -z`.

### Read-Only Enforcement (`capability_profile: inspect`)

Follow the **Review Containment** ladder in [uacp-bridge/SKILL.md](../SKILL.md) (fail-closed; minimum tier from `[bridges.defaults].inspect_containment`, default `worktree`). hermes-agent has **no `--read-only` flag**, and its built-in `file` toolset bundles read **and** write — so toolset gating alone cannot guarantee read-only. The honest mechanism:

- **Tier 2 (primary for hermes):** isolation via `--worktree` (hermes's own disposable git worktree) **or** the orchestrator-provided ephemeral worktree (run with cwd there). Any write lands in throwaway space → `read_only_enforcement: worktree`. *Same caveat as all worktrees: it contains accidental writes, it is not a hard boundary (shared `.git`); hard read-only against an untrusted process needs Tier 3.*
- **Toolset restriction (defense-in-depth):** pass `-t` with only read-oriented toolsets and **drop** `terminal`, `code_execution`, `delegation`, `cronjob`, `computer_use`, `image_gen`. Verify the active set with `hermes tools list`. This is not a hard guarantee (`file` still writes), so it does not by itself qualify as `tool-mode`.

If no worktree isolation is available → return **SKIPPED** (`skip_reason: "cannot guarantee read-only containment"`). Never resolve `inspect` to an uncontained `hermes -z`.

---

## ⚠ Structured-output caveat + evidence

`hermes -z` returns the assistant's final text on **stdout** — there is **no findings-JSON and no trajectory file** from the one-shot path (trajectory artifacts are an internal-runner concept, not produced by `hermes -z`).

**To extract findings:** the constructed prompt MUST end with "Return ONLY a fenced ```json block matching {…Agent Prompt Template JSON…}, no prose before or after." Capture stdout, locate the last fenced ```json block, parse it. On failure → lenient `{...}` extraction; else SKIPPED.

**Evidence body (ties to the bridge evidence model):** for richer evidence than the final answer, hermes persists **sessions** (`hermes sessions`) and can run under `acp` (structured JSON-RPC events). These are the Tier-3 native-transcript source if/when the evidence-capture ladder is built (see `design/bridge-containment/`). The one-shot stdout path captures conclusions only.

---

## Post-Analysis Protocol

- **Native-dispatch:** re-`delegate_task` Round N sub-agents with the context packet (parallel). Swarm/Kanban coordinates when present.
- **CLI:** hermes persists sessions, so Round N may `hermes --continue` / `--resume <session>` to carry prior context, **or** embed the full previous-round outputs + context packet in a fresh `hermes -z` (honour the 32 000-char stateless limit; summarize per the shared rules; never silently truncate). Record `prompt_size_chars_r{n}`.

Round counts: `quick` 0 / `standard` 1 / `thorough` ≤3 after initial analysis.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields:

```json
{
  "bridge": "hermes",
  "model_family": "multi-provider",
  "connection_used": "native-dispatch | cli | acp-server",
  "read_only_enforcement": "worktree",
  "model_authorized": true,
  "tier": 2,
  "resolved_model": "<provider/model or hermes:default>",
  "reasoning_applied_per_invocation": false
}
```

Output ID prefix: `H` (e.g., `H001`, `H002`).

---

## Notes

- **Host-can-also-be-a-bridge** — Hermes is UACP's host runtime *and* a dispatch target; this file is the dispatch target only. Kernel-as-plugin lives in `runtime-adapters/hermes/`.
- **Multi-provider exception** — absent from `config/uacp.toml` `[models]`; model resolved from hermes config or `[bridges.hermes].model`; subject to the `allowed_models` authorization gate.
- **SKIPPED-only** — no HALT path; unavailability/auth failure is non-blocking.
- **Non-interactive entry is `hermes -z`** — NOT `run_agent.py` (internal). `delegate_task`/Swarm when executor is hermes-agent; `acp` for editor integration.
- **Read-only is worktree isolation, not a flag** — `file` toolset bundles write, so `--worktree` (built-in) or the provided sandbox is the mechanism; `-t` restriction is defense-in-depth; SKIP if no isolation is possible.
- **No structured findings output** — parse the last fenced ```json block from stdout; fail closed to SKIPPED. No trajectory file from `hermes -z`.
- **No budget/turn flag on `-z`** — bound with the timeout.
- **Not a standalone binary** — Python harness; install via `hermes-agent.nousresearch.com/install.sh` (→ `~/.hermes`, CLI at `~/.local/bin/hermes`), pip/uv, or Docker.

---

## CLI Reference

*Last verified: 2026-06-25 against a live install — **Hermes Agent v0.17.0** (upstream d6269da7); `hermes -z` one-shot dogfooded end-to-end.*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| One-shot | `hermes -z "<prompt>" -t <toolsets> [-m <model>] [--worktree]` | Scripted non-interactive review — **primary CLI path** |
| Interactive TUI | `hermes` / `hermes chat` | Terminal UI — do NOT use programmatically |
| ACP server | `hermes acp` | stdio JSON-RPC for editor/IDE integration |
| Health / status | `hermes doctor` · `hermes status` | Config, provider, credential checks |
| Toolset config | `hermes tools list` · `hermes tools disable/enable <toolset>` | Inspect/restrict the active toolset |
| Model config | `hermes model` · `hermes setup` | Select default model/provider |

### `hermes` — Key global flags (apply to `-z`/`--oneshot`)

| Flag | Type | Purpose |
|------|------|---------|
| `-z`, `--oneshot` | string | One-shot prompt, non-interactive; assistant text → stdout |
| `-m`, `--model` | string | Model override for this invocation (e.g. `anthropic/claude-sonnet-4.6`) |
| `--provider` | string | Provider override (e.g. `openrouter`, `anthropic`, `opencode`) |
| `-t`, `--toolsets` | csv | Enabled toolsets for this invocation (e.g. `web,file,vision`) |
| `--worktree`, `-w` | flag | Run in an isolated git worktree (containment) |
| `--resume` / `--continue` | session | Resume a prior session (context continuity) |
| `--yolo` | flag | Bypass dangerous-command approval — **never for `inspect`** |
| `--ignore-rules` | flag | Skip auto-injection of AGENTS.md/SOUL.md/rules |
| `--safe-mode` | flag | Disable all customizations (troubleshooting) |
| `--cli` | flag | Force CLI (non-TUI) rendering |

Built-in toolsets (from `hermes tools list`): `web`, `browser`, `terminal`, `file` (read+write), `code_execution`, `vision`, `image_gen`, `tts`, `skills`, `todo`, `memory`, `session_search`, `clarify`, `delegation`, `cronjob`, `computer_use` (+ optional: `video`, `video_gen`, `x_search`, `moa`, `context_engine`, …). For `inspect`, enable only read-oriented ones and pair with `--worktree`.

### Auth & providers

- `hermes status` shows the active **Model** + **Provider** + which keys are set. Providers include OpenRouter (`OPENROUTER_API_KEY`), native Anthropic/OpenAI/Gemini/Kimi, Ollama, and **OpenCode Go**. Configure via `hermes setup` / `hermes model` / `hermes auth`.

### Sub-agent / delegation

`delegate_task(tasks=[{prompt, toolsets}], role="orchestrator"|"leaf", parallel=bool, timeout=int)` — agent-invoked (the `delegation` toolset), not a CLI flag. Sub-agents block `delegate_task`/`clarify`/`memory`/`send_message`/`code_execution`/`cronjob`. Kanban/Swarm coordination gated via `HERMES_KANBAN_TASK`.

### Install / Version / Health

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash   # → ~/.hermes ; CLI at ~/.local/bin/hermes
# or: pip install -e .  /  uv  /  Docker
hermes --version    # Hermes Agent vX.Y.Z (date) · upstream <sha>
hermes doctor       # config + dependency + provider-credential check
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Parse the last fenced ```json block from stdout |
| `124` | Timeout (from the `run_to` wrapper) | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other non-zero | CLI error | Capture stderr; return SKIPPED with detail |
| Valid exit, no JSON block | Parse failure | Lenient `{...}` extraction; else SKIPPED |

# Bridge: Hermes (Nous Research hermes-agent) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/).*

> **Host-can-also-be-a-bridge.** Hermes (Nous Research's `hermes-agent`) is UACP's **host runtime** — UACP's Guardian/Heartgate kernel ships as a hermes-agent *plugin* (`runtime-adapters/hermes/plugins/uacp_guardian/`). This file is the **bridge** for dispatching a review *to* hermes-agent as a reviewer runtime, exactly as `claude.md` dispatches to Claude even though Claude Code is also a host. The two roles are distinct: `runtime-adapters/hermes/` = UACP running *inside* Hermes; this file = UACP dispatching a council task *to* Hermes. Do not conflate them.

---

## Bridge Identity

```yaml
bridge: hermes
model_family: multi-provider   # hermes-agent is provider-agnostic (OpenRouter default; Anthropic/OpenAI/Gemini/Kimi/Ollama/local)
availability: conditional
connection_preference:
  1: native-dispatch  # Executor IS hermes-agent — delegate_task / Swarm (Kanban board)
  2: cli              # Any other executor — `python run_agent.py --query ...` (or the `hermes` CLI)
  3: acp-server       # Editor/IDE integration — `hermes acp` stdio JSON-RPC (schema value: acp-server)
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
| `model` | `[bridges.hermes]` | string | `""` (empty) | Optional model override in hermes-agent's `provider/model` (OpenRouter) form, e.g. `anthropic/claude-sonnet-4.6`. Empty = let hermes-agent resolve its own `model.default`. |
| `read_only_toolset` | `[bridges.hermes]` | string | `""` (empty) | The `--enabled_toolsets` profile for `inspect` tasks. MUST be a read-only profile that **includes file reads** — the built-in `safe` set excludes file reads and is unusable for review. Empty = bridge composes/verifies an inspect profile (never defaults to `safe`). See Read-Only Enforcement. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- `native_dispatch` capability — auto-detected (is the executor hermes-agent?)

### Multi-provider exception (like OpenCode)

hermes-agent is **provider-agnostic** (defaults to OpenRouter's 200+ models; also speaks native Anthropic/OpenAI/Gemini/Kimi/Ollama/local). Like OpenCode, it is **intentionally absent from `config/uacp.toml` `[models]`** — there is no `[models.tier_mappings.hermes]`. Model selection is delegated to hermes-agent's own config (`~/.hermes/.env` + `cli-config.yaml` `model.default`), or overridden per-run via `[bridges.hermes].model`. UACP does not validate Hermes model identifiers.

---

## Tier Resolution

Because Hermes is the multi-provider exception, tier does not resolve to a UACP-registry model. Instead:

1. Accept `bridge_input.tier` (or derive from `task_type` + `intensity` per [uacp-bridge/SKILL.md](../SKILL.md)) — used only for **timeout estimation** and to pick a stronger model when `[bridges.hermes].model` encodes a tier ladder.
2. If `[bridges.hermes].model` is set → pass it as `--model`. Otherwise omit `--model` and let hermes-agent use `model.default`.
3. Record `resolved_model` as whatever was passed (or `"hermes:model.default"` when delegated).

There is **no per-invocation reasoning/effort flag**; reasoning depth is a property of the chosen model. Record `reasoning_applied_per_invocation: false`.

---

## Pre-Flight — Connection Detection

### Check A: Native Dispatch? (executor is hermes-agent)

If this bridge is executing *inside* a hermes-agent session, prefer its native sub-agent dispatch (`delegate_task`) over shelling out.

```bash
# Heuristic: hermes-agent sets its home / session markers
echo ${HERMES_ROOT:+found}${HERMES_SESSION_ID:+found}
```

If running inside hermes-agent → **use native-dispatch** (delegate_task / Swarm). Otherwise → Check B.

### Check B: CLI Available?

```bash
which hermes || (python -c "import run_agent" 2>/dev/null && echo "run_agent importable")
```

If the `hermes` CLI or an importable `run_agent.py` is found → **use CLI path**. Else → Check C.

### Check C: ACP?

`hermes acp` exposes a stdio JSON-RPC agent (editor integration). Usable as a programmatic channel but higher friction than the CLI — only attempt if an ACP client harness is already available. Else → SKIPPED:

```json
{
  "bridge": "hermes",
  "status": "SKIPPED",
  "skip_reason": "hermes-agent not available (no in-session dispatch, no `hermes`/run_agent CLI, no ACP harness)",
  "outputs": [],
  "verdict": null
}
```

### Check D: Auth

hermes-agent needs a provider key in its environment (`OPENROUTER_API_KEY` by default, or native `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `KIMI_API_KEY` / `OLLAMA_BASE_URL`). Probe:

```bash
hermes doctor 2>/dev/null     # checks config + provider credentials
```

If no provider key resolves → SKIPPED (`skip_reason: "hermes-agent not configured: no provider key"`).

---

## Step: Native-Dispatch (preferred — executor is hermes-agent)

Use the `delegate_task` tool to spawn one read-only sub-agent per domain in `bridge_input.domains`, in parallel. Sub-agents inherit a restricted toolset and **cannot** recursively delegate, write memory, send messages, or run `execute_code` (the harness blocks `delegate_task`, `clarify`, `memory`, `send_message`, `execute_code`, `cronjob` inside sub-agents).

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

## Step: Execute via CLI (external executors)

Build one prompt per domain using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md), and **append the JSON-output contract explicitly** (hermes-agent emits a trajectory, not findings-JSON — see caveat).

```bash
# run_to = the OS-portable timeout helper from uacp-bridge/SKILL.md (timeout|gtimeout|perl-alarm)
run_to {final_timeout} python run_agent.py \
  --query="{constructed_prompt}" \
  --enabled_toolsets="{read_only_toolset}" \
  --max_turns={bounded_turns} \
  --save_trajectories \
  ${HERMES_BRIDGE_MODEL:+--model "$HERMES_BRIDGE_MODEL"}   # from [bridges.hermes].model, if set
```

- `--query` is the prompt (no stdin support — pass as the arg).
- `--enabled_toolsets` selects the read-only profile (see below).
- `--max_turns` bounds tool-call rounds (no USD budget flag).
- `--save_trajectories` writes the parseable artifact (see Output).
- `mini_swe_runner.py --task "..." --output_file <path>` is a lighter single-task alternative; `batch_runner.py --dataset_file <jsonl> --distribution <toolset> --num_workers N` parallelizes multiple prompts.

### Read-Only Enforcement (`capability_profile: inspect`)

Follow the **Review Containment** ladder in [uacp-bridge/SKILL.md](../SKILL.md) (fail-closed; minimum tier from `[bridges.defaults].inspect_containment`, default `worktree`). hermes-agent has **no `--read-only` flag** — read-only is **toolset gating** (soft, not OS-enforced), so its Tier-1 mode is verifiable only by inspecting the resolved tool list, and the worktree is the real floor:

- **Tier 1 (toolset):** compose an `inspect` profile that **includes read-only file/codegraph tools and excludes writers/terminal/delegate/execute_code** (the built-in `safe` set excludes file *reads* — unusable for review). Set it in `[bridges.hermes].read_only_toolset` and **verify** with `python run_agent.py --list_tools --enabled_toolsets "{profile}"` before trusting it. If verified → contributes `read_only_enforcement: tool-mode`.
- **Tier 2 (floor):** run inside the orchestrator-provided ephemeral worktree (`--dir`/cwd) so any stray write lands in throwaway space → declare `read_only_enforcement: worktree`.
- `image_gen` (in `safe`) writes ephemeral temp files only — benign.

If neither a verified read-only toolset **nor** an ephemeral worktree is available → return **SKIPPED** (`skip_reason: "cannot guarantee read-only containment"`). Never resolve `inspect` to a write-capable, uncontained invocation.

---

## ⚠ Structured-output caveat + the evidence trajectory

hermes-agent has **no findings-JSON output**. Every runner emits a **trajectory JSONL**:

- `run_agent.py --save_trajectories` → `trajectory_samples.jsonl` (or `failed_trajectories.jsonl`)
- `batch_runner.py` → `<run_name>/trajectories.jsonl`
- `mini_swe_runner.py --output_file <path>` → one JSON object

Each entry: `{ "conversations": [{"from": "system|human|gpt|tool", "value": "..."}], "completed": bool, "model": "...", "query": "...", "api_calls": int, "tool_stats": {tool: {count, success, failure}} }`.

**To extract findings:** the constructed prompt MUST end with "Return ONLY a fenced ```json block matching {…Agent Prompt Template JSON…}". Parse the **last `from: "gpt"`** message's value, locate the JSON block. On failure → lenient `{...}` extraction; else SKIPPED.

**Bonus (ties to the bridge evidence model):** the trajectory IS the reviewer's full traversal, and `tool_stats` is a native **coverage manifest** (what tools/files it touched). hermes-agent is therefore the natural **Tier-3 reference** for capturing *evidence body + coverage*, not just conclusions — preserve `trajectory_samples.jsonl` as the provenanced evidence artifact alongside the distilled findings.

---

## Post-Analysis Protocol

- **Native-dispatch:** re-`delegate_task` Round N sub-agents with the context packet (parallel). Swarm/Kanban coordinates when present.
- **CLI/ACP:** stateless — embed full previous-round outputs + context packet in each Round N `--query`, honouring the 32 000-char stateless limit (summarize per the shared rules; never silently truncate). Record `prompt_size_chars_r{n}`.

Round counts: `quick` 0 / `standard` 1 / `thorough` ≤3 after initial analysis.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields:

```json
{
  "bridge": "hermes",
  "model_family": "multi-provider",
  "connection_used": "native-dispatch | cli | acp-server",
  "read_only_enforcement": "worktree (+ tool-mode if toolset verified)",
  "tier": 2,
  "resolved_model": "<provider/model or hermes:model.default>",
  "reasoning_applied_per_invocation": false,
  "trajectory_artifact": ".uacp/bridges/hermes-<ts>-<session>.trajectory.jsonl",
  "coverage_from_tool_stats": true
}
```

Output ID prefix: `H` (e.g., `H001`, `H002`).

---

## Notes

- **Host-can-also-be-a-bridge** — Hermes is UACP's host runtime *and* a dispatch target; this file is the dispatch target only. Kernel-as-plugin lives in `runtime-adapters/hermes/`.
- **Multi-provider exception** — absent from `config/uacp.toml` `[models]`; model resolved from hermes-agent config or `[bridges.hermes].model`. UACP does not validate Hermes models.
- **SKIPPED-only** — no HALT path; unavailability/auth failure is non-blocking.
- **Native-dispatch preferred** — `delegate_task`/Swarm when executor is hermes-agent; CLI (`run_agent.py`) for external executors; ACP as a higher-friction alternative.
- **Read-only is toolset gating, not a flag** — pick an `inspect` toolset with read-only file/codegraph tools, no writers/terminal/delegate; verify with `--list_tools`; SKIP if no write-free profile is possible.
- **No structured findings output** — parse the last `gpt` message of the trajectory JSONL for the mandated JSON block; fail closed to SKIPPED.
- **No USD budget flag** — bound with `--max_turns`.
- **Trajectory = evidence body** — preserve it; `tool_stats` is a native coverage manifest (Tier-3 reference for the evidence model).
- **Not a standalone binary** — Python harness; install via `hermes-agent.nousresearch.com/install.sh`, pip/uv, or Docker.

---

## CLI Reference

*Last verified: 2026-06-25 (nousresearch/hermes-agent, main).*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| One-shot run | `python run_agent.py --query "<task>" --enabled_toolsets safe --save_trajectories` | Scripted non-interactive review — **primary CLI path** |
| Single SWE task | `python mini_swe_runner.py --task "<task>" --output_file <path>` | Lighter one-shot, minimal deps |
| Batch | `python batch_runner.py --dataset_file <jsonl> --batch_size N --run_name <id> --distribution <toolset> --num_workers N` | Many prompts in parallel |
| Interactive TUI | `hermes` / `hermes chat` | Terminal UI — do NOT use programmatically |
| ACP server | `hermes acp` (`python -m acp_adapter.entry`) | stdio JSON-RPC for editor/IDE integration |
| MCP server | `hermes mcp serve` | Messaging/approval bridge — **not** an execution dispatcher |
| Gateway | `hermes gateway` | IM platform integrations (Telegram/Slack/…) |

### `run_agent.py` — Key args (fire-based)

| Arg | Type | Default | Purpose |
|-----|------|---------|---------|
| `--query` | string | — | The task/prompt |
| `--model` | string | config `model.default` | `provider/model` (OpenRouter form) |
| `--api_key` | string | env | API key override |
| `--base_url` | string | provider default | Endpoint override |
| `--max_turns` | int | 10 | Max tool-call rounds (no USD budget) |
| `--enabled_toolsets` | csv | — | Toolset profile (e.g. `safe`) — read-only gating |
| `--disabled_toolsets` | csv | — | Toolsets to strip (e.g. writers/terminal) |
| `--list_tools` | bool | false | Print resolved tools and exit (verify read-only) |
| `--save_trajectories` | bool | false | Write `trajectory_samples.jsonl` (parseable artifact) |
| `--verbose` | bool | false | Debug logging |

### Auth & providers

- Default provider: OpenRouter (`OPENROUTER_API_KEY`). Native fallbacks: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`/`GEMINI_API_KEY`, `KIMI_API_KEY`, `OLLAMA_BASE_URL`, +others.
- Config: `~/.hermes/.env` + `cli-config.yaml` (`model.default`). Home overridable via `HERMES_ROOT`.

### Sub-agent / delegation

`delegate_task(tasks=[{prompt, toolsets}], role="orchestrator"|"leaf", parallel=bool, timeout=int)` — agent-invoked, not a CLI flag. Sub-agents block `delegate_task`/`clarify`/`memory`/`send_message`/`execute_code`/`cronjob`. Kanban/Swarm coordination gated via `HERMES_KANBAN_TASK`.

### Install / Version / Health

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash   # → ~/.hermes
# or: pip install -e .  /  uv  /  Docker (Dockerfile in repo)
hermes --version    # version + release date
hermes doctor       # config + dependency + provider-credential check
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Parse the last `gpt` message of the trajectory for the JSON block |
| `124` | Timeout (shell `timeout` wrapper) | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other non-zero | CLI error | Capture stderr; return SKIPPED with detail |
| Valid exit, no JSON block | Parse failure | Lenient `{...}` extraction; else SKIPPED |

# Bridge: Reasonix (DeepSeek-native) — uacp-bridge reference

*Per-runtime reference for [uacp-bridge](../SKILL.md). Depends on: uacp-bridge, the domain registry (uacp-core/references/domains/).*

> **Version trap — read first.** Reasonix `1.0+` is a ground-up **Go rewrite** (the `main-v2` line); the legacy `0.x` is a **TypeScript** build with a *different CLI surface* (no `reasonix review`, different flags, JSON config). `npm`'s `latest` dist-tag may still point at the `0.x` line — installing `reasonix@latest` can leave you on legacy. This bridge **requires the 1.x Go binary** and verifies it in pre-flight. Install/upgrade via `npm i -g reasonix@next` (or the `esengine/reasonix` Homebrew tap / `reasonix upgrade`).

---

## Bridge Identity

```yaml
bridge: reasonix
model_family: deepseek/reasonix
availability: conditional
connection_preference:
  1: cli   # The reasonix 1.x Go binary — `reasonix run` (primary) / `reasonix review` (fallback)
  2: skip  # Binary missing, wrong major version, or unauthenticated — return SKIPPED (non-blocking)
```

Terminal failure state: **SKIPPED only** — this bridge has no HALT path (like the Gemini bridge). If Reasonix is unavailable, the wrong version, or auth fails, return SKIPPED and continue. Never block the calling orchestrator.

---

## Configuration Reference

Parameters this bridge reads from `config/uacp.toml` at runtime:

| Parameter | Section | Type | Default | Description |
|-----------|---------|------|---------|-------------|
| `enabled` | `[bridges.reasonix]` | boolean | `true` | Whether this bridge is active. If `false`, the orchestrator skips it. |
| `timeout_multiplier` | `[bridges.reasonix]` | float | `1.0` | Multiplier applied to the uacp-bridge base timeout estimate. Reasonix is a single CLI process with a cache-first loop — no surcharge. |
| `invocation_mode` | `[bridges.reasonix]` | string | `"run"` | `run` (primary, general prompt) or `review` (diff-scoped). The bridge prefers `run` and falls back to `review` only when the orchestrator asks for a diff-native review and no general scope is supplied. |

**Not read from TOML** (intrinsic to bridge implementation):
- `connection_preference` — defined in this file only
- Reasonix's own model/effort/permission settings live in **Reasonix's** config (`reasonix.toml` / user `config.toml`), **not** in `config/uacp.toml`. UACP only selects *which* Reasonix provider entry to invoke (see Tier Resolution).

---

## Tier Resolution

Reasonix bridge resolves the model alias and reasoning level from `config/uacp.toml` `[models]` in `UACP_ROOT`. The tier mapping lives **only** in `uacp.toml` — this file does not hardcode it.

The general tier resolution protocol is defined in [uacp-bridge/SKILL.md](../SKILL.md). Reasonix-specific steps:

1. Read `UACP_ROOT/config/uacp.toml` `[models]` section
2. Look up `[models.tier_mappings.reasonix.{tier}]` → get `alias` (+ **advisory** `reasoning`)
3. Look up `[models.providers.deepseek.models.{alias}]` → `concrete_id` → resolved model id (e.g. `deepseek-v4-flash`, `deepseek-v4-pro`)
4. Pass that model to `--model` (a Reasonix provider-entry name, or `provider/model`)

The alias is stable; the `concrete_id` is updated in the registry when DeepSeek releases new models. No bridge reference changes required.

### ⚠ Reasoning is ADVISORY for this bridge (Reasonix-specific)

Unlike Codex (`--config reasoning-effort`), Claude (`--effort`), or the legacy `0.x` Reasonix CLI, **Reasonix 1.x `run`/`review` have no `--effort` flag**. Reasoning effort is a property of the **provider entry** in `reasonix.toml` (`effort = "low" | "medium" | "high" | "max"`, forwarded as `reasoning_effort` for OpenAI-compatible providers).

Consequence: the bridge selects the **model** via `alias`, but **cannot apply the tier's `reasoning` per-invocation** — Reasonix runs at whatever `effort` the chosen provider entry bakes in. So the tier mapping's `reasoning` value is **advisory only** (recorded for transparency; not enforced). The bridge does not pretend otherwise.

*Optional, if you want tiers to genuinely differ in effort:* define separate `reasonix.toml` provider entries per (model × effort) — e.g. `deepseek-pro-high`, `deepseek-pro-max` — point `[models.tier_mappings.reasonix].alias` at those names, and add matching `[models.providers.deepseek.models.*]` entries so step 3 resolves. This is not required and not the default. Reasonix's ladder is `low|medium|high|max` (no `xhigh`; map UACP `xhigh` → `max`).

**Override via `bridge_input.tier`:** If the council assigns a specific tier, use it directly. If absent, derive from `task_type` + `intensity` per uacp-bridge rules (see [uacp-bridge/SKILL.md](../SKILL.md)).

---

## Pre-Flight — Connection Detection

### Check A: CLI Installed?

```bash
which reasonix
```

If not found → return SKIPPED immediately:

```json
{
  "bridge": "reasonix",
  "status": "SKIPPED",
  "skip_reason": "reasonix CLI not available (which reasonix returned empty)",
  "outputs": [],
  "verdict": null
}
```

### Check B: Correct Major Version? (1.x Go line — MANDATORY)

```bash
reasonix --version    # e.g. "reasonix npm-v1.12.0-rc.1" or "reasonix 1.8.0"
```

Parse the semver. If the major version is `0` (legacy TypeScript line) → return SKIPPED:

```json
{
  "bridge": "reasonix",
  "status": "SKIPPED",
  "skip_reason": "reasonix is on the legacy 0.x TypeScript line; this bridge requires the 1.x Go rewrite (reasonix review and the v2 CLI surface). Upgrade: npm i -g reasonix@next",
  "outputs": [],
  "verdict": null
}
```

This check is not optional — the `0.x` CLI lacks `reasonix review` and uses a different flag/config surface, so silently proceeding produces malformed invocations.

### Check C: Auth / Config Resolvable?

Reasonix reads provider secrets from the environment via `api_key_env` (e.g. `DEEPSEEK_API_KEY`), with values stored in Reasonix's global `<reasonix-home>/.env` shared by CLI and desktop. A resolvable `default_model` (or `--model` target) must exist in `reasonix.toml` / user `config.toml`.

```bash
reasonix doctor --json    # redacted local diagnostics: version, config, provider key presence
```

If `doctor` reports a missing provider key or no resolvable model → return SKIPPED with `skip_reason: "reasonix not configured: {detail from doctor}"`. A lightweight alternative probe is `echo "ping" | reasonix run --max-steps 1` — non-zero exit or auth error → SKIPPED.

If all checks pass → **use CLI path** (Execution).

---

## Invocation Mode — `run` (primary) vs `review` (fallback)

| Mode | Command shape | When | Trade-offs |
|------|---------------|------|------------|
| **`run`** (primary) | `reasonix run "<constructed domain prompt>"` | Default for all `task_type`s. Matches the shared Agent Prompt Template (per-domain framing, intensity/tier, JSON contract). Works on any scope, not just diffs. | Read-only must be enforced by Reasonix config/sandbox (no per-call flag); free-text output (parse a mandated JSON block). |
| **`review`** (fallback) | `reasonix review --base <ref> [--commit <sha>] --model <provider> --instructions "<prompt>"` | Only when the orchestrator wants a **diff-scoped** review and supplies a git base/commit instead of a general scope. | Read-only **by design** (review subagent, max 12 steps). But: **diff is truncated at 16 000 chars**; single subagent (no per-domain fan-out); `--instructions` is the only prompt knob; same free-text output. |

`review` is deliberately the fallback: it is scoped to a git diff and cannot carry the council's per-domain prompt fan-out. Prefer `run` and only drop to `review` for diff-native requests.

---

## Execution — Primary path (`reasonix run`)

Build one prompt per domain in `bridge_input.domains` using the Agent Prompt Template from [uacp-bridge/SKILL.md](../SKILL.md), adapted to `task_type`. Because Reasonix emits **no structured output** (see caveat), the prompt MUST mandate the JSON contract explicitly and the bridge extracts it from stdout.

Resolve tier and the Reasonix provider entry first (see Tier Resolution), then:

```bash
PROMPT="{constructed_prompt}"     # Agent Prompt Template + explicit "return ONLY a fenced ```json block"

# run_to = the OS-portable timeout helper from uacp-bridge/SKILL.md (timeout|gtimeout|perl-alarm)
run_to {final_timeout} reasonix run "$PROMPT" \
  --model "{resolved_reasonix_provider}" \
  --dir "{scope_root}" \
  --max-steps {bounded_steps} \
  --metrics "/tmp/reasonix-{session_id}.json"   # cost/token accounting only — NOT findings
```

- `--dir {scope_root}` roots config, sandbox, and file tools at the review scope (point it at the worktree under review).
- `--max-steps` bounds the agent's tool-call rounds (there is **no USD budget flag** in 1.x — cost is observed retrospectively via `--metrics`).
- Stdin is also accepted (`echo "$PROMPT" | reasonix run`) when arg-length is a concern.

### Read-only enforcement (`capability_profile: inspect`)

Follow the **Review Containment** ladder in [uacp-bridge/SKILL.md](../SKILL.md) (fail-closed; minimum tier from `[bridges.defaults].inspect_containment`, default `worktree`). Reasonix `run` is autonomous and has **no per-invocation read-only / allowed-tools flag** (unlike Gemini `--approval-mode plan` or Claude `--allowedTools`), so its Tier-1 mode is **not verifiable** — it depends on the worktree floor:

- **Tier 1 (hard) — use `reasonix review` for diff-scoped `inspect`.** The `review` subagent is read-only by design → declare `read_only_enforcement: tool-mode`.
- **Tier 2 (floor) — for `reasonix run`, run inside the orchestrator-provided ephemeral worktree** (`--dir {worktree}`). Reasonix file-writers refuse paths outside `[sandbox] workspace_root` (= the `--dir` root) only when its sandbox is enabled — so the disposable worktree is the real guarantee: any stray write lands in throwaway space, never the live tree. Declare `read_only_enforcement: worktree`. Optionally also add `[permissions] deny = ["write_file","edit_file","multi_edit","move_file","Bash(*)"]` in `reasonix.toml` and an "analysis only" prompt line (defense-in-depth, not a substitute).

If neither a `review` invocation nor an ephemeral worktree is available → return **SKIPPED** (`skip_reason: "cannot guarantee read-only containment"`). Never resolve `inspect` to a write-capable, uncontained `reasonix run`.

---

## Execution — Fallback path (`reasonix review`)

```bash
# run_to = the OS-portable timeout helper from uacp-bridge/SKILL.md
run_to {final_timeout} reasonix review \
  --base "{base_ref}" \
  --model "{resolved_reasonix_provider}" \
  --instructions "{constructed_prompt: domains, focus areas, and the JSON-output contract}"
```

- No `--base`/`--commit` → reviews uncommitted working-tree changes; `--base main` → `main...HEAD`; `--commit <sha>` → that commit.
- Output is plain text to stdout (exit 0). Parse the mandated JSON block as in the primary path.
- Mind the **16 000-char diff truncation** — for large diffs, prefer `run` with an explicit file list, or split the review.

---

## ⚠ Structured-output caveat (applies to both paths)

Reasonix has **no `--json` / `--output-format` for findings**. The only machine-readable artifact is `reasonix run --metrics <path>`, which is **cost/token/cache accounting**, not findings. Consequences for parsing:

1. The constructed prompt MUST end with an explicit contract, e.g.:
   `Return ONLY a single fenced \`\`\`json block matching this schema: {…Agent Prompt Template JSON…}. No prose before or after.`
2. Capture stdout, locate the last fenced ```json block, parse it. On parse failure → attempt a lenient extraction of the outermost `{...}`; if still unrecoverable → return SKIPPED (`skip_reason: "unparseable reasonix output"`), per the shared CLI Error Handling table.
3. Read `--metrics` JSON for `resolved cost`/tokens and record alongside the bridge output (does not affect findings).

This is the single biggest difference from the Codex/Claude/Gemini bridges, all of which have first-class JSON output. Treat free-text parsing as best-effort and fail closed to SKIPPED.

---

## Post-Analysis Protocol

Reasonix is a stateless single-process CLI like Gemini/Codex/Kimi — run the uacp-bridge Post-Analysis Protocol (see [uacp-bridge/SKILL.md](../SKILL.md)) via re-prompting. Two context-passing options:

- **Stateless embed (default):** embed the full previous-round outputs + context packet in each Round N prompt, honouring the **32 000-char** stateless context limit (summarize per the shared rules; never silently truncate).
- **Session continuity (Reasonix-specific optimization):** Reasonix persists sessions; a Round N call may `reasonix run --continue` (most recent) or `--resume <session-file>` (specific) to reuse Round 1 history, so the Round N prompt carries only the context packet. Use only when the same session file is known to hold this bridge's Round 1; otherwise fall back to stateless embed.

Record `prompt_size_chars_r{n}` per round. Round counts: `quick` 0 / `standard` 1 / `thorough` ≤3 after the initial analysis.

---

## Output

For the full Output Schema, see [uacp-bridge/SKILL.md](../SKILL.md). Bridge-specific fields added by this adapter:

```json
{
  "bridge": "reasonix",
  "model_family": "deepseek/reasonix",
  "connection_used": "cli",
  "invocation_mode": "run | review",
  "read_only_enforcement": "tool-mode (review) | worktree (run)",
  "tier": 2,
  "resolved_model": "<resolved from registry>",
  "resolved_reasoning": "<advisory — from tier mapping; not applied per-invocation>"
}
```

`resolved_reasoning` is recorded for transparency only; Reasonix applies effort from the provider entry, not per-invocation (see Tier Resolution). Output ID prefix: `R` (e.g., `R001`, `R002`).

---

## Notes

- **Requires the 1.x Go line** — pre-flight Check B SKIPs on `0.x`. `npm`'s `latest` may lag on `0.x`; use `reasonix@next`, the Homebrew tap, or `reasonix upgrade`.
- **SKIPPED-only** — no HALT path; unavailability/auth failure is always non-blocking.
- **`run` is primary, `review` is the diff-scoped fallback** — `review` cannot carry per-domain fan-out and truncates diffs at 16k chars.
- **No structured findings output** — mandate a fenced JSON block in the prompt and extract it; fail closed to SKIPPED on parse failure.
- **Reasoning is config-baked, not a flag** — select a provider entry whose `effort` matches; `xhigh` → `max`.
- **No USD budget flag** in 1.x — bound with `--max-steps`; observe cost via `--metrics`.
- **Read-only is config/sandbox/prompt, not a flag** — for `inspect`, confine via `--dir` worktree + `[permissions] deny` writers; downgrade to `review` or SKIP if no write guarantee is possible.
- **UACP never configures Reasonix's models** — `config/uacp.toml` only names which Reasonix provider entry to invoke; the provider/effort/permission definitions live in `reasonix.toml`.
- **Tier is never hardcoded** — model selections come from `config/uacp.toml`; update the TOML when DeepSeek releases new models.

---

## CLI Reference

*Last verified: 2026-06-25 (reasonix 1.12.0-rc.1, Go `main-v2` line).*

### Invocation Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| One-shot run | `reasonix run "<task>"` | Scripted/programmatic use — **primary bridge path** |
| Diff review | `reasonix review [--base …]` | Diff-scoped review — **fallback bridge path** |
| Interactive TUI | `reasonix` | Terminal UI — do NOT use programmatically |
| ACP server | `reasonix acp` | stdio NDJSON JSON-RPC agent (editor/IDE integration) |
| HTTP server | `reasonix serve` | HTTP+SSE frontend (optional auth) |

### `reasonix run` — Flags (1.x)

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| (message) | string | stdin if omitted | Prompt — positional args joined by spaces, or piped via stdin |
| `--model` | provider name | config `default_model` | Reasonix provider entry name (or `provider/model`) |
| `--max-steps` | int | `0` (config/default) | Max tool-call rounds; bounds work (no USD budget exists) |
| `--metrics` | path | none | Write a JSON token/cache/cost summary to this path (accounting only) |
| `--dir` | path | cwd | Change to this dir first; config, sandbox, and file tools resolve from here |
| `--show-thinking` | flag | off | Show thinking text instead of the collapsed marker |
| `-c`, `--continue` | flag | off | Resume the most recent saved session (non-interactive) |
| `--resume` | path | none | Resume a specific session file (takes precedence over `--continue`) |

> No `--effort`, `--budget`, `--system`, `--json`, or `--output-format` in 1.x. Effort = provider-config; reasoning depth is selected by provider entry, not flag.

### `reasonix review` — Flags (1.x)

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--base` | branch/commit | HEAD (working-tree changes) | Diff `--base...HEAD` |
| `--commit` | sha | none | Review the changes introduced by one commit (`sha^..sha`) |
| `--model` | provider name | config `default_model` | Provider entry override |
| `--instructions` | string | none | Extra review instructions appended to the prompt (only prompt knob) |

Runs the built-in `review` subagent (read-only, max 12 steps); diff truncated at 16 000 chars; plain-text output to stdout.

### Auth & Config

- Provider secrets: env via `api_key_env` (e.g. `DEEPSEEK_API_KEY`); values stored in Reasonix global `<reasonix-home>/.env` (shared by CLI + desktop). Project `.env`, home `.env`, and shell vars are **not** provider-key runtime fallbacks.
- Config resolution: **flag > `./reasonix.toml` > user `config.toml` > built-in defaults**. User config path (v1.8.1+): `~/.reasonix/config.toml` (macOS/Linux), `%AppData%\reasonix\config.toml` (Windows). Override Reasonix home with `$REASONIX_HOME`.
- Minimal `reasonix.toml`:
  ```toml
  default_model = "deepseek-flash"
  [[providers]]
  name        = "deepseek-flash"
  kind        = "openai"
  base_url    = "https://api.deepseek.com"
  model       = "deepseek-v4-flash"
  api_key_env = "DEEPSEEK_API_KEY"
  # effort    = "high"     # provider-baked reasoning depth (low|medium|high|max)
  ```
- Models named in docs/preset: `deepseek-flash`/`deepseek-pro` → `deepseek-v4-flash`/`deepseek-v4-pro`. Any OpenAI-compatible endpoint is a config entry (also speaks Anthropic-kind providers).

### MCP

Reasonix is an MCP client: declare `[[plugins]]` (stdio `command`/`args`, or `type="http"`/`url`/`headers`) in `reasonix.toml`, OR drop a Claude-Code `.mcp.json` in the project root (read field-for-field; `reasonix.toml` wins on name collision). Manage via `reasonix mcp <add|remove|list|import>`. Not needed for basic review dispatch.

### Version / Install / Health

```bash
reasonix --version            # must be >= 1.0.0 for this bridge (Go line)
reasonix doctor --json        # redacted diagnostics: version, config, provider key presence
npm i -g reasonix@next        # install/upgrade to the 1.x Go line (latest dist-tag may be 0.x!)
brew tap esengine/reasonix && brew install esengine/reasonix/reasonix
reasonix upgrade [--check] [--force]   # self-update from GitHub releases (SHA256-verified)
```

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Parse stdout for the mandated JSON block |
| `124` | Timeout (shell `timeout` wrapper) | Return SKIPPED, `skip_reason: timeout_after_{n}s` |
| Other non-zero | CLI error | Capture stderr; return SKIPPED with detail |
| Valid exit, no JSON block | Parse failure | Lenient `{...}` extraction; else SKIPPED |

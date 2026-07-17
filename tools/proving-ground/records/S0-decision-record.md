# S0 — OpenAB lift spike: decision record

Throwaway verification spike for UACP Proving Ground (design: `design/proving-ground/20-runner.md`, `50-plan.md` S0).
Host: darwin arm64. Tools: cargo/rustc (~/.cargo/bin), Docker running, ollama OpenAI-compat at :11434, hermes v0.17.0 (~/.local/bin/hermes).
Clone: `github.com/openabdev/openab` @ shallow HEAD (Jul 2026), version 0.9.0. No UACP repo / ~/.hermes writes performed (temp HERMES_HOME used).

---

## Per-check verdicts

### (a) Crate separability — PASS (with a headline correction to the design's premise)

**The design names the wrong crate.** `50-plan.md`/`20-runner.md` say "lift `crates/openab-agent` (transport + session pool)". Reality:

- **`openab-agent` is a top-level dir, NOT under `crates/`, and is EXCLUDED from the root workspace** (`openab/Cargo.toml`: `exclude = ["openab-agent", "crates/platform-schema"]`). Its `Cargo.toml` declares `name="openab-agent"`, `description="Native Rust coding agent with built-in ACP support"`. It is OpenAB's **own standalone coding agent product** (a *server-side* ACP speaker — `openab-agent/src/acp.rs`), with **zero path deps on sibling openab crates** (all deps external: tokio, rmcp, oauth2, jsonschema, reqwest×2, …). It is separable, but it is **not** the client transport the runner needs.
- **The actual ACP CLIENT transport + session pool lives in `crates/openab-core/src/acp/`** (`mod.rs` 9, `protocol.rs` 718, `connection.rs` 1100, `pool.rs` 1001, `agentcore.rs` 722 = **3550 LoC**). This is the code that spawns an agent's ACP adapter subprocess and drives it over JSON-RPC.
- **Coupling of that client to the broker is minimal and cleanly liftable:**
  - Core client (`connection.rs`+`protocol.rs`+`pool.rs`+`mod.rs` = **2828 LoC**) imports only ubiquitous externals: `anyhow, serde, serde_json, tokio, tracing`. No serenity/discord, no AWS, not even reqwest (LLM I/O lives in the agent, not the client).
  - Only ONE broker symbol crosses in: `crates/openab-core/src/acp/pool.rs:3: use crate::config::AgentConfig;` — a single config struct.
  - `agentcore.rs` (722 LoC, 10 `aws_/bedrock/sigv4` refs) is the AWS Bedrock ACP variant — droppable, and the design already drops `agentcore/`.

**No `cargo build` was executed** (honest disclosure): a full build targets the crate we would *drop* (the `openab` broker), is heavy (rust:1-bookworm multi-stage), and the wrong-crate finding makes it low-value. Separability is established **statically** — workspace-exclude + package identity + dependency-edge mapping above. Size of a lift: ~2828 LoC, 5 trivial external deps, 1 config struct to inline.

### (b) One agent end-to-end over ACP from a bare harness — PASS (genuine model reply)

Harness: `acp_harness.py` (~150 LoC, stdlib only) spawns `hermes acp --accept-hooks` as a subprocess, NDJSON JSON-RPC over stdio, wire shapes mimicked from `openab-core/src/acp/connection.rs`. Model backed by local ollama via **temp HERMES_HOME only** (`s0-spike/hermes-home/config.yaml`, provider=custom, base_url=:11434/v1) + `OPENAI_BASE_URL/OPENAI_API_KEY` env — ~/.hermes untouched.

Exchange (`acp-exchange.log`, first lines):
```
--> initialize {protocolVersion:1, clientCapabilities:{}}
<-- id:1 result: agentInfo{name:hermes-agent, version:0.17.0}, protocolVersion:1, agentCapabilities{loadSession, sessionCapabilities.fork, ...}
--> initialized (notif)
--> session/new {cwd, mcpServers:[]}   <-- id:2 result.sessionId: b738deb4-...
--> session/prompt {sessionId, prompt:[{type:text, text:"Reply with exactly the single word: PONG"}]}
<-- session/update stream ... content.text "P" then "ONG"    <-- id:3 result.stopReason: "end_turn"
```
Round-trip confirmed: prompt in → **model-generated "PONG" streamed back over ACP** → `stopReason:end_turn`. `hermes acp --check` = "Hermes ACP check OK".

### (c) Container → host ollama + multi-turn tool calling — PASS (both parts)

- **c1 (container reachability):** `docker run --rm curlimages/curl -s http://host.docker.internal:11434/v1/models` → **HTTP=200**. The env-injection path reaches host ollama from inside a container.
- **c2 (multi-turn tool calling on ollama OpenAI-compat, the design's "known-weak path"):** `qwen2.5:3b` against `/v1/chat/completions` with a `get_weather` tool:
  - Turn 1 → well-formed tool_call: `id=call_wpiaeaco`, `type=function`, `function.name=get_weather`, `arguments="{\"city\":\"Paris\"}"` (valid JSON, parses).
  - Turn 2 (fed `role:tool` result "18C, sunny") → final answer: *"The current weather in Paris is 18°C and it's sunny outside."*
  - The flagged-weak path **works cleanly** with qwen2.5:3b. Honest note: single trial, temp=0; not stress-tested for multi-tool / parallel calls.

### (d) Server-side adapter inventory — PASS

Per-agent Dockerfiles present (20): `Dockerfile.{claude,codex,copilot,cursor,devin,gemini,grok,hermes,mimocode,opencode,pi,antigravity,native,unified,package,agentcore,gateway,builder,ci,final}` + base `Dockerfile`. All build the `openab` broker binary (root workspace) as the supervisor, then set `OPENAB_AGENT_COMMAND` to the per-agent ACP adapter it spawns:

| cell | `OPENAB_AGENT_COMMAND` | adapter source |
|---|---|---|
| hermes | `hermes-acp` | Hermes venv console-script (== `hermes acp`), built-in. **Verified live on host, v0.17.0.** |
| claude | `claude` driven via **`@agentclientprotocol/claude-agent-acp@0.45.0`** (npm) + `@anthropic-ai/claude-code@2.1.179`; `CLAUDE_CODE_EXECUTABLE=/usr/local/bin/claude` | `Dockerfile.claude:24-27` |
| codex | `codex-acp` | `@agentclientprotocol/codex-acp` + `@openai/codex` (`Dockerfile.codex:24`) |
| gemini | `gemini --acp` | native Gemini CLI |
| pi | `openab-agent` | `pi-acp` + `@earendil-works/pi-coding-agent` (`Dockerfile.pi:25`) — pi routed through openab-agent |
| opencode/cursor/grok/copilot/devin/mimo | `opencode acp` / `cursor-agent acp` / `grok agent stdio` / `copilot --acp --stdio` / `devin acp` / `mimo acp` | native/CLI adapters |
| antigravity | `agy-acp` | the in-repo `agy-acp` crate (own workspace) |

**Claude adapter identity correction:** OpenAB ships **`@agentclientprotocol/claude-agent-acp@0.45.0`**, NOT Zed's `claude-code-acp`. The design/memory note ("the real Claude adapter is Zed's claude-code-acp, not claude-agent-acp — OpenAB's table is loose on names") is **backwards for what OpenAB actually installs** — it installs claude-agent-acp. (No docker build performed per spike scope — inventory + entrypoint inspection only.)

---

## Headline decision recommendation: **REIMPLEMENT the thin ACP client** (mine OpenAB for edge-cases; do not import the crate)

Reason, grounded in the spike:
1. **The protocol is proven small.** A ~150-line stdlib Python harness did the full working client — initialize / session lifecycle / prompt / streaming `session/update` / permission auto-reply scaffolding — against the real `hermes acp`, with a genuine model round-trip. There is little to "lift" that isn't cheap to write.
2. **What we actually depend on is NOT OpenAB's code.** The hard external dependency is each agent's **ACP adapter binary** (`hermes-acp`, `claude-agent-acp`, `codex-acp`, …), which we spawn either way. OpenAB's value is the *inventory + pinned versions* (check d) and its *edge-case handling*, not the transport bytes.
3. **Lift is viable but carries the broker's shape.** `openab-core/src/acp/` is cleanly separable (2828 LoC, 5 externals, 1 `AgentConfig` struct) — a real fallback — but importing it drags `openab-core` 0.8.5's crate surface and Rust when red-pen decision #1 puts the bench in Python (`tools/proving-ground/`). Not worth it for ~2.8k LoC we can write to our own seam.
4. **Do mine, don't ignore.** `openab-core/src/acp/connection.rs:845-885` (`build_permission_response`) is a ready-made map of each agent's permission option-IDs (kiro/claude/codex/gemini variants), plus session-resume, watchdog, and stale-response handling — reimplement the client, but copy these edge behaviors rather than re-deriving them.

This matches `50-plan.md` open-question #1's lean ("lifted ACP/transport stays … a thin CLI the Python bench orchestrates"), refined: **thin, self-authored ACP client (Python for the bench, or a small Rust CLI), seeded by OpenAB's edge-case catalogue.**

## Go / no-go per agent cell

- **hermes — GO.** `hermes acp` built-in (v0.17.0), `--check` OK, full ACP round-trip with genuine model reply proven from a bare harness. Ready to seed the S1 `hermes-bare` smoke cell. **Caveat below (context floor) is a cell-config item, not a blocker.**
- **claude — GO (adapter exists) / auth-gated.** Adapter pinned and real: `@agentclientprotocol/claude-agent-acp@0.45.0`. Not live-tested here (no docker build in spike scope). Gated by `50-plan.md` open-question #2 (in-container auth for the unattended lane) — an S4 concern, flag early. NOT Zed's claude-code-acp.
- **codex / pi / gemini / others — deferred (S5+).** Adapters asserted + pinned by OpenAB Dockerfiles; none live-verified. Each is a cell-inventory fact, not a substrate risk.

## Surprises (brutally honest)

1. **Design's lift target is misidentified.** Transport = `crates/openab-core/src/acp/`; `openab-agent` = OpenAB's *own* standalone native agent (a server-side ACP speaker), not the client. Any lift language in the bundle must be corrected before S1.
2. **Claude adapter is `claude-agent-acp`, not Zed's `claude-code-acp`** — the design/memory note is inverted vs. what OpenAB ships.
3. **Hermes enforces a hard 64K context floor.** `qwen2.5:3b` (32K) is **rejected at `session/new`** ("below the minimum 64,000 required"). Worse: overriding `model.context_length: 65536` in config let `session/new` pass, but Hermes **re-guarded at prompt time** and returned a canned warning ("Ollama loaded qwen2.5:3b with only 32,768 tokens of runtime context") **instead of generating** — a silent refusal that would look like a passing run to a naive harness. **`llama3.2:3b` (131K, already installed) works cleanly.** → S1 cell finding: the hermes smoke-tier model MUST report ≥64K context; **qwen2.5:3b is unusable as the hermes cell model** despite being the fast default. (The 35B Qwen3.6 and qwen3:30b-a3b/262K also qualify.)
4. **The "known-weak" ollama tool-calling path PASSED** — the pessimism in the design was unfounded for single-tool multi-turn on qwen2.5:3b.
5. **Runtime model = broker-as-supervisor + adapter binary.** The Dockerfiles run the `openab` broker (the part we DROP) as the process that spawns the adapter. Dropping it means our runner spawns the adapter directly — which is exactly what `acp_harness.py` did (no `openab` binary in the loop). Confirms the reimplement path end-to-end.

## Evidence files (in `s0-spike/`)
- `acp_harness.py` — the bare ACP client harness
- `acp-exchange.log` — raw JSON-RPC exchange (initialize→session/new→prompt→PONG) + result summary
- `hermes-home/config.yaml` — isolated ollama-pointing config (no ~/.hermes writes)
- `openab/` — shallow OpenAB clone (citations above)

# uacp-bridge

Unified bridge dispatch contract for all runtime adapters in the UACP Bridge Adapter Suite. Defines the pre-flight SOP, input/output schemas, status semantics, tier system, timeout/verdict logic, and artifact format that every bridge implements.

## Why This Exists

Each runtime adapter (Claude, Gemini, Codex, OpenCode, Kimi) connects to a different AI runtime with different CLIs and APIs. `uacp-bridge` provides the shared contract so orchestrating skills only need to know one schema — not five.

## What It Defines

| Section | Purpose |
|---------|---------|
| Pre-flight SOP | Ordered detection steps every bridge follows before executing |
| Tier system | Abstract tier (0–4) → model resolution via `config/uacp.toml` |
| Timeout estimation | Scope-based formula, no hardcoded values |
| Input schema | `bridge_input` — the standard contract every bridge accepts |
| Output schema | Common report structure every bridge returns |
| Status semantics | `COMPLETED`, `SKIPPED`, `HALTED`, `ABORTED` and when each applies |
| Verdict logic | Pass/Fail/Concerns rules per task_type |
| Artifact format | JSONL event log + Markdown summary in `.uacp/bridges/` |
| Error handling | Exit code patterns, timeout handling, parse failure recovery |

## How Bridges Use This

Each per-runtime adapter references this document. When an orchestrating skill embeds a bridge's instructions into a Task agent prompt, the bridge follows `uacp-bridge` for all shared behavior and only adds its own connection-specific logic on top.

```
uacp-bridge/SKILL.md (the shared contract)
  ←  defines the contract for all runtime adapters

references/claude.md    ←  implements it: Task tool → claude CLI → Anthropic API
references/gemini.md    ←  implements it: gemini CLI → SKIPPED
references/codex.md     ←  implements it: MCP → codex exec → HALTED
references/opencode.md  ←  implements it: HTTP API → opencode run → HALTED
references/kimi.md      ←  implements it: kimi CLI → SKIPPED
```

## Part of

- UACP Bridge Adapter Suite
- Consumed by: all bridge adapters, agent-council, and lifecycle skills
- Depends on: nothing (this is the base layer)

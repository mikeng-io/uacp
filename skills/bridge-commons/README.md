# Bridge Commons

Shared contract for all bridge adapters in the Deep Skills Suite. Defines the pre-flight SOP, input/output schemas, status semantics, and artifact format that every bridge implements.

## Why This Exists

Each bridge adapter (Claude, Gemini, Codex, OpenCode) connects to a different AI runtime with different CLIs and APIs. Bridge-commons provides the shared layer so orchestrating skills only need to know one schema — not four.

## What It Defines

| Section | Purpose |
|---------|---------|
| Pre-flight SOP | Ordered detection steps every bridge follows before executing |
| Timeout estimation | Scope-based formula, no hardcoded values |
| Input schema | `bridge_input` — the standard contract every bridge accepts |
| Output schema | Common report structure every bridge returns |
| Status semantics | `COMPLETED`, `SKIPPED`, `HALTED`, `ABORTED` and when each applies |
| Artifact format | JSONL event log + Markdown summary in `...outputs/bridges/` |
| Error handling | Exit code patterns, timeout handling, parse failure recovery |

## How Bridges Use This

Each bridge's `SKILL.md` references this document. When an orchestrating skill embeds a bridge's instructions into a Task agent prompt, the bridge follows `bridge-commons` for all shared behavior and only adds its own connection-specific logic on top.

```
bridge-commons  ←  defines the contract
bridge-claude   ←  implements it: Task tool → claude CLI → Anthropic API
bridge-gemini   ←  implements it: gemini CLI → SKIPPED
bridge-codex    ←  implements it: MCP → codex exec → SKIPPED
bridge-opencode ←  implements it: HTTP API → opencode run → SKIPPED
```

## Part of

- Deep Skills Suite
- Consumed by: all bridge adapters, `deep-council`
- Depends on: nothing (this is the base layer)

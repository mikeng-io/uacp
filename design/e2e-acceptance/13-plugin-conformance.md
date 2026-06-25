---
type: design
title: Plugin conformance — the Priority-1 measurement (is the installed plugin actionable?)
description: The FIRST and primary measurement — exactly how the harness proves every capability the UACP plugin DECLARES is actionable in a freshly-installed container, before any lifecycle is driven. Comprehend the plugin manifest (declared capabilities) -> measure each is actionable with a concrete fail-closed probe -> serialize a conformance result. Defines the probe per capability type with its evidence. The lifecycle/governance measurement ([21]) is Priority 2 (next).
tags: [e2e, plugin, conformance, measurement, smoke, mcp, skills, hooks, actionable]
timestamp: 2026-06-26
edges:
  - {dst: 10-topology, rel: depends_on, provenance: derived}
  - {dst: 11-runner-adapter-seam, rel: depends_on, provenance: derived}
---

# Plugin conformance — the Priority-1 measurement

## Priority (mike): make the plugin actionable FIRST

Before driving any lifecycle, prove the **plugin itself works when installed** — skills load, hooks fire, the MCP server starts and its tools are callable, commands resolve. If the plugin doesn't register and function in a fresh agent, the lifecycle test is meaningless. So Increment 0 measures *plugin actionability*; the **MCP/lifecycle governance measurement ([21](21-assertions.md)) is Priority 2 (next time)**.

## How measurement works here, exactly (CMS applied to the plugin)

The plugin's **manifest is the claim**; an **actionable probe is the check**; the harness is the gate — the same comprehend→measure→serialize discipline UACP enforces on agents, turned on the plugin install:

1. **comprehend** — parse `.claude-plugin/plugin.json` (+ `marketplace.json`, the skills tree, the hooks config, the MCP config) into a list of **declared capabilities**: `{skills[], hooks[], mcp_tools[], commands[]}`. This list is *derived from the manifest*, not hand-written — so a capability added to the plugin is automatically owed a probe (no silent coverage gap).
2. **measure** — for EACH declared capability, run a concrete probe **inside the installed runner container** that proves it is live, with **evidence** (a captured artifact), fail-closed: no evidence == FAIL, not assumed-pass.
3. **serialize** — emit a `conformance.json`: per capability `{name, kind, probe, status: pass|fail, evidence}`. Pass iff EVERY declared capability is actionable. This is the Priority-1 verdict.

## The probe per capability type (the exact mechanism)

| Capability | "Actionable" means | Probe (in the installed container) | Evidence |
|---|---|---|---|
| **MCP server + tools** | the server starts and exposes the governed tools; a read-only one returns a valid result | spawn the server as the plugin configures it; MCP `tools/list` ⇒ set **equals** `{s.name for s in tool_specs()}`; `tools/call` a read-only tool (`uacp_oracle_query` or `uacp_heartgate_check`) ⇒ JSON result, exit clean | the `tools/list` payload + the call's JSON response |
| **Skills** | each declared skill is installed at the discoverable path with valid frontmatter, and is invokable | the skill files resolve under the plugin's skills root; each `SKILL.md` frontmatter parses + has the required kind/name; (where the runtime allows) the agent can *list* the skill | the resolved paths + parsed frontmatter; a list-skills probe output |
| **Hooks** | each declared hook is registered AND fires on its event with the intended effect | trigger the hook's event in the container (e.g. a PreToolUse tool-call ⇒ the Guardian hook runs; SessionStart ⇒ `UACP.md` injected) and observe the effect (block/inject/log) | the hook's observable effect (the injected text / the block decision / the hook log line) |
| **Commands** (if any) | each declared slash-command resolves to its handler | invoke the command headless; it dispatches without "unknown command" | the command's dispatch output |

**Fail-closed throughout:** a probe that cannot run (server won't start, skill path missing, hook didn't fire) is a **FAIL with the reason captured**, never a skipped/assumed pass — the same #503-class rule the verification gate uses.

## What this catches that nothing else can

A packaging regression: the manifest references a moved skill; the MCP config points at a stale path; a hook is declared but not wired; `tool_specs()` drifts from what the server actually lists; the plugin installs but a skill's frontmatter is invalid. All invisible to in-process tests (which import directly) — visible here because the probe runs against the **freshly-installed plugin in a clean agent container**.

## Boundary with Priority 2

Plugin conformance proves the capabilities are **live and callable**. It does NOT drive a governed run or measure governance-correctness — that is the lifecycle measurement ([21](21-assertions.md)), explicitly deferred. The clean seam: conformance answers *"can the agent USE UACP?"*; the lifecycle measurement answers *"when it does, does the governance hold?"*.

## To expand
- The exact manifest→capability extraction (which files, which keys) once the parallel adapter session finalizes the plugin shape.
- A per-capability evidence schema feeding the same `result.json` corpus ([22](22-benchmark.md)) so conformance is benchmarkable across runtimes too.
- Whether a skill/command "invokable" probe needs a live agent turn or can be a static+dispatch check (runtime-dependent; CC may differ from Hermes/Codex).

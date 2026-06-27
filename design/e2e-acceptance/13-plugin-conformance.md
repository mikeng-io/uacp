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

## As-built capability surface (RESOLVED — adapter session, commit 7da7ed8)

The council caught that an earlier plugin install shipped **hooks only** (the MCP server was wired
via a gitignored, personal `.mcp.json` — a marketplace install got zero governed tools). The parallel
adapter session **fixed this**: `.claude-plugin/plugin.json` now declares the capability surface a CC
install actually exposes, so the EXPECTED ∪ DISCOVERED model below has concrete sources:

- **MCP tools** → `plugin.json:mcpServers.uacp` — launched via
  `uv run --no-project --with mcp>=1.0 … python ${CLAUDE_PLUGIN_ROOT}/runtime-adapters/mcp/uacp_mcp_server.py`
  (uv self-provisions the server's deps; the **one host prereq is `uv`** in the runner image). The
  probe starts THIS command and asserts `tools/list` == `tool_specs()`.
- **Hooks** → `plugin.json:hooks` → `./runtime-adapters/claude/hooks.json` (explicit pointer; not auto-discovery).
- **Skills** → convention-discovered from the shipped `skills/<dir>/SKILL.md` tree (ADR-0017).

The conformance harness still operates **expected-vs-actual** (a regression that un-ships any of these
must FAIL, not vacuously pass) — but the discovery recipe for Claude Code is now pinned, not pending.

## How measurement works here, exactly (expected-vs-actual, not manifest-parse)

The capability inventory is **NOT** "what the manifest enumerates." It is the per-runtime UNION of:

- **EXPECTED** — what a UACP install *should* provide, from UACP's own capability spec (the governed
  `tool_specs()` for MCP; the `skills/` tree it ships; the hooks in `runtime-adapters/claude/hooks.json`). This is the
  contract, independent of any one runtime's manifest format.
- **DISCOVERED** — what the install *actually* exposes, found the way the runtime loads it (a **per-
  runtime discovery recipe** owned by the runner-adapter seam [11](11-runner-adapter-seam.md): for
  Claude Code = the plugin's hooks file + the shipped MCP config + the auto-discovered skills tree;
  for Hermes/Codex = that runtime's mechanism).

CMS turned on the install: **comprehend** EXPECTED ∪ DISCOVERED → the capability set; **measure** each
with a concrete probe in the installed container (with evidence, fail-closed); **serialize** a
`conformance.json`. **A capability that is EXPECTED but not DISCOVERED/actionable is a FAIL** — this is
what catches "the plugin didn't ship the MCP server." Pass iff every expected capability is actionable.

## The probe per capability type (the exact mechanism)

Only probe capability KINDS the runtime supports AND UACP actually expects — never a phantom row
(council: there are no `commands` in the UACP plugin, so probing "commands" would silently pass an
empty category = false coverage). For Claude Code today the expected kinds are MCP tools, skills, and
hooks.

| Capability | "Actionable" means | Probe (in the installed container) | Evidence |
|---|---|---|---|
| **MCP server + tools** | the install registers the server; it starts; it exposes the EXPECTED governed tools | the runtime's MCP wiring starts the server; MCP `tools/list` ⇒ set **equals** `{s.name for s in tool_specs()}` (this alone needs no preconditions — the primary liveness assertion); THEN one `tools/call` against a **deliberately-seeded minimal fixture** to prove dispatch works end to end | the `tools/list` payload + the seeded call's JSON response |
| **Skills** | each EXPECTED skill is discovered at the runtime's skills path with valid frontmatter, and is listable | the `skills/<dir>/SKILL.md` files resolve where the runtime discovers them; each frontmatter parses + has the required kind/name; (where the runtime allows) the agent can *list* the skill | the resolved paths + parsed frontmatter; a list-skills probe output |
| **Hooks** | each declared hook is registered AND fires on its event with the intended effect | trigger the hook's event in the container (a PreToolUse tool-call ⇒ the Guardian hook runs; SessionStart ⇒ `UACP.md` injected) and observe the effect (block/inject/log) | the hook's observable effect (the injected text / the block decision / the hook log line) |

> **Probe-tool choice (council):** the `tools/call` probe must use a genuinely side-effect-free,
> NO-precondition path. `uacp_heartgate_check` (needs a real `transition_path` + `authority_artifact`
> + a seeded run) and `uacp_oracle_query` (`external.network_read`, ships `enabled=false`, and the
> runner is offline) are BOTH unsuitable. Prefer **`tools/list`-only as the liveness assertion**
> (no call needed), plus a `tools/call` only against a fixture the harness seeds for exactly that
> purpose — never against an arbitrary "read-only" tool that turns out to have preconditions.

**Fail-closed throughout:** a probe that cannot run (server not registered, won't start, skill path
missing, hook didn't fire) is a **FAIL with the reason captured**, never a skipped/assumed pass — the
same #503-class rule the verification gate uses.

## What this catches that nothing else can

A packaging regression: the manifest references a moved skill; the MCP config points at a stale path; a hook is declared but not wired; `tool_specs()` drifts from what the server actually lists; the plugin installs but a skill's frontmatter is invalid. All invisible to in-process tests (which import directly) — visible here because the probe runs against the **freshly-installed plugin in a clean agent container**.

## Boundary with Priority 2

Plugin conformance proves the capabilities are **live and callable**. It does NOT drive a governed run or measure governance-correctness — that is the lifecycle measurement ([21](21-assertions.md)), explicitly deferred. The clean seam: conformance answers *"can the agent USE UACP?"*; the lifecycle measurement answers *"when it does, does the governance hold?"*.

## To expand (build-detail — the MODEL above is the design; these are for BUILD)
- The CC discovery recipe is now PINNED (plugin.json `mcpServers`/`hooks` + the skills tree, commit 7da7ed8); the Hermes/Codex recipes are pinned when those runners are added.
- The runner image must include `uv` (the MCP server's launch prereq) — a runner-image build detail ([11](11-runner-adapter-seam.md)).
- The minimal seeded fixture for the `tools/call` dispatch probe.
- A per-capability evidence schema feeding the same `result.json` corpus ([22](22-benchmark.md)) so conformance is benchmarkable across runtimes too.
- Whether a skill "invokable" probe needs a live agent turn or can be a static+dispatch check (runtime-dependent).

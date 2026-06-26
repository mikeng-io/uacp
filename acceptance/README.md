# UACP E2E Acceptance Harness

The containerized, real-install acceptance test for UACP. Design: [`design/e2e-acceptance/`](../design/e2e-acceptance/).

This is the **acceptance** layer (real install, real surface), distinct from the in-process
integration tests that gate CI. It is built in increments (design node 30).

## Increment 0 — plugin conformance (built)

Proves the UACP plugin is **actionable**: every capability it should expose actually works once
installed. The prober ([`conformance.py`](conformance.py)) comprehends the plugin manifest into the
expected capabilities, then probes each against the real plugin:

- **MCP tools** — launches the server EXACTLY as `plugin.json:mcpServers.uacp` configures it
  (`uv run … runtime-adapters/mcp/uacp_mcp_server.py`), speaks real MCP stdio, and asserts the listed
  tool set **equals `tool_specs()`** (a missing tool is the "plugin shipped zero MCP servers"
  regression the design review caught).
- **Hooks** — the declared `hooks/hooks.json` resolves, parses, and declares its hook commands.
- **Skills** — each shipped `skills/<dir>/SKILL.md` is loadable (valid frontmatter + a `name`).

Fail-closed: an **expected-but-not-actionable** capability is a FAIL, not a vacuous pass.

### Run it

Deterministic prober (needs `uv` + the `mcp` SDK; no container, no model):

```bash
python3 acceptance/conformance.py .            # prints conformance.json; exit 0 iff all actionable
python3 -m pytest tests/acceptance/ -q         # the same prober + non-vacuity checks (CI)
```

In a clean, isolated container (only the documented host prereq — `uv`):

```bash
mkdir -p acceptance/out
docker compose -f acceptance/compose.yml run --rm conformance
cat acceptance/out/conformance.json
```

## Next increments (designed, not built)

1. the lifecycle **should-block** pipe (a containerized agent, governance-correctness assertion);
2. the **golden path** + tiered scoring; 3. the **backend seam** (Ollama/OpenAI/Anthropic);
4. the scenario ladder + scheduling; 5. a **second runtime** (Hermes/Codex) behind the runner seam.

See [`design/e2e-acceptance/30-roadmap.md`](../design/e2e-acceptance/30-roadmap.md).

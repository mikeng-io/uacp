# UACP E2E Acceptance Harness

The containerized acceptance test for UACP. Design: [`design/e2e-acceptance/`](../design/e2e-acceptance/).

This is the **acceptance** layer: it **reproduces what a real user does** and reports the truth — a
*black-box* test, distinct from the in-process integration tests. It is **allowed to fail**: a red run
that reproduces a real user-facing bug is the point, not something to engineer away.

## Increment 0 — does a normal user's install actually work?

`acceptance/run.sh` runs, in a clean container, **exactly what a normal user does** and reports
**Claude Code's own verdict** — it never reads the plugin source, launches the MCP server itself, or
warms a cache:

1. **baseline** — a realistic env only: **Claude Code + `uv`** (the standard tools a normal dev has),
   installed their official ways. Nothing pre-resolved, nothing warmed. If the plugin needs something
   the user lacks, the test *exposes* it.
2. **install (the published path)** — `claude plugin marketplace add` + `claude plugin install uacp`.
3. **observe** — `claude plugin list` (did Claude Code **load** it?) + `claude mcp list` (did the
   plugin's MCP server **connect**?). Exit non-zero — with the captured CC output as the bug report —
   if it failed to load or the MCP server didn't connect.

It caught a real ship-to-users bug on its first faithful run: the plugin **failed to load** because
`plugin.json` declared `hooks: ./hooks/hooks.json` which Claude Code already auto-loads (duplicate).
That was fixed in the *product* (drop the manifest key) → the plugin loads and the e2e goes green.

### Run it

```bash
make acceptance                                          # build + run the container
# or:
docker compose -f acceptance/compose.yml run --rm conformance
cat acceptance/out/03-plugin-list.txt                    # Claude Code's own report
```

Needs docker. The captured `claude` output lands under `acceptance/out/`.

## Next increments (designed, not built)

The **agent actually using** the plugin — `claude -p "<task>" --dangerously-skip-permissions` (the
non-interactive headless mode) against a model backend (local Ollama via a proxy, or a key) — then the
governed lifecycle + tiered governance assertions. See
[`design/e2e-acceptance/30-roadmap.md`](../design/e2e-acceptance/30-roadmap.md).

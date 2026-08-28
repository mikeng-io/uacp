# `runner:hermes` — UACP plugin-conformance acceptance container

The Hermes twin of [`acceptance/`](../README.md). Same discipline — reproduce what a real user does,
report the **runtime's own verdict** — with Hermes' install recipe instead of Claude Code's.

Design: [`design/e2e-acceptance/11-runner-adapter-seam.md`](../../design/e2e-acceptance/11-runner-adapter-seam.md)
(the 5-point runner contract) and
[`design/e2e-acceptance/13-plugin-conformance.md`](../../design/e2e-acceptance/13-plugin-conformance.md)
(what "actionable" means). Full specification of this build: [`GOAL.md`](GOAL.md).

## The hole it closes

UACP core shipped PEP 695 syntax (`class Loaded[T]`, 3.12+) while the Hermes venv is Python 3.11.
Hermes wraps each plugin's load in its own `except`, so the plugin did not load — it was merely
recorded as `error`. No crash, no failing test, CI green on 3.13. Meanwhile `config/uacp.toml`
asserted `migration_status = "live_bound_user_plugin"`.

That claim survived because **nothing ever ran the shipped plugin on a real Hermes at a real floor
interpreter.** Static guards (`tests/unit/test_python_version_floor.py`, `scripts/check_python_floor.py`,
the `test-floor` CI job) now prove the code *parses and imports* at the floor. They do not prove it
*loads inside Hermes*. This container does.

## Run it

```bash
make acceptance-hermes                                                   # build + run
# or:
docker compose -f acceptance/hermes/compose.yml run --rm conformance-hermes
cat acceptance/hermes/out/conformance.json                               # the serialized verdict
cat acceptance/hermes/out/06-toolsets.json                               # Hermes' own tool report
```

Needs docker. Build takes several minutes (a real Hermes install). Captured Hermes output lands
under `acceptance/hermes/out/`.

## What it does

1. **Baseline.** `debian:bookworm-slim` — **no Python at all**, plus what a user needs to run Hermes'
   published installer. Hermes' own `install.sh` (pinned by commit + sha256, == `v0.20.6`) bootstraps
   `uv`, and `uv` provisions the interpreter. So the interpreter under test is **whatever Hermes
   chose** (3.11.16 in practice), not one the harness picked. Deliberately unlike
   `tools/proving-ground/images/hermes/Dockerfile`, which pins `python:3.12-slim` — that is a cell
   image, not a floor reproduction. No cache warming, no pre-resolved deps, no source mount standing
   in for an install.
2. **Install, the user-real way.** Hermes has no marketplace. `config/uacp.toml
   [runtime_bindings.hermes]` declares the binding as a **symlink** into `HERMES_ROOT/plugins/`, and
   Hermes plugins are **opt-in** — so the harness does exactly the two things a user does:
   `ln -s` the adapter, then `hermes plugins enable uacp_guardian`.
3. **Observe — Hermes' own reports only.** The harness never reads the plugin's source, never imports
   UACP's Python, and never starts the adapter itself.
4. **Assert, fail-closed**, and serialize `conformance.json`. Non-zero exit on failure; the captured
   Hermes output is the bug report.

## The reports it reads, and why those

Discovery was done against the real pinned CLI in-container (reproduce with
[`probe.sh`](probe.sh)), not from documentation. What Hermes actually offers without a model:

| Hermes command | What it reports | Used for |
|---|---|---|
| `hermes plugins list --json` | **activation only** — a directory scan plus the `plugins.enabled` allow-list | assert the binding took |
| `hermes logs` / `hermes logs errors` | the loader's own `Failed to load plugin '<name>': <reason>` | the load-failure diagnostic |
| `hermes gateway` + `GET /v1/toolsets` | each toolset's **concrete registered tool names**, straight out of the live registry | the tool-presence assertion |
| `hermes tools list --platform cli` | the plugin's toolset appears under "Plugin toolsets" | secondary corroboration (captured, not asserted) |

**`hermes plugins list` is not sufficient on its own** — under the planted PEP-695 fault it still
reported `uacp_guardian` as `"status": "enabled"`. A harness asserting only on it would have passed
the very defect that motivated this work.

The name-level oracle is the api_server platform's `GET /v1/toolsets`, whose own docstring calls it
"the deterministic equivalent of what a client would otherwise have to recover by asking the model
what tools it can call". It needs no model, so the container runs with `network_mode: none`.

Dead ends, recorded so they are not re-tried: `hermes chat -q "/tools"` and `hermes -z` send the text
to the **model** rather than dispatching the slash command, so the name-level `/tools` listing is
unreachable without inference; `hermes mcp serve` is a *messaging bridge*, not the agent's tool
surface; `hermes doctor` / `hermes status` say nothing about user-plugin load state; `hermes tools
--summary` requires a TTY.

## The expected tool set is derived, never hardcoded

EXPECTED comes from the **generated** block of the shipped
`runtime-adapters/hermes/plugins/uacp_guardian/plugin.yaml`, which `scripts/gen_doc_tables.py`
derives from `tool_specs()` and CI drift-lints (`make docs-drift`). So the harness tracks the registry
automatically. A literal count here would rot — that is exactly how the manifest once drifted to 10
while the kernel registered 19. If the generated block is empty, the harness **fails closed** rather
than passing vacuously.

## Proven / not proven

**Proven.** The adapter loads inside a real Hermes at the interpreter Hermes itself selected, and all
19 governed tools it declares are registered under its toolset — compared **by name**, both
directions (missing *and* unexpected).

**Not proven, deliberately:**

- **The lifecycle drive (Priority 2).** Out of scope per
  [node 11](../../design/e2e-acceptance/11-runner-adapter-seam.md): there is no MCP/tool channel for
  the lifecycle ops (init / transition / register / finalize) yet, so Increment 1 is blocked.
  Conformance does not need it, which is why it goes first. This container satisfies contract points
  1, 2, 4 and 5; **point 3 (drive the lifecycle) is not attempted.**
- **Plugin hook firing.** `uacp_guardian` registers `pre_tool_call` / `post_tool_call` /
  `pre_llm_call`, but Hermes exposes no model-free report of plugin hook registration (`hermes hooks`
  is a different subsystem — shell-script hooks in `config.yaml`), and `pre_llm_call` needs a model
  turn to fire at all. Asserting any of it here would need a model in the loop, so it is covered by
  `tests/integration/test_hermes_preamble_injection.py` instead and left unasserted here. Stated
  rather than faked.

  > Which hooks Hermes actually fires is not what it declares. `on_session_start` is in its
  > valid-hook list and is **never fired** for plugins — established by registering a probe plugin
  > with seven hooks and running a real session, where only `on_session_finalize` fired. That is why
  > the cognition preamble rides `pre_llm_call` + `is_first_turn`.
- **`thread_title_sync`.** Carries the same unbacked-binding problem, but is a separate probe.
- **Host installs.** The claim is scoped to this container's reproducible install.

## Calibrated, not merely green

A harness that cannot catch the defect that motivated it is not evidence. Both directions are
demonstrated in [`evidence/20260828-calibration.md`](evidence/20260828-calibration.md): the real
historical PEP-695 defect → RED with Hermes' own reason; one tool removed from the registered surface
→ RED naming that tool; both reverted → GREEN.

## Where this runs

**Periodic / pre-release — not a merge gate.** Per
[node 00](../../design/e2e-acceptance/00-intent.md)'s integration-vs-acceptance table, the integration
tests gate merges and the acceptance tests prove the shipped product. This one builds a full Hermes
from source over the network and takes minutes, so it must **not** be wired into the PR-blocking CI
job. It is `make acceptance-hermes`, run before a release or when the adapter, `tool_specs()`, or the
Python floor changes. The fast, always-on guards for the same failure class are
`tests/unit/test_python_version_floor.py` and the `test-floor` CI job.

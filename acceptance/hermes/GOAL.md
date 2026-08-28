# Goal: `runner:hermes` acceptance container — plugin conformance

Build the Hermes twin of the existing Claude Code acceptance harness: a container that
installs UACP into Hermes **the user-real way** and proves, from Hermes' own report, that
the plugin actually loaded and its governed tools are callable.

## Why this exists (the defect it must catch)

UACP core shipped PEP 695 syntax (`class Loaded[T]`, 3.12+) while the Hermes venv is
Python 3.11. Hermes' plugin loader wraps each plugin in its own `except`, so the plugin
did not load and was merely marked `error` — no crash, no failing test, CI green on 3.13.
Meanwhile `config/uacp.toml` asserted `migration_status = "live_bound_user_plugin"`.
A claim of "bound" survived because **nothing ever ran the shipped plugin on a real
Hermes at a real floor interpreter.** That is the hole to close.

## Scope

**Priority 1 (plugin conformance) ONLY** — per `design/e2e-acceptance/13-plugin-conformance.md`.
Do NOT build the lifecycle drive (Priority 2). Node 11 records why: there is no MCP/tool
channel for lifecycle ops (init/transition/register/finalize) yet, so Increment 1 is
blocked. Conformance does not need it, which is why it goes first.

## Read first

- `design/e2e-acceptance/11-runner-adapter-seam.md` — the 5-point contract ANY runner must
  satisfy. Your image must satisfy points 1, 2, 4, 5. Point 3 (drive the lifecycle) is
  out of scope.
- `design/e2e-acceptance/13-plugin-conformance.md` — what "actionable" means.
- `acceptance/` — the Claude Code reference implementation (Dockerfile + run.sh +
  compose.yml). Mirror its **shape and discipline**, not its install commands.
- `tools/proving-ground/images/hermes/Dockerfile` — an existing Hermes image with a
  reproducible pinned install recipe (install.sh @ commit `2bd1977`, sha256-verified,
  == v0.17.0). **Reuse the pin. Do NOT reuse its `FROM python:3.12-slim`** — see below.
- `runtime-adapters/hermes/plugins/uacp_guardian/` — the adapter under test.
- `config/uacp.toml` `[runtime_bindings.hermes]` — the declared binding is a **symlink**
  into `HERMES_ROOT/plugins/`. That is the user-real install path for Hermes (there is no
  marketplace install as with Claude Code).

## Hard requirements

1. **Reproduce the real environment, do not choose a convenient one.** The existing
   proving-ground image pins `python:3.12-slim`, which is exactly why this defect stayed
   invisible. Let Hermes' own installer select its interpreter, or pin the version a real
   `install.sh` run produces (3.11.x). If you pin a Python, the pin must be justified in a
   comment as *matching real installs*, never as *making the test pass*.
2. **No warming, no shortcuts.** No pre-resolved deps, no source mount in place of an
   install, no cache priming. If the first real launch is broken, this test must EXPOSE
   that, not paper over it. (`acceptance/Dockerfile` states this rule; inherit it.)
3. **Assert on Hermes' OWN report, never on your own inspection.** The harness must not
   read plugin source or import Python itself. Discovery step: determine how Hermes
   reports plugin load status and tool registration — candidates are `hermes doctor`,
   `hermes status`, `hermes tools list`, and any plugin-listing subcommand. Verify against
   the real CLI in-container; `skills/uacp-bridge/references/hermes.md` documents the CLI
   surface but is not authoritative on plugin reporting.
4. **A loaded-but-errored plugin must FAIL the harness.** This is the crux. Asserting
   "hermes started" is worthless. Assert (a) the plugin is reported loaded with no error
   state, and (b) its governed tools are actually present.
5. **Derive the expected tool set, never hardcode it.** The surface is whatever
   `tool_specs()` yields (19 today; the manifest is generated from it by
   `scripts/gen_doc_tables.py` and drift-linted). A hardcoded count in the harness will
   silently rot — the manifest already drifted 10 vs 19 that way.
6. **Non-interactive and headless.** No approval prompts. Never `--yolo`.
7. **Exit non-zero on failure; the captured Hermes output IS the bug report.** Write
   artifacts to a mounted `out/` volume, same as `acceptance/run.sh`.

## Acceptance criteria — the harness is only done when calibrated

Green on a correct tree is NOT sufficient evidence. You must prove the harness discriminates:

- **Planted-fault calibration (mandatory).** Reintroduce the real historical defect —
  restore `class Loaded[T]` in `skills/uacp-core/scripts/engines/io/loaders.py` — rebuild,
  and confirm the harness goes **RED** with a diagnostic naming the plugin as unloaded.
  Then revert and confirm **GREEN**. A harness that cannot catch the defect that motivated
  it is not evidence of anything.
- **Second planted fault:** remove one tool from the registered surface and confirm the
  tool-presence assertion catches it (proves criterion 5 is live, not decorative).
- Record both calibration runs as the harness's own evidence.

## Deliverables

- `acceptance/hermes/` (or the layout node 11 implies) — Dockerfile, entrypoint, compose
  service, README stating what is proven and what is explicitly NOT (no lifecycle drive).
- A short note on where this runs (it is periodic/pre-release, not a merge gate — see
  node 00's integration-vs-acceptance table). Do not wire it into the PR-blocking CI job.
- If, and only if, the container proves a live bind end-to-end: the evidence artifact that
  lets `config/uacp.toml [runtime_bindings.hermes.adapters.uacp_guardian]` move from
  `migration_status = "unverified"` back to a backed claim, committed at a path reachable
  from a fresh clone. Do not restore the old status without that artifact.

## Out of scope

Lifecycle drive; the model-backend seam (no model is needed for conformance); benchmark
scoring; `thread_title_sync` (it carries the same unbacked-binding problem but is a
separate probe).

## Working rules

Work in a git worktree, not on `main`. Tests are the arbiter, not inspection. Report what
actually happened — if the container cannot reach a real Hermes install, say so rather
than substituting a mock.

---

## Context: the state this goal starts from

The PEP 695 defect is **already fixed** on branch `fix/py-floor-and-hermes-manifest`
(worktree `.worktrees/fix-py-floor`), which also:

- corrected `requires-python` `>=3.10` → `>=3.11` (3.10 never worked — `config.py` has an
  unguarded `import tomllib`, stdlib only from 3.11);
- moved ruff `target-version` off the CI interpreter (`py313` → `py311`), since `UP` was
  actively *suggesting* the 3.12-only syntax that broke Hermes;
- added `tests/unit/test_python_version_floor.py` (grammar guard, runs on any interpreter)
  and `scripts/check_python_floor.py` + a blocking `test-floor` CI job (real floor
  interpreter, catches newer-than-floor stdlib);
- generated `plugin.yaml`'s tool list from `tool_specs()` (was 10, actual 19) and put it
  under the existing drift lint;
- set `migration_status` to `unverified` — **this goal produces the evidence that can
  move it back.**

Those are static guards. They prove the code *parses and imports* at the floor. They do
NOT prove the plugin *loads inside a real Hermes*. That is the gap this container closes,
and it is why the calibration step is non-negotiable: the harness must be shown to catch
the exact defect the static guards now prevent, or it is not evidence of anything.

# Calibration — `runner:hermes` plugin conformance (2026-08-28)

A green harness is not evidence of anything until it is shown to go **red on the defect it exists to
catch**. This is that demonstration. Both faults were planted in the source tree, the image was
rebuilt from scratch, the harness was run, and the fault was then reverted.

All runs: `docker run --rm --network none -v <out>:/out uacp-acceptance-hermes /run.sh`
(no network at run time — plugin conformance needs no model, and removing the network proves it).

Runtime under test, as Hermes reported it: **Hermes Agent v0.17.0 (2026.6.19)**, interpreter
**Python 3.11.16** — chosen by Hermes' own `install.sh` on a `debian:bookworm-slim` base that ships
no Python at all. That interpreter is the whole point: it is the floor at which the original defect
bit, and nothing in this harness selected it.

---

## Fault 1 (mandatory) — the real historical defect: PEP 695 syntax at a 3.11 floor

Restored `class Loaded[T]` (and `value: T | None`) in
`skills/uacp-core/scripts/engines/io/loaders.py` — the exact shape that shipped and silently broke
the Hermes bind.

**Result: RED, exit code 1.** The diagnostic names the plugin as unloaded *and* carries Hermes' own
reason:

```
FAIL: Hermes reports 'uacp_guardian' FAILED TO LOAD:
    2026-08-28 00:38:37,270 WARNING hermes_cli.plugins: Failed to load plugin 'uacp_guardian': invalid syntax (loaders.py, line 57)
FAIL: Hermes' registered-tool report contains no 'uacp_guardian' toolset — the plugin registered nothing
FAIL: governed tools DECLARED but not registered in Hermes:
    - uacp_artifact_write
    ... (all 19)
```

Note what did **not** change under this fault: `hermes plugins list --json` still reported
`uacp_guardian` as `"status": "enabled"`, `"source": "user"`. That is precisely the hole this harness
closes — Hermes' activation report is a directory scan plus a config allow-list and says nothing
about whether the module imported. Any harness asserting only on `plugins list` would have passed
this run.

## Fault 2 — a tool removed from the *registered* surface

Deleted the `uacp_sandbox_check` `ToolSpec` from `skills/uacp-core/scripts/tool_specs.py`, leaving
the shipped `plugin.yaml` manifest still declaring all 19. The plugin loads fine; one declared
governed tool simply never registers.

**Result: RED, exit code 1**, naming the exact tool:

```
FAIL: governed tools DECLARED but not registered in Hermes:
    - uacp_sandbox_check
```

This is what makes criterion 5 live rather than decorative: the assertion is a **set comparison by
name**, not a count, so it localizes the regression instead of just reporting a mismatch.

## Revert — both faults removed

**Result: GREEN, exit code 0.**

```
PASS: Hermes loaded 'uacp_guardian' on Python 3.11.16 and registered all 19 declared governed tools
```

Serialized artifact: [`20260828-plugin-conformance.json`](20260828-plugin-conformance.json).

---

## What the calibration establishes

| Failure mode | Caught by | Shown |
|---|---|---|
| Plugin silently fails to load at the real floor interpreter | Hermes' own `Failed to load plugin` log line + absence of its toolset in the live registry | Fault 1 |
| A declared governed tool is not actionable | EXPECTED ∪ DISCOVERED set difference, by name | Fault 2 |
| Manifest declares tools the install does not expose | same comparison, `unexpected_tools` side | structurally (same assertion, other direction) |

## What it does NOT establish

- **Plugin hook firing.** `uacp_guardian` registers `pre_tool_call` / `post_tool_call`. Hermes
  exposes no model-free report of plugin hook registration (`hermes hooks` is a different subsystem —
  shell-script hooks declared in `config.yaml`), so this harness does not assert it, and no calibration
  for it exists. Stated rather than faked.
- **The lifecycle drive.** Priority 2, out of scope — see the README.

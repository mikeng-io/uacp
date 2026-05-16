---
type: index
tags: [index, runtime, enforcement, guardian, heartgate]
status: living-document
---

# Runtime Enforcement — Index

How Guardian (pre-tool-call) and Heartgate (phase-transition) actually enforce policy, and how to bind UACP to a new runtime.

## Documents

| File | Purpose |
|---|---|
| [runtime-enforcement.md](runtime-enforcement.md) | Guardian decision flow, Heartgate full check list (18 rows), state-mutation protocol, mode-aware enforcement. |
| [runtime-integration-guide.md](runtime-integration-guide.md) | Integration contract for building a UACP-aware runtime adapter (hooks, tools, configuration entry points). |
| [runtime-porting-and-version-control.md](runtime-porting-and-version-control.md) | Runtime-adapter authority chain, symlink/export binding, version-control SOP, future runtime targets. |

## Related

- Lifecycle model: [`../lifecycle/`](../lifecycle/INDEX.md).
- Tool/skill authority surfaces: [`../reference/skill-enforcement-spec.md`](../reference/skill-enforcement-spec.md).
- Kernel source: `runtime-adapters/hermes/plugins/uacp_guardian/{__init__.py, kernel.py}`.

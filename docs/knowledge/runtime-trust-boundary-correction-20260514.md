# Runtime Trust Boundary Correction — 2026-05-14

## Why This Exists

During containment planning, the operator pushed back that UACP was drifting into trying to police arbitrary user behavior: editing files in VS Code, changing local config, disabling plugins, or running external runtimes without UACP integration. That framing is outside UACP's intended framework and creates circular enforcement assumptions.

See `docs/runtime/runtime-enforcement.md` §Runtime Trust Boundary for the canonical boundary doctrine. This note captures the operator-preference pattern and the correction response — it does not restate the doctrine.

## Operator Preference Pattern

When a proposed solution feels "fuzzy," "chaotic," or like it is "jumping out of the framework," **pause and reframe the authority boundary before adding mechanisms.** Prefer clear separation of responsibility over hardline config or self-policing loops.

## Out-of-Band Mutation Examples

Manual or host-side changes are not "impossible"; they are **untrusted until revalidated**:

- A file edited in VS Code.
- A plugin symlink changed manually.
- `config.yaml` changed outside a governed writer/tool path.
- An external runtime (e.g., Codex, OpenCode) run without UACP integration enabled.

## 3-Step Correct Response

1. Do not pretend UACP prevented the change.
2. Re-run the relevant verification/proof before trusting affected artifacts.
3. Update evidence/status if the runtime posture changed; keep protected execution fail-closed when required posture cannot be proven.

---

*Provenance: boundary correction recorded in UACP commit `d968a64` (2026-05-14), touching `docs/runtime-enforcement.md`, `docs/index.md`, `.outputs/uacp-current-status.yaml`, `.outputs/uacp-operational-dashboard.yaml`, and `verification/runtime-trust-boundary-correction-20260514.yaml`.*

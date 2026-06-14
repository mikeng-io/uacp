# UACP Runtime Trust Boundary Correction — 2026-05-14

## Why this exists
During containment planning, the operator pushed back that UACP was drifting into trying to police arbitrary user behavior: editing files in VS Code, changing local config, disabling plugins, or running external runtimes without UACP integration. That framing is outside UACP's intended framework and creates circular enforcement assumptions.

## Correct boundary
- **UACP** defines lifecycle, authority, side effects, evidence obligations, and required runtime posture.
- **Guardian** enforces UACP rules inside a controlled runtime/tool path and verifies runtime-provided evidence.
- **Host/runtime containment** supplies the actual filesystem/process boundary for shell/code execution.
- **Operator/host-side behavior** outside the governed runtime is not something UACP claims to prevent.

## Rule for out-of-band mutation
Manual or host-side changes are not “impossible”; they are **untrusted until revalidated**.

Examples:
- A file edited in VS Code.
- A plugin symlink changed manually.
- `config.yaml` changed outside a governed writer/tool path.
- An external runtime like Codex/OpenCode run without UACP integration enabled.

Correct response:
1. Do not pretend UACP prevented the change.
2. Re-run the relevant verification/proof before trusting affected artifacts.
3. Update evidence/status if the runtime posture changed.
4. Keep protected execution fail-closed when required posture cannot be proven.

## Containment implication
Containment is a host/runtime property, not a self-declared UACP permission. UACP can require contained execution; Guardian can verify evidence that containment exists; the host/runtime must actually provide it. If it cannot, UACP-bound shell/code remains blocked.

## Operator preference captured
When Mike says a proposed solution feels “fuzzy,” “chaotic,” or like it is “jumping out of the framework,” pause and reframe the authority boundary before adding mechanisms. Prefer clear separation of responsibility over hardline config or self-policing loops.

## Canonical session outcome
The boundary correction was recorded in UACP commit `d968a64`:
- `docs/runtime-enforcement.md`
- `docs/index.md`
- `.outputs/uacp-current-status.yaml`
- `.outputs/uacp-operational-dashboard.yaml`
- `verification/runtime-trust-boundary-correction-20260514.yaml`
